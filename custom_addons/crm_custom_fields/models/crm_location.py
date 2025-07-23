from odoo import models, fields

class CrmLocation(models.Model):
    _name = 'crm.location'
    _description = 'CRM Custom Fields Location'

    name = fields.Char(required=True)
    code = fields.Char(string="Internal Code")
    
