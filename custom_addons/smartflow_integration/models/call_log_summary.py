from odoo import models, fields

class CallLogSummary(models.Model):
    _name = "call.log.summary"
    _description = "Daily Call Duration Summary"

    user_id = fields.Many2one("res.users", required=True, index=True)
    date = fields.Date(required=True, index=True)
    total_calls = fields.Integer(default=0)
    total_duration = fields.Float(default=0.0, help="Total call duration in minutes")

    _sql_constraints = [
        ('unique_user_date', 'unique(user_id, date)', 'One summary per user per day!')
    ]