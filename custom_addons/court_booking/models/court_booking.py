from odoo import models, fields

class CourtBooking(models.Model):
    _name = 'court.booking'
    _description = 'Court Booking'

    member_id = fields.Many2one('res.partner', string='Member', required=True)
    court_id = fields.Many2one('court.details', string='Court', required=True)
    slot_id = fields.Many2one('court.time.slot', string='Time Slot', required=True)
    booking_date = fields.Date(required=True)
    racket_qty = fields.Integer(string="Rackets", default=1)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid')
    ], default='draft')
