# models/res_users.py
from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    role_level = fields.Selection([
        ('senior', 'Senior'),
        ('junior', 'Junior'),
        ('trainee', 'Trainee'),
    ], string="Role Level")
