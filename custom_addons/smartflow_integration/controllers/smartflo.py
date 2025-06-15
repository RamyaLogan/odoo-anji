from odoo import http,fields
import odoo.http as ohttp
from odoo.http import request
import json
import requests
import uuid
from datetime import datetime

class SmartfloController(http.Controller):

    @http.route('/smartflo/recent_calls', type='json', auth='user')
    def get_recent_calls(self):
        today_str = datetime.utcnow().strftime('%Y-%m-%d')
        partner_id = request.env.user.partner_id.id
        channel = f"smartflo.agent.{partner_id}"

        calls = request.env['smartflo.call.log'].sudo().search(
            [('start_time', '>=', today_str)],
            order='start_time desc',
            limit=5
        )

        return [{
            'uuid': c.uuid,
            'lead_id': c.lead_id.id,
            'lead_name': c.lead_id.name,
            'status': c.status,
            'duration': c.duration,
            'call_start': c.start_time,
            'direction': c.direction
        } for c in calls]

    @http.route('/smartflo/c2c_call', type='json', auth='user', methods=['POST'], csrf=False)
    def c2c_call(self, **kw):
        data = json.loads(request.httprequest.data.decode('utf-8'))
        phone = data.get('phone')
        caller_id = request.env.user.smartflo_caller_id
        extension = request.env.user.smartflo_extension_number
        if not phone:
            return {"error": "Phone number is required"}

        # Replace these with your actual Smartflo values
        headers = {
            "accept": "application/json",
            "Authorization": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI2MDg5MDUiLCJjciI6ZmFsc2UsImlzcyI6Imh0dHBzOi8vY2xvdWRwaG9uZS50YXRhdGVsZXNlcnZpY2VzLmNvbS90b2tlbi9nZW5lcmF0ZSIsImlhdCI6MTc0OTY3ODE4MywiZXhwIjoyMDQ5Njc4MTgzLCJuYmYiOjE3NDk2NzgxODMsImp0aSI6ImoyUVhMb2FZUzRSTWtrSlUifQ.W4G7O5wCj-KS_v42xAn3iYGW0xryA1zqj-mZ0P9Yl1E",
            "Content-Type": "application/json"
        }
        call_uuid = str(uuid.uuid4())
        payload = {
            "agent_number": extension,
            "destination_number": "9962390577",
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
            request.env['ir.logging'].create({
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
            message = {
                    'type': 'smartflo.call',
                    'lead_name': data.get('lead_name'),
                    'lead_id': data.get('lead_id'),
                    'phone': phone,
                    'call_start': fields.Datetime.now().isoformat().replace('T', ' '),
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

        