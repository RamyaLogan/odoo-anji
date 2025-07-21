# models/res_users.py
from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    user_role_id = fields.Many2one('user.role', string="User Role")
    
