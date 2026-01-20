from odoo import fields, models

class PosConfig(models.Model):
    _inherit = "pos.config"

    whatsapp_auto_send_receipt = fields.Boolean(
        string="Auto-send WhatsApp receipt after payment",
        default=False,
    )

    whatsapp_receipt_message = fields.Char(
        string="WhatsApp receipt message",
        default="Thank you! Your receipt is attached.",
    )

    whatsapp_template_id = fields.Many2one(
        "mail.whatsapp.template",
        string="WhatsApp Receipt Template",
        domain="[('state','=','approved'),('is_supported','=',True)]",
        help="Template used when sending POS receipt via WhatsApp",
    )
    upi_payee_vpa = fields.Char(
        string="UPI Payee ID (VPA)",
        help="Example: doneztech@okaxis (the UPI ID / VPA that receives payments)"
    )
    upi_payee_name = fields.Char(
        string="UPI Payee Name",
        help="Example: DoneZ Tech"
    )
