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
import io

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
        # Hot lead split
    percent_hot_senior = fields.Integer(string="Hot % - Senior", default=60)
    percent_hot_junior = fields.Integer(string="Hot % - Junior", default=30)
    percent_hot_trainee = fields.Integer(string="Hot % - Trainee", default=10)

    # Warm lead split
    percent_warm_senior = fields.Integer(string="Warm % - Senior", default=20)
    percent_warm_junior = fields.Integer(string="Warm % - Junior", default=40)
    percent_warm_trainee = fields.Integer(string="Warm % - Trainee", default=40)

    @api.constrains('percent_hot_senior', 'percent_hot_junior', 'percent_hot_trainee',
                    'percent_warm_senior', 'percent_warm_junior', 'percent_warm_trainee')
    def _check_percentage_total(self):
        for rec in self:
            hot_total = rec.percent_hot_senior + rec.percent_hot_junior + rec.percent_hot_trainee
            warm_total = rec.percent_warm_senior + rec.percent_warm_junior + rec.percent_warm_trainee
            if hot_total != 100:
                raise UserError("Hot lead distribution must total 100%.")
            if warm_total != 100:
                raise UserError("Warm lead distribution must total 100%.")
    @api.onchange('file')
    def _onchange_file(self):
        if self.filename:
            base, ext = os.path.splitext(self.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.saved_filename = f"{base}_{timestamp}{ext}"


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
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            s3.download_fileobj(S3_BUCKET, s3_key, tmp)
            tmp.flush()
            os.fsync(tmp.fileno())  # Ensure data is fully written to disk
            tmp_path = tmp.name

        try:
            return self.process_uploaded_leads(tmp_path, import_type) if import_type == 'lead' else self.process_uploaded_opportunity(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    
    def process_uploaded_leads(self, file_path,import_type):
        team_name = 'Online Sales Team' if import_type == 'lead' else 'Offline Sales Team'
        online_team = self.env['crm.team'].search([('name', '=', team_name)], limit=1)
        assigned_users = online_team.member_ids.ids
        user_count = len(assigned_users)

        header_map, data_rows = self._load_excel(import_type,file_path)
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
            name, email,whatsapp_no = row[header_map['name']], row[header_map['email']], row[header_map['whatsapp_no']]
            assigned_user_id = assigned_users[index % user_count]

            leads_to_create.append({
                'name': name, 'phone': phone, 'email_from': email,
                'user_id': assigned_user_id, 'type': 'lead','whatsapp_no': whatsapp_no
            })
            duplicate_records.add(phone)
            index += 1

            if len(leads_to_create) >= 500:
                imported += self._create_leads_and_activities(leads_to_create)
                leads_to_create, activities_to_create = [], []

        # Create activities for existing leads
        self.create_followup_activities(existing_leads, summary="Second Time - Recall", days=1)

        # Final batch processing
        if leads_to_create:
            imported += self._create_leads_and_activities(leads_to_create)

        os.remove(file_path)
        _logger.info(f"Leads imported: {imported}, Duplicates: {duplicates}, Existing Leads: {len(existing_leads)}")
        return {
            'imported': imported,
            'existing_leads': len(existing_leads),
            'duplicates': duplicates
        }

    def process_uploaded_opportunity(self, file_path):
        self = self.with_env(self.env(user=SUPERUSER_ID))

        team_name = 'Offline Sales Team'
        offline_team = self.env['crm.team'].search([('name', '=', team_name)], limit=1)
        assigned_users = offline_team.member_ids.ids
        user_count = len(assigned_users)

        if not assigned_users:
            raise UserError(f"No members found in team: {team_name}")

        header_map, data_rows = self._load_excel(file_path)
        phones_to_process = self._extract_phones(data_rows, header_map)
        existing_leads = self.env['crm.lead'].search([
            ('phone', 'in', list(phones_to_process)),
            ('type', '=', 'lead')
        ])
        existing_lead_map = {self.normalize_phone(lead.phone): lead for lead in existing_leads}

        # Prepare tag cache: hot, warm, cold
        tag_cache = {}
        for tag_label in ['hot', 'warm', 'cold']:
            tag = self.env['crm.tag'].search([('name', '=', tag_label)], limit=1)
            if not tag:
                tag = self.env['crm.tag'].create({'name': tag_label})
            tag_cache[tag_label] = tag

        updated, skipped, created, index = 0, 0, 0,0

        for row in data_rows:
            try:
                raw_phone = row[header_map.get('phone', '')]
                if not raw_phone:
                    skipped += 1
                    continue

                phone = self.normalize_phone(raw_phone)
                lead = existing_lead_map.get(phone)

                category_value = row[header_map['category']].strip().lower()
                if category_value not in tag_cache:
                    tag = self.env['crm.tag'].search([('name', '=', category_value)], limit=1)
                    if not tag:
                        tag = self.env['crm.tag'].create({'name': category_value})
                    tag_cache[category_value] = tag
                category_tag = tag_cache.get(category_value)
                if not lead:
                    lead = self.env['crm.lead'].create({
                        'name': row[header_map['name']],
                        'phone': phone,
                        'type': 'opportunity',
                        'sugar_level': row[header_map['sugar_level']],
                        'status': row[header_map['stage']],
                        'access_batch_code_full': row[header_map['batch_code']],
                        'user_id': assigned_users[index % user_count],
                    })
                    created += 1
                else:
                # Add tag only if not already linked
                    lead.write({
                        'type': 'opportunity',
                        'sugar_level': row[header_map['sugar_level']],
                        'status': row[header_map['stage']],
                        'access_batch_code_full': row[header_map['batch_code']],
                        'user_id': assigned_users[index % user_count],
                    })
                    updated += 1
                if category_tag.id not in lead.tag_ids.ids:
                        lead.write({'tag_ids': [(4, category_tag.id)]})

                # Follow-up activity in 48 hours
                self.env['mail.activity'].create({
                    'res_model_id': self.env['ir.model']._get_id('crm.lead'),
                    'res_id': lead.id,
                    'activity_type_id': self.env.ref('mail.mail_activity_data_call').id,
                    'summary': "Post Conversion Follow-up",
                    'user_id': lead.user_id.id,
                    'date_deadline': fields.Date.today() + timedelta(days=2),
                })

                index += 1

                if updated % 100 == 0:
                    _logger.info(f"Updated {updated} leads...")

            except Exception as e:
                _logger.warning(f"Error processing row: {e}")
                skipped += 1
                continue

        os.remove(file_path)
        _logger.info(f"Conversion complete. Updated: {updated}, Skipped: {skipped}, Existing leads found: {len(existing_leads)}")

        return {
            'updated': updated,
            'skipped': skipped,
            'created': created,
            'existing_leads': len(existing_leads),
        }

    def _load_excel(self,import_type, file_path):
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active
        header_row = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
        header_map = {header.lower().strip(): idx for idx, header in enumerate(header_row)}

        required_cols = ['name', 'phone', 'email', 'whatsapp_no'] if import_type == 'lead' else ['name', 'phone', 'category', 'sugar_level', 'stage', 'batch_code']
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

    def _create_leads_and_activities(self, leads_data):
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
        if len(activities_to_create) >= 500:
                Activity.create(activities_to_create)
                activities_to_create = []
        if activities_to_create:
            Activity.create(activities_to_create)

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