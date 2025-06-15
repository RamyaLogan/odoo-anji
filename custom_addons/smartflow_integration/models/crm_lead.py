# models/crm_lead.py
from odoo import models, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    smartflo_call_log_ids = fields.One2many(
        'smartflo.call.log', 'lead_id', string="Call History"
    )