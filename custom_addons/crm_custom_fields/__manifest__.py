{
    "name": "CRM Custom Fields",
    "version": "17.0.1.0.0",
    "category": "CRM",
    "summary": "Custom fields for CRM module",
    "depends": ["crm", "base", "queue_job"],
    "data": [
        "security/ir.model.access.csv",
        "views/crm_call_lead_view.xml",
        "views/lead_import_wizard_view.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}