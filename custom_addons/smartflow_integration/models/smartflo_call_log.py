from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
import pytz
from datetime import datetime

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
        elif len(call_to_number) == 10:
            customer_number_trimmed = customer_number_raw
        else:
            customer_number_trimmed = customer_number_raw[2:]

        lead = self.env['crm.lead'].sudo().search([
            ('phone', '=', customer_number_trimmed)
        ], limit=1)
        return lead

    def _resolve_agent(self, data):
        agent_number = data.get('answered_agent_number')
        answered_agent = data.get('answered_agent')
        agent_extension = answered_agent.get('number') if isinstance(answered_agent, dict) else None

        # Fallback from missed agent block
        if not agent_number or agent_number == "_number":
            missed_agents = data.get('missed_agent') or []
            if missed_agents and isinstance(missed_agents, list):
                agent_number = missed_agents[0].get('agent_number')
                agent_extension = missed_agents[0].get('number')

        # Primary search if agent_number exists
        if agent_number:
            agent_user = self.env['res.users'].sudo().search([
                '|',
                ('smartflo_agent_number', '=', agent_number),
                ('smartflo_extension_number', '=', agent_extension)
            ], limit=1)
            return agent_user

        # ✅ Final fallback using inbound `call_to_number` → DID based mapping
        call_to_number = data.get('call_to_number')
        if call_to_number:
            if not call_to_number.startswith("+"):
                if call_to_number.startswith("91"):
                    call_to_number = "+" + call_to_number
                elif len(call_to_number) == 10:
                    call_to_number = "+91" + call_to_number
            agent_user = self.env['res.users'].sudo().search([
                '|','|',
                ('smartflo_agent_number', '=', call_to_number),
                ('smartflo_extension_number', '=', call_to_number),
                ('smartflo_caller_id', '=', call_to_number)
            ], limit=1)
            return agent_user

        return None

    @api.model
    def process_webhook_data(self, data):
        custom_identifier = data.get('custom_identifier', {})
        uuid = custom_identifier.get('odoo_uuid') or data.get('uuid')
        call_id = data.get('call_id')
        direction_raw = data.get('direction') or ''
        direction = 'outbound' if direction_raw == 'clicktocall' else 'inbound'

        customer_number_raw = (
            data.get('customer_no_with_prefix') or 
            data.get('customer_number') or 
            data.get('caller_id_number')
        )

        # Resolve Agent
        agent_user = self._resolve_agent(data)

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
            'start_time': data.get('start_stamp'),
            'answer_time': data.get('answer_stamp'),
            'end_time': data.get('end_stamp'),
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
        self.update_call_summary(agent_user, data.get('start_stamp'), values['duration'])
        return {'success': True}

    def update_call_summary(self,agent_user, call_start_str, duration):
        call_start_dt = datetime.strptime(call_start_str, "%Y-%m-%dT%H:%M:%SZ")
        call_date = call_start_dt.date()
        summary = self.env['call.log.summary'].sudo().search([
            ('user_id', '=', agent_user.id),
            ('date', '=', call_date)
        ], limit=1)

        if summary:
            summary.sudo().write({
                'total_calls': summary.total_calls + 1,
                'total_duration': summary.total_duration + duration
            })
        else:
            self.env['call.log.summary'].sudo().create({
                'user_id': agent_user.id,
                'date': call_date,
                'total_calls': 1,
                'total_duration': duration
            })

    @staticmethod
    def safe_int(val, default=0):
        try:
            return int(val)
        except (ValueError, TypeError):
            return default      

    def convert_utc_str_to_ist_str(self,utc_str):
        if not utc_str:
            return None
        utc_dt = fields.Datetime.from_string(utc_str)
        ist = pytz.timezone("Asia/Kolkata")
        utc_dt = utc_dt.replace(tzinfo=pytz.utc)
        ist_dt = utc_dt.astimezone(ist)
        return ist_dt.strftime("%Y-%m-%d %H:%M:%S")