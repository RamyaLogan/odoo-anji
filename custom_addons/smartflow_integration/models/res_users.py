from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    smartflo_extension_number = fields.Char("Smartflo Extension")
    smartflo_agent_number = fields.Char("Smartflo Agent Number")
    smartflo_caller_id = fields.Char("Smartflo Caller ID")
    smartflo_account_type = fields.Selection([
        ('OR165136', 'OR165136'),
        ('TACN6513', 'TACN6513'),
    ], string="Smartflo Account Type")
   