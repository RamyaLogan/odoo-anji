from odoo import models, fields, api
from datetime import timedelta

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
            ('follow_up', 'Follow Up'),
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
    ],  string="Payment Status", track_visibility='onchange')

    payment_date = fields.Date(string="Payment Date", track_visibility='onchange')
    payment_reference = fields.Char(string="Payment Reference", track_visibility='onchange')
    payment_amount = fields.Float(string="Payment Amount", track_visibility='onchange')
    payment_mode = fields.Selection([
        ('tagmango', 'Tag Mango'),
        ('razorpay', 'Razor Pay'),
        ('upi', 'UPI'),
    ],  string="Payment Mode", track_visibility='onchange')
    access_batch_code_full = fields.Char("Batch Code", required=False)

    access_batch_code = fields.Char(
        string="Access Batch Code",
        compute="_compute_access_batch_code",
        inverse="_inverse_access_batch_code",
        store=False
    )
    next_payment_date = fields.Date(string="Next Partial Payment Date",  track_visibility='onchange')
    follow_up_on = fields.Datetime(string="Next Follow Up Date")

    status = fields.Selection([('new','New L1'),
        ('walk_in','Walk In'),
        ('follow_up', 'Follow Up'),
        ('dnp', 'DNP'),
        ('not_interested','Not Interested'),
        ('disqualified','Disqualified'),     
        ('l1_basic_course_enrolled_fully_paid','L1 Basic Course Enrolled - Fully Paid'),
        ('l1_basic_course_enrolled_partially_paid','L1 Basic Course Enrolled - Partially Paid')],
        default="new",
        required=True,
        string="Status",
        group_expand='_group_expand_stage',track_visibility='onchange')

    remarks = fields.Text(string="Remarks")
    log_remarks = fields.Text(string="Remarks", track_visibility='onchange', compute='_compute_remarks')
    walk_in_date = fields.Datetime(string="Walk In Date")

    @api.depends('remarks')
    def _compute_remarks(self):
        for rec in self:
            if rec.status:
                rec.log_remarks = f"{rec.status} - {rec.remarks}"

    @api.onchange('status', 'payment_status')
    def _onchange_file(self):
        if self.status == 'l1_basic_course_enrolled_fully_paid' or self.payment_status == 'paid':
            self.payment_status = 'paid'
            self.status = 'l1_basic_course_enrolled_fully_paid'
        elif self.status == 'l1_basic_course_enrolled_partially_paid' or self.payment_status == 'partial':
            self.payment_status = 'partial'
            self.status = 'l1_basic_course_enrolled_partially_paid'

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
        return ['new', 'dnp', 'follow_up', 'disqualified', 'done']

    @api.model
    def _group_expand_stage(self, states, domain, order):
        return ['new',  'follow_up', 'walk_in', 'dnp', 'not_interested','l1_basic_course_enrolled_fully_paid', 'l1_basic_course_enrolled_partially_paid', 'disqualified' ]

    @api.model
    def create_payment_followup_activity(self):
        for lead in self:
            if lead.next_payment_date:
                lead.activity_schedule(
                    'mail.mail_activity_data_call',
                    date_deadline=lead.next_payment_date,
                    summary='Follow-up for next payment installment',
                    note='Reminder: collect partial payment today.'
                )

    def get_status_display(self,status,value):
        """Return the label of the current status selection."""
        return dict(self._fields[status].selection).get(value, '')

    @api.model
    def create_followup_activity(self):
        CallType = self.env.ref('mail.mail_activity_data_call')

        for lead in self:
            # 1) figure out which status and pick date + duration
            event_dt = None
            duration = None   # timedelta or None
            note     = None

            if lead.status == 'follow_up' and lead.follow_up_on:
                event_dt = lead.follow_up_on
                duration = timedelta(minutes=3)
                all_day   = False
                note     = f'Follow-up: {lead.remarks}' or 'Follow-up on lead'

            elif lead.status == 'dnp':
                # 48 hours from "now"
                event_dt = fields.Datetime.now() + timedelta(hours=48)
                all_day   = True
                note     = f'DNP: {lead.remarks}' or 'DNP follow-up'

            elif lead.status == 'walk_in' and lead.walk_in_date:
                event_dt = lead.walk_in_date
                all_day   = False
                duration = timedelta(minutes=30)
                note     = f'Walk-in: {lead.remarks}' or 'Walk-in Booking'

            elif lead.status == 'l1_basic_course_enrolled_partially_paid' and  lead.next_payment_date:
                # combine date + midnight
                event_dt = lead.next_payment_date
                all_day   = True
                note     = f'Payment Reminder: {lead.remarks}' or 'Partial payment reminder'

            else:
                continue
            self.create_activity(lead, CallType, event_dt, duration, note,all_day,'status',lead.status)
        

    def create_activity(self,lead,CallType, event_dt, duration, note,all_day,status,status_value):
        activity = lead.activity_schedule(
                activity_type_id=CallType.id,
                date_deadline=event_dt,
                summary=f"{lead.get_status_display(status,status_value)} for {lead.name}",
                note=note,
            )

            # 3) create the calendar.event
        event_vals = {
            'name':        f"{lead.get_status_display(status,status_value)}: {lead.name}",
            'allday':      all_day,
            'user_id':     lead.user_id.id or self.env.uid,
            'partner_ids': [(4, lead.user_id.partner_id.id)] if lead.user_id.partner_id else [],
            'res_model':   'crm.lead',
            'res_model_id':     self.env['ir.model']._get('crm.lead').id,
            'res_id':      lead.id,
            'opportunity_id': lead.id,
        }
        
        if duration:
            start_dt = event_dt
            stop_dt  = event_dt + duration
            event_vals.update({
                'start': start_dt,
                'stop':  stop_dt,
            })
        else:
            # Only change here: guard against calling .date() on a date
            if hasattr(event_dt, 'date'):
                sd = event_dt.date()
            else:
                sd = event_dt
            event_vals.update({
                'start_date': sd.isoformat(),
                'stop_date':  sd.isoformat(),
            })

        # otherwise Odoo will treat it as an allday event on start.date()

        event = self.env['calendar.event'].create(event_vals)

        # 4) link & close the activity
        activity.write({'calendar_event_id': event.id})

    @api.model
    def create_followup_activity_online_team(self):
        CallType = self.env.ref('mail.mail_activity_data_call')

        for lead in self:
            # 1) figure out which status and pick date + duration
            event_dt = None
            duration = None   # timedelta or None
            note     = None

            if lead.call_status == 'follow_up' and lead.follow_up_on:
                event_dt = lead.follow_up_on
                duration = timedelta(minutes=3)
                all_day   = False
                note     = f'Follow-up: {lead.remarks}' or 'Follow-up on lead'

            elif lead.call_status == 'dnp':
                # 48 hours from "now"
                event_dt = fields.Datetime.now() + timedelta(hours=48)
                all_day   = True
                note     = f'DNP: {lead.remarks}' or 'DNP follow-up'

            else:
                continue

            self.create_activity(lead, CallType, event_dt, duration, note,all_day,'call_status',lead.call_status)
        

    def _compute_masked_phone(self):
        for rec in self:
            if rec.phone:
                rec.masked_phone = rec.phone[:2] + '******' + rec.phone[-2:]
            else:
                rec.masked_phone = ''

    def write(self, vals):
        res = super().write(vals)
                # Only trigger follow-up when relevant fields change
        trigger_fields = {'status', 'follow_up_on', 'walk_in_date', 'next_payment_date','call_status'}
        if trigger_fields & set(vals.keys()):
            self.create_followup_activity()
        if 'call_status' in vals:
            self.create_followup_activity_online_team()
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
