from odoo import http,fields
import odoo.http as ohttp
from odoo.http import request
import json
import requests
import uuid
from odoo.fields import Datetime
import pytz
from datetime import datetime, time
class SmartfloController(http.Controller):

    @http.route('/smartflo/recent_calls', type='json', auth='user')
    def get_recent_calls(self):
        partner_id = request.env.user.partner_id.id
        channel = f"smartflo.agent.{partner_id}"
        ist = pytz.timezone("Asia/Kolkata")
        now_ist = Datetime.now(ist)
        # Today IST 00:00
        today_ist = ist.localize(datetime(now_ist.year, now_ist.month, now_ist.day, 0, 0, 0))
        # Convert to UTC for search
        today_utc = today_ist.astimezone(pytz.utc)
        calls = request.env['smartflo.call.log'].sudo().search(
            [('effective_start_time', '>=', today_utc),
            ('agent_id', '=', request.env.user.id)],
            order='effective_start_time desc',
            limit=20
        )
        return [{
            'uuid': c.uuid,
            'lead_id': c.lead_id.id,
            'lead_name': c.lead_id.name,
            'status': c.status,
            'duration': c.duration,
            'call_start': c.start_time.astimezone(ist).isoformat() if c.start_time else c.requested_time.astimezone(ist).isoformat() if c.requested_time else None,
            'direction': c.direction
        } for c in calls]

    @http.route('/smartflo/c2c_call', type='json', auth='user', methods=['POST'], csrf=False)
    def c2c_call(self, **kw):
        data = json.loads(request.httprequest.data.decode('utf-8'))
        phone = data.get('phone')
        ist = pytz.timezone("Asia/Kolkata")
        caller_id = request.env.user.smartflo_caller_id
        extension = request.env.user.smartflo_extension_number
        if not phone:
            return {"error": "Phone number is required"}
        # Replace these with your actual Smartflo values
        config = request.env['ir.config_parameter'].sudo()
        user = request.env.user
        account_type = user.smartflo_account_type
        if account_type == 'OR165136':
            api_key = config.get_param("smartflo.OR165136.api_key")
        elif account_type == 'TACN6513':
            api_key = config.get_param("smartflo.TACN6513.api_key")
        else:
            return {"error": "Smartflo API Key not configured for this user."}

        headers = {
            "accept": "application/json",
            "Authorization": api_key,
            "Content-Type": "application/json"
        }
        call_uuid = str(uuid.uuid4())
        payload = {
            "agent_number": extension,
            "destination_number": phone,
            "caller_id": caller_id,
            "async": 1,
            "custom_identifier": {
                "lead_id": data.get('lead_id'),
                "lead_name": data.get('lead_name'),
                "odoo_uuid": call_uuid,
                "source": "CRM"
        }
        }
        try:
            resp = requests.post("https://api-smartflo.tatateleservices.com/v1/click_to_call", headers=headers,
                    json=payload)
            print(resp.status_code, resp.text)
            request.env['ir.logging'].sudo().create({
                'name': 'Smartflo Call',
                'type': 'server',
                'level': 'info',
                'message': f"Calling {phone} via Smartflo for agent {extension}",
                'path': 'smartflo',
                'func': 'c2c_call',
                'line': 0,
            })

            resp.raise_for_status()
            request.env['smartflo.call.log'].sudo().create({
                'uuid': call_uuid,
                'customer_number': phone,
                'lead_id': data.get('lead_id'),
                'status': 'initiated',
                'direction': 'outbound',
                'agent_id': request.env.user.id,
                'requested_time': fields.Datetime.now(),
                'call_connected': False,
            })
            SmartfloLogModel = request.env['smartflo.call.log'].sudo()
            call_start_str = fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            SmartfloLogModel.update_call_summary(request.env.user, call_start_str, 0, data.get('lead_id'))
            message = {
                    'type': 'smartflo.call',
                    'lead_name': data.get('lead_name'),
                    'lead_id': data.get('lead_id'),
                    'phone': phone,
                    'call_start': fields.Datetime.now().astimezone(ist).isoformat(),
                    'status': "initiated",
                    'uuid': call_uuid,
                    'direction': 'outbound',
            }
            channel = f"smartflo.agent.{request.env.user.partner_id.id}"
            request.env['bus.bus']._sendone(channel,'smartflo.call',message)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}
        
    @http.route('/smartflo/webhook', type='json', auth='public', methods=['POST'], csrf=False)
    def smartflo_webhook(self, **kwargs):
        request.env['smartflo.call.log'].sudo().with_delay(
            description="Process Smartflo Webhook"
        ).process_webhook_data(json.loads(request.httprequest.data.decode('utf-8')))
        return {'status': 'queued'}

        