from odoo import models, fields

class LeadImportBatch(models.Model):
    _name = 'lead.import.batch'
    _description = 'Imported Batch Tracker'

    name = fields.Char("Batch Code", required=True)
    import_type = fields.Selection([('lead', 'Lead'), ('opportunity', 'Opportunity')], required=True)
    import_date = fields.Datetime("Imported At", default=fields.Datetime.now)