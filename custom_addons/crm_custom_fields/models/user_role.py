# models/user_role.py
from odoo import models, fields

class UserRole(models.Model):
    _name = 'user.role'
    _description = 'User Role'

    name = fields.Char(required=True)
    code = fields.Char(string="Internal Code")
    has_level = fields.Boolean(default=False, help="If this role supports levels like Senior/Junior/Trainee")