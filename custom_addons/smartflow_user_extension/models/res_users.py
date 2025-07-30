from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    smartflo_account_type = fields.Selection([
        ('OR165136', 'OR165136'),
        ('TACN6513', 'TACN6513'),
    ], string="Smartflo Account Type")
   