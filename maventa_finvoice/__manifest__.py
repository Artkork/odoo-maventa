{
    "name": "Maventa Finvoice",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "license": "LGPL-3",
    "author": "Your Company",
    "website": "https://www.yourcompany.com",
    "summary": "Finvoice invoice sending through Maventa operator",
    "description": """
    This module enables sending electronic invoices in Finvoice format
    through Maventa operator's API. It integrates with Odoo's accounting
    system to automatically generate and transmit Finvoice invoices.
    
    Features:
    - Maventa API integration
    - Finvoice format generation
    - Automatic invoice transmission
    - Batch sending capabilities
    - Invoice status tracking
    - Error handling and logging
    """,
    "depends": [
        "account",
        "sale",
        "base",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/maventa_config_views.xml",
        "views/account_move_views.xml",
        "views/finvoice_log_views.xml",
        "views/menu_views.xml",
        "wizards/send_finvoice_wizard_views.xml",
    ],
    "external_dependencies": {
        "python": [
            "requests",
            "lxml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
