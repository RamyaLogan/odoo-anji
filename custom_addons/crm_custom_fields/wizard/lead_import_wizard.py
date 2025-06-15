from odoo import models, fields, api,SUPERUSER_ID
from odoo.exceptions import UserError
from openpyxl import load_workbook
import base64
import os
import logging
from datetime import datetime
import openpyxl
from dateutil.relativedelta import relativedelta
from psycopg2.extras import execute_values
from odoo.api import Environment
import psycopg2
from odoo.modules.registry import Registry
import boto3

S3_BUCKET = 'mhs-doneztech'
S3_PREFIX = 'crm-imports/' 
_logger = logging.getLogger(__name__)

class LeadImportWizard(models.TransientModel):
    _name = 'lead.import.wizard'
    _description = 'Lead Import Wizard'

    file = fields.Binary('Excel File', required=True)
    filename = fields.Char('File Name')
    saved_filename = fields.Char('Saved File Name', readonly=True)
    import_type = fields.Selection([('lead', 'Lead'), ('opportunity', 'Opportunity')],default='lead',
        string='Import Type',
        invisible=True,)


    @api.onchange('file')
    def _onchange_file(self):
        if self.filename:
            base, ext = os.path.splitext(self.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.saved_filename = f"{base}_{timestamp}{ext}"
import boto3

S3_BUCKET = 'your-bucket-name'
S3_PREFIX = 'crm-imports/'  # optional prefix/folder

    def action_import_leads(self):
        s3 = boto3.client('s3')
        for record in self:
            if record.file and record.filename:
                base, ext = os.path.splitext(record.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                s3_key = f"{S3_PREFIX}{base}_{timestamp}{ext}"

                decoded_file = base64.b64decode(record.file)
                s3.upload_fileobj(io.BytesIO(decoded_file), S3_BUCKET, s3_key)

                # Trigger the job with the S3 path
                self.env['lead.import.wizard'].with_delay(description="CRM S3 Import").process_uploaded_leads_from_s3(s3_key, self.import_type)
    
    @api.model
    def process_uploaded_leads_from_s3(self, s3_key, import_type):
        import tempfile
        s3 = boto3.client('s3')
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            s3.download_fileobj(S3_BUCKET, s3_key, tmp)
            tmp_path = tmp.name

        try:
            return self.process_uploaded_leads(tmp_path, import_type)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    
    def process_uploaded_leads(self, file_path,import_type):
        team_name = 'Online Sales Team' if import_type == 'lead' else 'Offline Sales Team'
        online_team = self.env['crm.team'].search([('name', '=', team_name)], limit=1)
        assigned_users = online_team.member_ids.ids
        user_count = len(assigned_users)

        header_map, data_rows = self._load_excel(file_path)
        phones_to_import = self._extract_phones(data_rows, header_map)
        existing_leads = self.env['crm.lead'].search([('phone', 'in', list(phones_to_import))])
        existing_phones = set(self.normalize_phone(p) for p in existing_leads.mapped('phone'))

        leads_to_create, activities_to_create = [], []
        duplicate_records, imported, duplicates, index = set(), 0, 0, 0
        for row in data_rows:
            phone = self.normalize_phone(row[header_map['phone']])
            if not phone or phone in existing_phones:
                continue
            if phone in duplicate_records:
                duplicates += 1
                continue
            name, source, age = row[header_map['name']], row[header_map['source']], self._safe_int(row[header_map['age']])
            assigned_user_id = assigned_users[index % user_count]

            leads_to_create.append({
                'name': name, 'phone': phone, 'age': age, 'import_source': source,
                'user_id': assigned_user_id, 'type': 'lead',
            })
            duplicate_records.add(phone)
            index += 1

            if len(leads_to_create) >= 500:
                imported += self._create_leads_and_activities(leads_to_create, activities_to_create)
                leads_to_create, activities_to_create = [], []

        # Create activities for existing leads
        self.create_followup_activities(existing_leads, summary="Second Time - Recall", days=1)

        # Final batch processing
        if leads_to_create:
            imported += self._create_leads_and_activities(leads_to_create, activities_to_create)

        if activities_to_create:
            self.env['mail.activity'].create(activities_to_create)

        os.remove(file_path)
        _logger.info(f"Leads imported: {imported}, Duplicates: {duplicates}, Existing Leads: {len(existing_leads)}")
        return {
            'imported': imported,
            'existing_leads': len(existing_leads),
            'duplicates': duplicates
        }

    def _load_excel(self, file_path):
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active
        header_row = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
        header_map = {header.lower().strip(): idx for idx, header in enumerate(header_row)}

        required_cols = ['name', 'phone', 'source', 'age']
        for col in required_cols:
            if col not in header_map:
                raise UserError(f"Missing required column: {col}")

        data_rows = list(sheet.iter_rows(min_row=2, values_only=True))
        return header_map, data_rows

    def _extract_phones(self, data_rows, header_map):
        phones = set()
        for row in data_rows:
            try:
                phone = row[header_map['phone']]
                if phone:
                    phones.add(self.normalize_phone(phone))
            except IndexError:
                continue
        return phones

    def _safe_int(self, val):
        try:
            return int(val)
        except:
            return 0

    def _create_leads_and_activities(self, leads_data, activities_buffer,activity_type_id):
        created = self.env['crm.lead'].create(leads_data)
        self.create_followup_activities(created, summary="Follow Up Call", days=1)
        return len(created)

    def create_followup_activities(self, leads, summary='Second Time - Recall', days=1):
        Activity = self.env['mail.activity'].sudo().with_context(mail_notrack=True, tracking_disable=True, mail_create_nolog=True)
        crm_model_id = self.env['ir.model']._get_id('crm.lead')
        activity_type = self.env.ref('mail.mail_activity_data_call')
        deadline = fields.Date.context_today(self) + relativedelta(days=days)

        activities_to_create = []
        for lead in leads:
            activities_to_create.append({
                'res_model_id': crm_model_id,
                'res_id': lead.id,
                'activity_type_id': activity_type.id,
                'summary': summary,
                'user_id': lead.user_id.id,
                'date_deadline': deadline,
            })
        BATCH_SIZE = 500
        self.env['mail.activity'].sudo().create(activities_to_create)
        for i in range(0, len(activities_to_create), BATCH_SIZE):
            batch = activities_to_create[i:i+BATCH_SIZE]
            self.bulk_insert_activities(batch)
            """ if len(activities_to_create) >= 500:
                Activity.create(activities_to_create)
                activities_to_create = []
        if activities_to_create:
            Activity.create(activities_to_create) """

    def _prepare_activity(self, lead, user_id,summary, activity_type_id):
        return {
            'res_model_id': self.env['ir.model']._get_id('crm.lead'),
            'res_id': lead.id,
            'activity_type_id': activity_type_id,
            'summary': summary,
            'user_id': user_id,
            'date_deadline': fields.Date.context_today(self) + relativedelta(days=1),
        }

    @api.model
    def bulk_insert_activities(self, activity_data):
        """Efficient SQL insert into mail.activity using psycopg2 with a fresh environment."""
        registry = Registry(self.env.cr.dbname)
        with registry.cursor() as new_cr:
            new_env = Environment(new_cr, SUPERUSER_ID, self.env.context)

            model_id = new_env['ir.model']._get_id('crm.lead')
            now = fields.Datetime.now()

            values = [
                (
                    data['res_model_id'],
                    data['res_id'],
                    data['activity_type_id'],
                    data['summary'],
                    data['user_id'],
                    data['date_deadline'],
                    SUPERUSER_ID,
                    now,
                    SUPERUSER_ID,
                    now
                )
                for data in activity_data
            ]

            if not values:
                return

            query = """
                INSERT INTO mail_activity (
                    res_model_id, res_id, activity_type_id, summary, user_id,
                    date_deadline, create_uid, create_date, write_uid, write_date
                ) VALUES %s
            """

            execute_values(new_cr, query, values)
            new_cr.commit()

        # Notify UI to reflect changes
        notifications = [
            ['mail.activity', data['res_id'], {'type': 'activity_updated'}]
            for data in activity_data
        ]
        self.env['bus.bus']._sendmany(notifications)
        
    def normalize_phone(self,phone):
        return ''.join(filter(str.isdigit, str(phone).strip()))

    def is_valid_phone(self, phone):
        return True
        # try:
        #     parsed = phonenumbers.parse(phone, None)
        #     return phonenumbers.is_valid_number(parsed)
        # except:
        #     return False