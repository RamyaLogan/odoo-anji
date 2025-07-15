{
    "name": "Online Team Dashboard (OWL)",
    "version": "1.0",
    "category": "Sales",
    "summary": "Interactive dashboard with custom KPIs for online sales team",
    "depends": ["base", "web", "crm", "smartflow_integration"],
    "data": [
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "online_team_dashboard/static/src/js/*.js",
             "online_team_dashboard/static/src/xml/*.xml",
             "online_team_dashboard/static/src/data/*.json",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3"
}