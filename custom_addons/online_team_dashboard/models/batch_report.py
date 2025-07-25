import io
from odoo import models, fields, api
from datetime import datetime,timedelta
import pandas as pd
from io import BytesIO
import base64
import logging
_logger = logging.getLogger(__name__)

class DashboardCustomBatchReport(models.TransientModel):
    _name = 'batch.report'
    _description = 'Email Batch Report Using Dashboard Logic'

    @api.model
    def run_batch_summary_cron(self):
        _logger.info("📧 [Batch Report Cron] Triggered...")

        today = fields.Date.today()
        dashboard_model = self.env['online.team.dashboard']
        offline_dashboard_model = self.env['offline.team.dashboard']
        if today.weekday() not in [1, 5]:
            _logger.info("📅 Today is not Tuesday or Saturday, skipping email send.")
            return

        for i in range(1, 8):
            date = today - timedelta(days=i)
            if date.weekday() in [1, 5]:  # Tuesday or Saturday
                import_day = date
                _logger.info("✅ Found Tuesday/Saturday: %s", import_day)
                break
        else:
            _logger.info("❌ No Tuesday/Saturday found in the past 7 days.")
            return
            
        start = datetime.combine(import_day, datetime.min.time())
        end = datetime.combine(import_day, datetime.max.time())

        batch_lines = self.env['lead.import.batch'].search([
            ('import_date', '>=', start),
            ('import_date', '<=', end)
        ])

        # Deduplicate batch codes using set(), then convert back to list (if needed)
        online_batch_codes = list(set(batch_lines.filtered(lambda b: b.import_type == 'lead').mapped('name')))
        offline_batch_codes = list(set(batch_lines.filtered(lambda b: b.import_type == 'opportunity').mapped('name')))
        selected_leads = self.env['crm.lead'].search([
            ('type', '=', 'lead'),
            ('batch_code_full', '=', online_batch_codes),
        ])
        _logger.info("✅ Selected batch_code: %s with %d leads", online_batch_codes, len(selected_leads))

        if not selected_leads:
            _logger.info("❌ No leads found in the last 10 days.")
            return

        _logger.info("✅ Found %s leads for batch code: %s", len(selected_leads), online_batch_codes)
        

        summary, user_map, status_counter = dashboard_model._aggregate_leads(selected_leads)
        leaderboard, _ = dashboard_model._compute_user_stats(user_map, [])
        status_data = dashboard_model._compute_status_distribution(status_counter)
        attachment = self._generate_excel_attachment(summary, leaderboard, status_data)

        selected_offline_leads = self.env['crm.lead'].search([
            ('type', '=', 'opportunity'),
            ('batch_code_full', '=', offline_batch_codes),
        ])
        _logger.info("✅ Selected batch_code: %s with %d offline leads", offline_batch_codes, len(selected_offline_leads))

        if not selected_offline_leads:
            _logger.info("❌ No leads found in the last 10 days.")
            return

        _logger.info("✅ Found %s leads for batch code: %s", len(selected_offline_leads), offline_batch_codes)
        

        offline_summary, offline_user_map, offline_batch_map, offline_status_counter = offline_dashboard_model._aggregate_leads(selected_offline_leads)
        offline_leaderboard, _ = offline_dashboard_model._compute_user_stats(offline_user_map, [])
        offline_status_data = offline_dashboard_model._compute_status_distribution(offline_status_counter)
        offline_batch_aggregation_table, offline_batch_payment_chart = offline_dashboard_model._format_batch_stats(offline_batch_map)

        offline_attachment = self._generate_offline_excel_attachment(offline_summary, offline_leaderboard, offline_status_data,offline_batch_aggregation_table,offline_batch_payment_chart)



        template = self.env.ref('online_team_dashboard.batch_report_email_template')
        ctx = {
            'batch_code': ', '.join(online_batch_codes + offline_batch_codes),
            'summary': summary,
            'leaderboard': leaderboard,
            'status_data': status_data,
        }
        template.with_context(ctx).send_mail(self.id, force_send=True,email_values={'attachment_ids': [attachment.id,offline_attachment.id]})
        _logger.info("📤 Email sent using template: %s", template.name)
    

    def _generate_excel_attachment(self, summary, leaderboard, status_data):
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            pd.DataFrame([summary]).to_excel(writer, index=False, sheet_name='Summary')
            pd.DataFrame(leaderboard).to_excel(writer, index=False, sheet_name='Leaderboard')
            pd.DataFrame(status_data).to_excel(writer, index=False, sheet_name='Status')

        buffer.seek(0)
        attachment = self.env['ir.attachment'].create({
            'name': f'Batch_Report_Online_{fields.Date.today()}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(buffer.read()),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return attachment

    def _generate_offline_excel_attachment(self, summary, leaderboard, status_data,offline_batch_aggregation_table,offline_batch_payment_chart):
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            pd.DataFrame([summary]).to_excel(writer, index=False, sheet_name='Summary')
            pd.DataFrame(leaderboard).to_excel(writer, index=False, sheet_name='Leaderboard')
            pd.DataFrame(status_data).to_excel(writer, index=False, sheet_name='Status')
            pd.DataFrame(offline_batch_aggregation_table).to_excel(writer, index=False, sheet_name='Batch Aggregation')
            pd.DataFrame(offline_batch_payment_chart).to_excel(writer, index=False, sheet_name='Batch Payment')

        buffer.seek(0)
        attachment = self.env['ir.attachment'].create({
            'name': f'Batch_Report_Offline_{fields.Date.today()}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(buffer.read()),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return attachment