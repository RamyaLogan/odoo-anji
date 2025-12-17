from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    company_type = fields.Selection(
        [
            ('it', 'IT'),
            ('non_it', 'Non-IT'),
        ],
        string='Company Type',
        required=True
    )
