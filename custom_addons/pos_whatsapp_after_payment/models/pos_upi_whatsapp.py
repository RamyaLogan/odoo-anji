# models/pos_upi_whatsapp.py
import base64
from odoo import models, _
from odoo.exceptions import UserError

class PosUpiWhatsapp(models.AbstractModel):
    _name = "pos.upi.whatsapp"
    _description = "POS UPI WhatsApp Sender"

    def send_upi_qr(self, mobile, upi_uri, qr_png_base64):
        if not mobile:
            raise UserError(_("Customer mobile missing"))

        gateway = self.env["mail.gateway"].search(
            [("gateway_type", "=", "whatsapp")], limit=1
        )
        if not gateway:
            raise UserError(_("No WhatsApp gateway configured"))

        partner = self.env["res.partner"].search(
            ["|", ("mobile", "=", mobile), ("phone", "=", mobile)],
            limit=1,
        )
        if not partner:
            raise UserError(_("Customer not found"))

        channel = partner._whatsapp_get_channel(
            "mobile" if partner.mobile else "phone",
            gateway
        )

        attachments = []
        if qr_png_base64:
            attachments.append(("upi_qr.png", base64.b64decode(qr_png_base64)))

        channel.message_post(
            body=_("Please pay using the UPI QR / link:\n%s") % upi_uri,
            attachments=attachments,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        return True