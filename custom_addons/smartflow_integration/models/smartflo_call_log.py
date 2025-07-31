from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
import pytz
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class SmartfloCallLog(models.Model):
    _name = 'smartflo.call.log'
    _description = 'Smartflo Call Log'
    _order = 'start_time desc'

    call_id = fields.Char(string="Call ID", index=True)
    uuid = fields.Char(string="Odoo UUID", required=True, index=True)
    status = fields.Selection([
        ('initiated', 'Initiated'),
        ('missed_by_agent', 'Missed by Agent'),
        ('missed_by_customer', 'Missed by Customer'),
        ('answered_voicemail', 'Answered (Voicemail)'),
        ('answered_talk', 'Answered (Talk)'),
    ], string="Call Status")
    direction = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound')
    ], string="Direction")

    requested_time = fields.Datetime(string="C2C Requested Time")
    customer_number = fields.Char(string="Customer Number", index=True)
    agent_number = fields.Char(string="Agent Number")
    agent_id = fields.Many2one('res.users', string="Agent")

    start_time = fields.Datetime(string="Start Time")
    answer_time = fields.Datetime(string="Answer Time")
    end_time = fields.Datetime(string="End Time")

    duration = fields.Integer(string="Total Duration (sec)")
    billsec = fields.Integer(string="Billable Duration (sec)")
    recording_url = fields.Char(string="Recording URL")
    hangup_cause = fields.Char(string="Hangup Cause")
    call_connected = fields.Boolean(string="Call Connected")

    lead_id = fields.Many2one('crm.lead', string="Linked Lead")
    model_name = fields.Char(string="Source Model")

    color = fields.Integer(string="Color Index")
    active = fields.Boolean(default=True)
    effective_start_time = fields.Datetime(
        string="Effective Start Time",
        compute="_compute_effective_start_time",
        store=True,
        index=True
    )

    @api.depends('start_time', 'requested_time')
    def _compute_effective_start_time(self):
        for rec in self:
            rec.effective_start_time = rec.start_time or rec.requested_time 
            
    @api.model
    def auto_archive_old_logs(self):
        cutoff = fields.Datetime.now() - relativedelta(days=180)
        logs = self.search([('create_date', '<', cutoff), ('active', '=', True)])
        logs.write({'active': False})

    @api.model
    def auto_delete_very_old_logs(self):
        cutoff = fields.Datetime.now() - relativedelta(years=1)
        self.search([('create_date', '<', cutoff)]).unlink()

    def _resolve_call_status(self, data, direction):
        call_status_raw = (data.get('call_status') or '').lower()
        reason_key = (data.get('reason_key') or '').lower()
        billsec = self.safe_int(data.get('billsec'))
        call_flow = data.get('call_flow') or []
        missed_agents = data.get('missed_agent') or []

        if call_status_raw == 'missed':
            if missed_agents:
                return 'missed_by_agent'
            else:
                return 'missed_by_customer'
        elif any(step.get("type") == "Agent" and step.get("id") is None for step in call_flow[1:]) \
                and reason_key == "call disconnected by caller" and billsec < 30:
            return 'answered_voicemail'
        elif not call_status_raw and direction == 'inbound':
            return 'initiated'
        else:
            return 'answered_talk'
            
    
    def _resolve_lead(self, customer_number_raw):

        if customer_number_raw and customer_number_raw.startswith("+91"):
            customer_number_trimmed = customer_number_raw[3:]
        elif len(customer_number_raw) == 10:
            customer_number_trimmed = customer_number_raw
        else:
            customer_number_trimmed = customer_number_raw[2:]

        lead = self.env['crm.lead'].sudo().search([
            ('phone', '=', customer_number_trimmed)
        ], limit=1)
        return lead

    def _resolve_agent(self, data):
        def generate_possible_variants(number):
            """Generate all useful variants for comparison with DB."""
            if not number or not isinstance(number, str):
                return []
            digits = ''.join(filter(str.isdigit, number))
            variants = set()
            if len(digits) == 10:
                variants.add(digits)
                variants.add('91' + digits)
                variants.add('+91' + digits)
            elif len(digits) == 12 and digits.startswith('91'):
                variants.add(digits)
                variants.add('+' + digits)
                variants.add(digits[2:])  # raw 10-digit
            elif len(digits) == 13 and digits.startswith('91') and digits[2] == '0':
                variants.add(digits)
            else:
                variants.add(digits)  # could be extension or internal code
            return list(variants)

        # Step 1: Get number + extension
        agent_number_raw = data.get('answered_agent_number')
        answered_agent = data.get('answered_agent')
        agent_extension_raw = answered_agent.get('number') if isinstance(answered_agent, dict) else None

        # Step 2: Fallback to missed agent if needed
        if not agent_number_raw or agent_number_raw == "_number":
            missed_agents = data.get('missed_agent') or []
            if missed_agents and isinstance(missed_agents, list) and missed_agents[0]:
                agent_number_raw = missed_agents[0].get('agent_number')
                agent_extension_raw = missed_agents[0].get('number')

        variants = set(generate_possible_variants(agent_number_raw) + generate_possible_variants(agent_extension_raw))

        if not variants:
            _logger.warning("⚠️ No number variants found to resolve agent.")
            return None

        # Step 3: Search across smartflo fields
        domain = ['|', '|']
        domain += [('smartflo_agent_number', 'in', list(variants))]
        domain += [('smartflo_extension_number', 'in', list(variants))]
        domain += [('smartflo_caller_id', 'in', list(variants))]

        agent_user = self.env['res.users'].sudo().search(domain, limit=1)
        if agent_user:
            _logger.info("✅ Agent resolved: %s (%s)", agent_user.name, agent_user.id)
            return agent_user

        # Step 4: Fallback to call_to_number or caller_id_number
        direction = data.get('direction')
        raw_fallback = data.get('call_to_number') if direction == 'inbound' else data.get('caller_id_number')
        fallback_variants = generate_possible_variants(raw_fallback)

       
        if fallback_variants:
            domain = ['|', '|']
            domain += [('smartflo_agent_number', 'in', fallback_variants)]
            domain += [('smartflo_extension_number', 'in', fallback_variants)]
            domain += [('smartflo_caller_id', 'in', fallback_variants)]
            agent_user = self.env['res.users'].sudo().search(domain, limit=1)
            if agent_user:
                _logger.info("✅ Agent resolved via fallback: %s (%s)", agent_user.name, agent_user.id)
                return agent_user

        _logger.warning("❌ No agent resolved for this call.")
        return None

    @api.model
    def process_webhook_data(self, data):
        custom_identifier = data.get('custom_identifier', {})
        uuid = custom_identifier.get('odoo_uuid') or data.get('uuid')
        call_id = data.get('call_id')
        direction_raw = data.get('direction') or ''
        direction = 'outbound' if direction_raw == 'clicktocall' or direction_raw == 'click_to_call' else 'inbound'

       
        customer_number_raw = (
            data.get('customer_no_with_prefix') or
            data.get('customer_number') or
            (data.get('caller_id_number') if direction_raw == 'inbound' else data.get('call_to_number'))
        )

        # Resolve Agent

        agent_user = self._resolve_agent(data)
        if not agent_user:
            _logger.warning("No agent found for call data: %s", data)
            return {'error': 'No agent found for this call.'}
        # Resolve Lead
        lead_id = custom_identifier.get('lead_id')
        lead_name = custom_identifier.get('lead_name')

        # Step 2: If lead_id not present, try to resolve
        if not lead_id:
            lead = self._resolve_lead(customer_number_raw)
            lead_id = lead.id if lead else False
            lead_name = lead.name if lead else ''
    
        # Status Resolution
        status = self._resolve_call_status(data, direction)

        # Build Values
        values = {
            'call_id': call_id,
            'uuid': uuid,
            'customer_number': customer_number_raw,
            'agent_number': data.get('answered_agent_number'),
            'agent_id': agent_user.id if agent_user else False,
            'start_time': self._safe_datetime(data.get('start_stamp')),
            'answer_time': self._safe_datetime(data.get('answer_stamp')),
            'end_time': self._safe_datetime(data.get('end_stamp')),
            'duration': self.safe_int(data.get('duration')),
            'billsec': self.safe_int(data.get('billsec')),
            'recording_url': data.get('recording_url'),
            'hangup_cause': data.get('hangup_cause'),
            'call_connected': data.get('call_connected', False),
            'status': status,
            'direction': direction,
            'lead_id': lead_id,
            'color': {
                'answered': 10,
                'voicemail': 7,
                'missed_by_agent': 1,
                'missed_by_customer': 2,
                'initiated': 3,
            }.get(status, 0),
        }
        # Create or update record
        log = self.env['smartflo.call.log'].sudo().search([('uuid', '=', uuid)], limit=1)
        if log:
            log.write(values)
        else:
            self.env['smartflo.call.log'].sudo().create(values)
            self.update_call_summary(agent_user, data.get('start_stamp'), values['duration'],lead_id)
        # Send realtime bus only if agent found
        if agent_user:
            message = {
                'type': 'smartflo.call',
                'lead_name': lead_name,
                'lead_id': lead_id,
                'call_start': self.convert_utc_str_to_ist_str(data.get('start_stamp')),
                'status': status,
                'duration': values['duration'],
                'uuid': uuid,
                'direction': direction,
            }
            channel = f"smartflo.agent.{agent_user.partner_id.id}"
            self.env['bus.bus']._sendone(channel, 'smartflo.call', message)
        return {'success': True}

    def update_call_summary(self,agent_user, call_start_str, duration,lead_id):
        if not agent_user:
            return
        _logger.info("update call summart: %s", agent_user.id)
        call_start_dt = datetime.strptime(call_start_str, "%Y-%m-%d %H:%M:%S")
        call_date = call_start_dt.date()
        summary = self.env['call.log.summary'].sudo().search([
            ('user_id', '=', agent_user.id),
            ('date', '=', call_date)
        ], limit=1)
        lead_total_calls = summary.total_lead_calls if summary else 0
        if lead_id:
            lead_total_calls +=1
        if summary:
            summary.sudo().write({
                'total_calls': summary.total_calls + 1,
                'total_duration': summary.total_duration + duration,
                'total_lead_calls': lead_total_calls
            })
        else:
            self.env['call.log.summary'].sudo().create({
                'user_id': agent_user.id,
                'date': call_date,
                'total_calls': 1,
                'total_lead_calls': lead_total_calls,
                'total_duration': duration
            })

    @staticmethod
    def safe_int(val, default=0):
        try:
            return int(val)
        except (ValueError, TypeError):
            return default  

    def _safe_datetime(self, val):
        if isinstance(val, str) and val.strip():
            try:
                return fields.Datetime.from_string(val)
            except Exception:
                return False
        return False

    def convert_utc_str_to_ist_str(self,utc_str):
        if not utc_str:
            return None
        utc_dt = fields.Datetime.from_string(utc_str)
        ist = pytz.timezone("Asia/Kolkata")
        utc_dt = utc_dt.replace(tzinfo=pytz.utc)
        ist_dt = utc_dt.astimezone(ist)
        return ist_dt.strftime("%Y-%m-%d %H:%M:%S")