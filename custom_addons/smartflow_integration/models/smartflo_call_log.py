from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

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

    @api.model
    def auto_archive_old_logs(self):
        cutoff = fields.Datetime.now() - relativedelta(days=180)
        logs = self.search([('create_date', '<', cutoff), ('active', '=', True)])
        logs.write({'active': False})

    @api.model
    def auto_delete_very_old_logs(self):
        cutoff = fields.Datetime.now() - relativedelta(years=1)
        self.search([('create_date', '<', cutoff)]).unlink()

    @api.model
    def process_webhook_data(self, data):
        uuid = data.get('custom_identifier', {}).get('odoo_uuid') or data.get('uuid')
        call_id = data.get('call_id')
        customer_number = data.get('customer_no_with_prefix') or data.get('customer_number')

        agent_number = data.get('answered_agent_number')
        answered_agent = data.get('answered_agent')
        agent_extension = answered_agent.get('number') if isinstance(answered_agent, dict) else None
        # If missed, try to get from missed_agent
        if not agent_number or agent_number == "_number":
            missed_agents = data.get('missed_agent') or []
            if missed_agents and isinstance(missed_agents, list):
                agent_number = missed_agents[0].get('agent_number')
                agent_extension = missed_agents[0].get('number')
        # Lookup agent
        agent_user = None
        if agent_number:
            agent_user = self.env['res.users'].sudo().search([
                '|',
                ('smartflo_agent_number', '=', agent_number),
                ('smartflo_extension_number', '=', agent_extension)
            ], limit=1)

        # Resolve direction
        direction = data.get('direction')
        if direction == 'clicktocall':
            direction = 'outbound'

        billsec = self.safe_int(data.get('billsec'))
        reason_key = (data.get('reason_key') or '').lower()
        call_flow = data.get('call_flow') or []
        duration = self.safe_int(data.get('duration'))
        # Determine final status
        call_status_raw = data.get('call_status', '').lower()
        missed_agents = data.get('missed_agent') or []

        if call_status_raw == 'missed':
            if missed_agents:
                status = 'missed_by_agent'
            else:
                status = 'missed_by_customer'
        elif any(
            step.get("type") == "Agent" and step.get("id") is None
            for step in call_flow[1:]
        ) and reason_key == "call disconnected by caller" and billsec < 30:
            status = 'answered_voicemail'
        else:
            status = 'answered_talk'

        # Build values
        values = {
            'call_id': call_id,
            'uuid': uuid,
            'customer_number': customer_number,
            'agent_number': agent_number,
            'agent_id': agent_user.id if agent_user else False,
            'start_time': data.get('start_stamp'),
            'answer_time': data.get('answer_stamp'),
            'end_time': data.get('end_stamp'),
            'duration': duration,
            'billsec': billsec,
            'recording_url': data.get('recording_url'),
            'hangup_cause': data.get('hangup_cause'),
            'call_connected': data.get('call_connected', False),
            'status': status,
            'direction': direction,
            'color': {
                'answered': 10,
                'voicemail': 7,
                'missed_by_agent': 1,
                'missed_by_customer': 2,
                'initiated': 3,
            }.get(status, 0),
        }

        # Link lead
        lead_id = data.get('custom_identifier', {}).get('lead_id')
        lead_name = data.get('custom_identifier', {}).get('lead_name')
        if not lead_id:
            lead = self.env['crm.lead'].sudo().search([('customer_number', '=', customer_number)], limit=1)
            lead_id = lead.id if lead else False
            lead_name = lead.name if lead else False
        if lead_id:
            values['lead_id'] = lead_id

        # Update or create log
        log = self.env['smartflo.call.log'].sudo().search([('uuid', '=', uuid)], limit=1)
        if log:
            log.write(values)
        else:
            self.env['smartflo.call.log'].sudo().create(values)

        # Notify agent
        if agent_user:
            message = {
                    'type': 'smartflo.call',
                    'lead_name': lead_name,
                    'lead_id': lead_id,
                    'call_start': data.get('start_stamp'),
                    'status': status,
                    'duration': duration,
                    'uuid': uuid,
            }
            channel = f"smartflo.agent.{agent_user.partner_id.id}"
            self.env['bus.bus']._sendone(channel,'smartflo.call',message)
        return {
            'message': message,
            'channel': channel
        }
    def safe_int(val, default=0):
        try:
            return int(val)
        except (ValueError, TypeError):
            return default      
