from odoo import fields, models,api
import logging
_logger = logging.getLogger(__name__)

class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    is_upi_qr = fields.Boolean(string="UPI QR Payment")

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        fields.append('is_upi_qr')
        _logger.warning("[WA][POS] Adding is_upi_qr to pos.payment.method load params")
        return fields