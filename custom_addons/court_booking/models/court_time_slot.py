from odoo import models, fields

class CourtTimeSlot(models.Model):
    _name = 'court.time.slot'
    _description = 'Time Slot'

    name = fields.Char(required=True)
    code = fields.Char()
    start_time = fields.Float()
    end_time = fields.Float()
    is_active = fields.Boolean(default=True)
