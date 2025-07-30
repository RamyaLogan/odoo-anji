from odoo import models, api, fields
from collections import defaultdict, Counter
from datetime import timedelta, datetime


class OfflineTeamDashboard(models.AbstractModel):
    _name = "offline.team.dashboard"
    _description = "Offline Team Dashboard"

    @api.model
    def get_dashboard_data(self, **filters):
        today = fields.Date.context_today(self)
        filters = filters or {}

        # -----------------------
        # Parse filters or default
        # -----------------------
        from_date = fields.Date.from_string(filters.get("from_date")) if filters.get("from_date") else today - timedelta(days=7)
        to_date = fields.Date.from_string(filters.get("to_date")) if filters.get("to_date") else today
        from_dt = datetime.combine(from_date, datetime.min.time())
        to_dt = datetime.combine(to_date, datetime.max.time())

        selected_user_ids = filters.get("selected_user_ids") or []
        tag_filters = filters.get("tags") or []  # list of lowercase tag names like ['hot', 'warm']
        batch_code = filters.get("batch_code")

        # -----------------------
        # Build domain filters
        # -----------------------
        domain = [
            ('type', '=', 'opportunity'),
            ('create_date', '>=', from_dt),
            ('create_date', '<=', to_dt),
        ]
        if selected_user_ids:
            domain.append(('user_id', 'in', selected_user_ids))
        if batch_code:
            batch_list = [b.strip() for b in batch_code.split(",") if b.strip()]
            if batch_list:
                domain.append(('batch_code_full', 'in', batch_list))

        # -----------------------
        # Fetch filtered leads
        # -----------------------
        leads = self.env['crm.lead'].search(domain)

        # -----------------------
        # Optional tag filtering
        # -----------------------
        if tag_filters:
            leads = leads.filtered(lambda l: any(tag.name.lower() in tag_filters for tag in l.tag_ids))

        # -----------------------
        # Remaining logic unchanged
        # -----------------------
        users = self._get_sales_users()
        all_user_ids = [u.id for u in self._get_sales_users()]
        call_logs = self._get_call_logs(from_date, to_date,selected_user_ids or all_user_ids)
        

        summary, user_leads_map, batch_map, status_counter = self._aggregate_leads(leads)
        summary["unassigned_count"] = summary["total_leads"] - summary["total_assigned"]

        leaderboard, touch_rate_data = self._compute_user_stats(user_leads_map, call_logs)
        status_pie_data = self._compute_status_distribution(status_counter)
        call_counts_by_date = self._compute_call_trends(call_logs)
        batch_aggregation_table, batch_payment_chart = self._format_batch_stats(batch_map)

        return {
            "from_date": from_date,
            "to_date": to_date,
            **summary,
            "table": leaderboard,
            "touch_rate_data": touch_rate_data,
            "call_counts_by_date": call_counts_by_date,
            "status_pie_data": status_pie_data,
            "batch_payment_chart": batch_payment_chart,
            "batch_enrollment_data": batch_aggregation_table,
            "users": [{"id": u.id, "name": u.name} for u in users],
        }

    def _get_leads(self, from_dt, to_dt):
        return self.env['crm.lead'].search([
            ('type', '=', 'opportunity'),
            ('create_date', '>=', from_dt),
            ('create_date', '<=', to_dt),
        ])

    def _get_call_logs(self, from_date, to_date, user_ids=None):
        domain = [
            ('date', '>=', from_date),
            ('date', '<=', to_date),
            ('user_id', 'in', user_ids),
        ]
        return self.env['call.log.summary'].search(domain)

    def _get_sales_users(self):
        team = self.env['crm.team'].search([('name', '=', 'Offline Sales Team')], limit=1)
        return team.member_ids if team else self.env['res.users']

    def _aggregate_leads(self, leads):
        touched_statuses = {
            'follow_up','diabetes_interested_in_webinar','diabetes_not_interested_in_webinar',
             'walk_in', 'dnp','l1_basic_course_enrolled_fully_paid', 'l1_basic_course_enrolled_partially_paid', 'disqualified'
        }

        summary = {
            "total_leads": 0,
            "total_assigned": 0,
            "total_touched": 0,
            "hot_leads": 0,
            "warm_leads": 0,
            "walk_in": 0,
            "total_enrolled": 0,
            "fully_paid": 0,
            "partially_paid": 0,
            "close_rate": 0.0,
        }

        user_leads_map = defaultdict(list)
        batch_map = defaultdict(lambda: {
            "lead_count": 0,
            "enrolled_count": 0,
            "fully_paid": 0,
            "partial_paid": 0
        })
        status_counter = Counter()

        for lead in leads:
            summary["total_leads"] += 1
            if lead.user_id:
                summary["total_assigned"] += 1
                user_leads_map[lead.user_id.id].append(lead)

            status = (lead.status or '').lower()
            status_counter[status] += 1

            if status in touched_statuses:
                summary["total_touched"] += 1
            if lead.status == 'walk_in':
                summary["walk_in"] += 1
            if lead.status == 'l1_basic_course_enrolled_fully_paid':
                summary["fully_paid"] += 1
                summary["total_enrolled"] += 1
            elif lead.status == 'l1_basic_course_enrolled_partially_paid':
                summary["partially_paid"] += 1
                summary["total_enrolled"] += 1

            if any(tag.name.lower() == 'hot' for tag in lead.tag_ids):
                summary["hot_leads"] += 1
            if any(tag.name.lower() == 'warm' for tag in lead.tag_ids):
                summary["warm_leads"] += 1

            batch = lead.batch_code_full or "No Batch"
            batch_data = batch_map[batch]
            batch_data["lead_count"] += 1
            if lead.status == 'l1_basic_course_enrolled_fully_paid':
                batch_data["fully_paid"] += 1
                batch_data["enrolled_count"] += 1
            elif lead.status == 'l1_basic_course_enrolled_partially_paid':
                batch_data["partial_paid"] += 1
                batch_data["enrolled_count"] += 1

        if summary["total_leads"]:
            summary["close_rate"] = round(summary["fully_paid"] / summary["total_leads"] * 100, 2)

        return summary, user_leads_map, batch_map, status_counter

    def _compute_user_stats(self, user_leads_map, call_logs):
        touched_statuses = {
            'follow_up','diabetes_interested_in_webinar','diabetes_not_interested_in_webinar',
             'walk_in', 'dnp','l1_basic_course_enrolled_fully_paid', 'l1_basic_course_enrolled_partially_paid', 'disqualified'
        }

        duration_map = defaultdict(float)
        total_calls = defaultdict(int)
        leaderboard = []
        touch_rate_data = []

        for log in call_logs:
            duration_map[log.user_id.id] += log.total_duration / 60.0
            total_calls[log.user_id.id] += log.total_calls

        user_model = self.env['res.users']
        for user_id, leads in user_leads_map.items():
            user = user_model.browse(user_id)
            touched = 0
            hot = 0
            warm = 0
            enrolled = 0

            for lead in leads:
                if (lead.call_status or '').lower() in touched_statuses:
                    touched += 1
                if any(tag.name.lower() == 'hot' for tag in lead.tag_ids):
                    hot += 1
                if any(tag.name.lower() == 'warm' for tag in lead.tag_ids):
                    warm += 1
                if lead.status in ['l1_basic_course_enrolled_fully_paid', 'l1_basic_course_enrolled_partially_paid']:
                    enrolled += 1

            untouched = len(leads) - touched
            leaderboard.append({
                "id": user.id,
                "name": user.name,
                "total_assigned": len(leads),
                "hot_leads": hot,
                "warm_leads": warm,
                "total_touched": touched,
                "untouched": untouched,
                "total_calls": total_calls.get(user_id, 0),
                "call_duration": round(duration_map.get(user_id, 0.0), 2),
                "total_enrolled": enrolled,
                "close_rate": round((enrolled / len(leads)) * 100, 2) if leads else 0,
            })

            touch_rate_data.append({
                "name": user.name,
                "touched": touched,
                "untouched": untouched,
            })

        return leaderboard, touch_rate_data

    def _compute_status_distribution(self, status_counter):
        status_field = self.env['crm.lead'].fields_get()['status']
        status_labels = dict(status_field.get('selection') or [])
        return [
            {"label": status_labels.get(status, status), "value": count}
            for status, count in status_counter.items()
        ]

    def _compute_call_trends(self, call_logs):
        calls_by_date = defaultdict(int)
        for log in call_logs:
            calls_by_date[log.date] += log.total_calls

        return [{"date": str(day), "count": calls_by_date[day]} for day in sorted(calls_by_date)]

    def _format_batch_stats(self, batch_map):
        table = []
        chart = []

        for batch, stats in batch_map.items():
            table.append({
                "batch": batch,
                "lead_count": stats["lead_count"],
                "enrolled_count": stats["enrolled_count"],
            })
            chart.append({
                "batch": batch,
                "fully_paid": stats["fully_paid"],
                "partial_paid": stats["partial_paid"],
            })

        return table, chart

    @api.model
    def get_users(self):
        """Fetch users from 'Offline Sales Team' or fallback to all users."""
        users = self._get_sales_users()
        return [{"id": u.id, "name": u.name} for u in users]