from odoo import models, api, fields
from collections import defaultdict, Counter
from datetime import timedelta, datetime


class OnlineTeamDashboard(models.AbstractModel):
    _name = "online.team.dashboard"
    _description = "Online Team Dashboard"

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

        # -----------------------
        # Build domain filters
        # -----------------------
        domain = [
            ('type', '=', 'lead'),
            ('create_date', '>=', from_dt),
            ('create_date', '<=', to_dt),
        ]
        if selected_user_ids:
            domain.append(('user_id', 'in', selected_user_ids))

        # -----------------------
        # Fetch filtered leads
        # -----------------------
        leads = self.env['crm.lead'].search(domain)

        # -----------------------
        # Remaining logic
        # -----------------------
        call_logs = self._get_call_logs(from_date, to_date)
        users = self._get_sales_users()

        summary, user_leads_map, status_counter = self._aggregate_leads(leads)
        summary["unassigned_leads"] = summary["total_leads"] - summary["total_assigned"]

        leaderboard, touch_rate_data = self._compute_user_stats(user_leads_map, call_logs)
        status_pie_data = self._compute_status_distribution(status_counter)
        call_counts_by_date, overall_total_calls, overall_total_duration = self._compute_call_trends(call_logs)

        call_status_field = self.env['crm.lead']._fields['call_status']
        status_list = [{"key": key, "label": label} for key, label in call_status_field.selection]

        return {
            "from_date": from_date,
            "to_date": to_date,
            **summary,
            "table": leaderboard,
            "touch_rate_data": touch_rate_data,
            "call_counts_by_date": call_counts_by_date,
            "status_pie_data": status_pie_data,
            "overall_total_calls": overall_total_calls,
            "overall_call_duration": round(overall_total_duration, 2),
            "users": [{"id": u.id, "name": u.name} for u in users],
            "status": status_list,
        }

    def _get_call_logs(self, from_date, to_date):
        return self.env['call.log.summary'].search([
            ('date', '>=', from_date),
            ('date', '<=', to_date),
        ])

    def _get_sales_users(self):
        teams = self.env['crm.team'].search([('name', 'in', ['Online Sales Team - Web', 'Online Sales Team - FB'])])
        return teams.mapped('member_ids') if teams else self.env['res.users']

    def _aggregate_leads(self, leads):
        summary = {
            "total_leads": len(leads),
            "total_assigned": len(leads.filtered(lambda l: l.user_id)),
            "total_touched": len(leads.filtered(lambda l: (l.call_status or '').lower() in ['done', 'dnp', 'disqualified', 'follow_up'])),
            "total_done": len(leads.filtered(lambda l: (l.call_status or '').lower() == 'done')),
            "close_rate": 0.0,
        }

        if summary["total_leads"]:
            summary["close_rate"] = round((summary["total_done"] / summary["total_leads"]) * 100, 2)

        user_leads_map = defaultdict(list)
        status_counter = Counter()

        for lead in leads:
            if lead.user_id:
                user_leads_map[lead.user_id.id].append(lead)
            status = (lead.call_status or 'new').lower()
            status_counter[status] += 1

        return summary, user_leads_map, status_counter

    def _compute_user_stats(self, user_leads_map, call_logs):
        duration_map = defaultdict(float)
        total_calls = defaultdict(int)

        for log in call_logs:
            duration_map[log.user_id.id] += log.total_duration / 60.0
            total_calls[log.user_id.id] += log.total_calls

        user_model = self.env['res.users']
        leaderboard = []
        touch_rate_data = []

        for user_id, leads in user_leads_map.items():
            user = user_model.browse(user_id)
            touched = len([l for l in leads if (l.call_status or '').lower() in ['done', 'dnp', 'disqualified', 'follow_up']])
            done = len([l for l in leads if (l.call_status or '').lower() == 'done'])
            new = len([l for l in leads if (l.call_status or '').lower() == 'new'])
            untouched = len(leads) - touched

            leaderboard.append({
                "id": user.id,
                "name": user.name,
                "total_assigned": len(leads),
                "total_touched": touched,
                "pending": new,
                "done": done,
                "interested": 0,  # You can compute this if applicable
                "connected": round((touched / len(leads)) * 100, 2) if leads else 0,
                "call_duration": round(duration_map.get(user.id, 0.0), 2),
                "total_calls": total_calls.get(user.id, 0),
            })

            touch_rate_data.append({
                "name": user.name,
                "touched": touched,
                "untouched": untouched,
            })

        return leaderboard, touch_rate_data

    def _compute_status_distribution(self, status_counter):
        return [{"label": k.title(), "value": v} for k, v in status_counter.items()]

    def _compute_call_trends(self, call_logs):
        calls_per_day = defaultdict(int)
        total_duration = 0.0
        total_calls = 0

        for log in call_logs:
            calls_per_day[log.date] += log.total_calls
            total_duration += log.total_duration / 60.0
            total_calls += log.total_calls

        trend = [{"date": str(day), "count": calls_per_day[day]} for day in sorted(calls_per_day)]
        return trend, total_calls, total_duration
    
    @api.model
    def get_users(self):
        """Fetch users from 'Online Sales Team' or fallback to all users."""
        users = self._get_sales_users()
        return [{"id": u.id, "name": u.name} for u in users]