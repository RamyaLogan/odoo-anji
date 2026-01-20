import base64
import logging
from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    @classmethod
    def action_send_upi_payment_whatsapp(cls, mobile, upi_uri, qr_png_base64):
        """
        Send UPI QR / link on WhatsApp WITHOUT needing a POS order.
        """
        env = cls.env if hasattr(cls, "env") else cls._cr.env

        if not mobile:
            raise UserError(_("Customer mobile number is required."))

        gateway = env["mail.gateway"].search(
            [("gateway_type", "=", "whatsapp")], limit=1
        )
        if not gateway:
            raise UserError(_("No WhatsApp gateway configured."))

        # create / get whatsapp channel directly by mobile
        channel = env["mail.channel"]._whatsapp_get_channel_by_number(
            mobile, gateway
        )
        if not channel:
            raise UserError(_("Could not create WhatsApp channel."))

        attachments = []
        if qr_png_base64:
            attachments.append((
                "upi-payment.png",
                base64.b64decode(qr_png_base64),
            ))

        body = _(
            "Please pay using the UPI QR or link below:\n\n%s"
        ) % (upi_uri or "")

        channel.message_post(
            body=body,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            attachments=attachments,
        )

        return True

    def action_send_receipt_whatsapp(self, ticket_image, basic_image):
        """WhatsApp-only send triggered by POS Receipt screen button."""
        self.ensure_one()

        config = self.config_id
        if not config or not config.whatsapp_auto_send_receipt:
            raise UserError(_("WhatsApp receipt sending is disabled in POS Settings."))

        partner = self.partner_id
        if not partner:
            raise UserError(_("Please select a customer before sending WhatsApp receipt."))

        gateway = self.env["mail.gateway"].search([("gateway_type", "=", "whatsapp")], limit=1)
        if not gateway:
            raise UserError(_("No WhatsApp gateway configured."))

        number_field = "mobile" if partner.mobile else "phone"
        if not getattr(partner, number_field):
            raise UserError(_("Customer has no phone/mobile number."))

        channel = partner._whatsapp_get_channel(number_field, gateway)
        if not channel:
            raise UserError(_("Could not create WhatsApp channel for this customer."))

        attachments = []
        if ticket_image:
            _logger.warning("[WA][POS] Ticket image size: %s bytes", len(ticket_image))
            attachments.append((f"{self.name}-ticket.png", base64.b64decode(ticket_image)))
        if basic_image:
            _logger.warning("[WA][POS] Ticket image size: %s bytes", len(basic_image))
            attachments.append((f"{self.name}-basic.png", base64.b64decode(basic_image)))

        inv = self._whatsapp_build_invoice_attachment_tuple()
        if inv:
            attachments.append(inv)
        ctx = dict(self.env.context)
        template = getattr(config, "whatsapp_template_id", False)
        if template:
            ctx["whatsapp_template_id"] = template.id

        body = config.whatsapp_receipt_message or _("Thank you! Your receipt is attached.")

        _logger.warning("[WA][POS] Button send: channel=%s order=%s partner=%s attachments=%s",
                        channel.display_name, self.name, partner.display_name, [a[0] for a in attachments])

        channel.with_context(ctx).message_post(
            body=body,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            attachments=attachments,
        )

        return True

    def _pos_get_invoice_move(self):
        """Return account.move invoice for this POS order, or False."""
        self.ensure_one()

        # Try common links (varies by version/customization)
        for fname in ("account_move", "invoice_id", "account_move_id"):
            if hasattr(self, fname):
                move = getattr(self, fname)
                if move:
                    return move

        # Fallback: search by origin/reference
        move = self.env["account.move"].search(
            [
                ("invoice_origin", "=", self.name),
                ("move_type", "in", ("out_invoice", "out_refund")),
            ],
            order="id desc",
            limit=1,
        )
        return move or False

    def _whatsapp_build_invoice_attachment_tuple(self):
        """Return (filename, pdf_bytes) or False."""
        self.ensure_one()

        move = self._pos_get_invoice_move()
        if not move:
            return False

        # Try "with payments" first, then normal invoice
        for report_ref in ("account.report_invoice_with_payments", "account.report_invoice"):
            try:
                pdf_bytes, _ = self.env["ir.actions.report"]._render_qweb_pdf(
                    report_ref,
                    res_ids=move.ids,
                )
                filename = f"Invoice {move.name or move.display_name}.pdf"
                return (filename, pdf_bytes)
            except Exception:
                _logger.exception("[WA][POS] Failed rendering invoice report_ref=%s move=%s", report_ref, move.id)

        return False
