from odoo import models, fields

class CrmCallLead(models.Model):
    _inherit = "crm.lead"

    masked_phone = fields.Char(string='Phone mask', compute='_compute_masked_phone')
    import_source = fields.Char(string='Lead Source')
    age = fields.Integer(string='Age')
    
    def _compute_masked_phone(self):
        for rec in self:
            if rec.phone:
                rec.masked_phone = rec.phone[:2] + '****' + rec.phone[-2:]
            else:
                rec.masked_phone = ''

    def action_trigger_smartflo_call(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.client",
            "tag": "smartflo_initiate_call",
            "target": "new",
            "params": {
                "phone": self.phone, 
                "lead_name": self.name,
                "lead_id": self.id,
            },
        }
        return action

    def action_call_lead(self):
        # This method is called when the user clicks the "Call Lead" button
        for lead in self:
            if lead.phone:
                # Open the phone dialer with the lead's phone number
                return {
                    'type': 'ir.actions.act_url',
                    'url': f'tel:{lead.phone}',
                    'target': 'self',
                }
            else:
                raise UserError("No phone number available for this lead.")
