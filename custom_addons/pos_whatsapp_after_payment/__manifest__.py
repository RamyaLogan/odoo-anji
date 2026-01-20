{
    "name": "POS WhatsApp After Payment",
    "version": "1.0.0",
    "category": "Point of Sale",
    "depends": [
        "point_of_sale",
        # keep this dependency name EXACTLY as your installed module's technical name
        # (check Apps > installed module name, or Settings > Technical > Modules)
        "mail_gateway_whatsapp",
        # if you want invoice PDF attach:
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/pos_config_views.xml",
        "views/pos_payment_method_views.xml",
    ],
    "assets": {
    "point_of_sale._assets_pos": [
        "pos_whatsapp_after_payment/static/src/js/payment_method_fields.js",
        "pos_whatsapp_after_payment/static/**/*.js",
        "pos_whatsapp_after_payment/static/src/**/*.js",
        "pos_whatsapp_after_payment/static/src/**/*.xml",
        "pos_whatsapp_after_payment/static/src/app/screens/receipt_screen/receipt_screen_whatsapp.xml",
        "pos_whatsapp_after_payment/static/src/app/screens/receipt_screen/receipt_screen_whatsapp.js",
    ],
},
    'sequence': 1,
    "installable": True,
    "application": False,
}