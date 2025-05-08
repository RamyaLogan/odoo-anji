from odoo import models, fields

class CourtDetails(models.Model):
    _name = 'court.details'
    _description = 'Court Information'

    name = fields.Char(required=True)
    is_active = fields.Boolean(default=True)
