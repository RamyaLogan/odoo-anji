{
    "name": "CRM Custom Fields",
    "version": "17.0.1.0.0",
    "category": "CRM",
    "summary": "Custom fields for CRM module",
    "depends": ["base", "crm", "mail","queue_job","calendar"],
    "data": [
        "security/ir.model.access.csv",
        "security/leads_groups.xml",
        "views/crm_call_lead_view.xml",
        "views/lead_import_wizard_view.xml",
        "views/crm_phone_number_search_view.xml",
        "views/crm_lead_stage_view.xml",
        "views/crm_assign_lead_view.xml",
        "views/crm_assign_lead_wizard_view.xml",
        "views/res_users_view.xml",
        "views/user_role_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "crm_custom_fields/static/src/js/mail_message_patch.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}