from odoo import models, fields, api

class CrmCallLead(models.Model):
    _inherit = "crm.lead"

    masked_phone = fields.Char(string='Phone', compute='_compute_masked_phone')
    import_source = fields.Char(string='Lead Source')
    age = fields.Integer(string='Age')
    sugar_level = fields.Selection([
        ('120-150', '120-150'),
        ('150-200', '150-200'),
        ('200-250', '200-250'),
        ('250-300', '250-300'),
        ('>300', '>300')
    ], string='Sugar Level')
    available_for_webinar = fields.Boolean(string="Available for Webinar")
    treatment_status = fields.Selection([
        ('yes','Yes'),
        ('no','No')
    ], string="Treatment Status", default='no')
    webinar_attended = fields.Selection([
        ('yes','Yes'),
        ('no','No')
    ], string="Webinar Attended", default='no')
    call_status = fields.Selection([
        ('dnp', 'DNP'),
        ('follow_up', 'Follow Up'),
        ('disqualified', 'Disqualified')
    ], string="Call Status")
    language = fields.Selection([
        ('tamil','Tamil'),
        ('english', 'English'),
        ('hindi', 'Hindi'),
        ('telugu', 'Telugu'),
        ('malayalam', 'Malayalam'),
        ('other', 'Other')
    ], string="Language")
    occupation = fields.Selection([
        ('house_wife', 'House Wife'),
        ('it', 'IT'),
        ('student', 'Student'),
        ('retired', 'Retired'),
        ('other','Other')], string="Occupation"
    )
    gender = fields.Selection([
        ('male','Male'),
        ('female','Female')
    ],string="Gender")

    payment_status = fields.Selection([
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
    ],  string="Payment Status")

    payment_date = fields.Date(string="Payment Date")
    payment_reference = fields.Char(string="Payment Reference")
    payment_amount = fields.Float(string="Payment Amount")
    payment_mode = fields.Selection([
        ('tagmango', 'Tag Mango'),
        ('razorpay', 'Razor Pay'),
        ('upi', 'UPI'),
    ],  string="Payment Mode")
    access_batch_code = fields.Char(string='Access Batch Code')
    next_payment_date = fields.Date(string="Next Partial Payment Date")

    @api.model
    def create_payment_followup_activity(self):
        for lead in self:
            if lead.next_payment_date:
                lead.activity_schedule(
                    'mail.activity_data_call',
                    date_deadline=lead.next_payment_date,
                    summary='Follow-up for next payment installment',
                    note='Reminder: collect partial payment today.'
                )

    def _compute_masked_phone(self):
        for rec in self:
            if rec.phone:
                rec.masked_phone = rec.phone[:2] + '******' + rec.phone[-2:]
            else:
                rec.masked_phone = ''

    def write(self, vals):
        res = super().write(vals)
        if 'next_payment_date' in vals:
            self.create_payment_followup_activity()
        return res

    def action_trigger_smartflo_call(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.client",
            "tag": "smartflo_initiate_call",
            "target": "new",
            "params": {
                "phone": self.phone, 
                "lead_name": self.name,
                "lead_id": self.id,
            },
        }
        return action

    def action_call_lead(self):
        # This method is called when the user clicks the "Call Lead" button
        for lead in self:
            if lead.phone:
                # Open the phone dialer with the lead's phone number
                return {
                    'type': 'ir.actions.act_url',
                    'url': f'tel:{lead.phone}',
                    'target': 'self',
                }
            else:
                raise UserError("No phone number available for this lead.")
