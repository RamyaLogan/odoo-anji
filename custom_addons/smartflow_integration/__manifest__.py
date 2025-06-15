{
    'name': 'Smart Flow Integration',
    'version': '17.0.1.0.0',
    'category': 'Tools',
    'depends': ['base','crm','web'],
    'data': [
        "security/ir.model.access.csv",
        'views/res_users_view.xml',
        'views/smartflo_call_log_views.xml',
        'views/crm_lead_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'smartflow_integration/static/src/img/*.svg',
            'https://cdn.jsdelivr.net/npm/jssip/dist/jssip.min.js',
            'smartflow_integration/static/src/js/*.js',
            'smartflow_integration/static/src/xml/*.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}