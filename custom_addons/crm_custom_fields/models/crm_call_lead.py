from odoo import models, fields, api

class CrmCallLead(models.Model):
    _inherit = 'crm.lead'

    payment_attachments = fields.Many2many(
        'ir.attachment', 
        'crm_lead_payment_attachment_rel', 
        'lead_id', 
        'attachment_id',
        string="Payment Attachments",
        domain="[('res_model','=','crm.lead'), ('res_id','=', id)]",
    )
    masked_phone = fields.Char(string='Phone', compute='_compute_masked_phone')
    whatsapp_no = fields.Char(string='Whatsapp No.')
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
    call_status = fields.Selection(
        [
            ('new', 'New'),
            ('dnp', 'DNP'),
            ('followup', 'Follow-up'),
            ('disqualified', 'Disqualified'),
            ('done', 'Done'),
        ],
        default="new",
        required=True,
        string="Call Status",
        group_expand='_group_expand_call_status'
    )
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
    access_batch_code_full = fields.Char("Batch Code", required=False)

    access_batch_code = fields.Char(
        string="Access Batch Code",
        compute="_compute_access_batch_code",
        inverse="_inverse_access_batch_code",
        store=False
    )
    next_payment_date = fields.Date(string="Next Partial Payment Date")

    @api.depends('access_batch_code_full')
    def _compute_access_batch_code(self):
        for rec in self:
            if rec.access_batch_code_full and rec.access_batch_code_full.startswith('DS'):
                rec.access_batch_code = rec.access_batch_code_full[2:]
            else:
                rec.access_batch_code = rec.access_batch_code_full or ''

    def _inverse_access_batch_code(self):
        for rec in self:
            if rec.access_batch_code:
                rec.access_batch_code_full = f'DS{rec.access_batch_code}'
            else:
                rec.access_batch_code_full = ''
    @api.model
    def _group_expand_call_status(self, states, domain, order):
        return ['new', 'dnp', 'followup', 'disqualified', 'done']

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
