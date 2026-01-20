from odoo import models
import logging
_logger = logging.getLogger(__name__)
_logger.warning("[WA][POS] pos_session.py imported ✅")

class PosSession(models.Model):
    _inherit = "pos.session"

    def _pos_ui_models_to_load(self):
        res = super()._pos_ui_models_to_load()
        return res

    def _loader_params_pos_payment_method(self):
        res = super()._loader_params_pos_payment_method()
        _logger.warning("[WA][POS] Adding is_upi_qr to pos.payment.method load params")
        res["search_params"]["fields"].append("is_upi_qr")
        return res