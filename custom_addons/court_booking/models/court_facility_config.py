from odoo import models, fields

class CourtFacilityConfig(models.Model):
    _name = 'court.facility.config'
    _description = 'Court Facility Settings'

    name = fields.Char(default="Court Facility", readonly=True)
    total_rackets = fields.Integer(default=10)
    max_rackets_per_booking = fields.Integer(default=4)
    max_bookings_per_slot = fields.Integer(default=2)
