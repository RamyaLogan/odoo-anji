from odoo import models, fields, api

class AssignLeadsWizard(models.TransientModel):
    _name = 'crm.assign.leads.wizard'
    _description = 'Assign Leads Wizard'

    lead_ids = fields.Many2many('crm.lead', string="Leads")
    user_ids = fields.Many2many('res.users', string="Salespersons")

    def action_assign_leads(self):
        users = self.user_ids.sorted(lambda u: u.id)
        user_count = len(users)
        for idx,lead in enumerate(self.lead_ids):
            # Simple round-robin assignment logic
            assigned_user = users[idx % user_count]  # You can customize logic here
            lead.user_id = assigned_user