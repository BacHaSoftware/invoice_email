# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Email For Invoice',
    'author': 'Bac Ha Software',
    'website': 'https://bachasoftware.com',
    'maintainer': 'Bac Ha Software',
    'version': '1.0',
    'category': 'Invoice',
    'sequence': 75,
    'summary': 'Custom email flow for invoicing',
    'description': "Option to send one invoice email for all partners instead of one email per partner.",
    'depends': ['account'],
    'assets': {
        'web.assets_backend': []
    },
    'data': ['data/invoice_email_template_data.xml','wizard/account_invoice_send_views.xml'],
    'demo': [],
    "external_dependencies": {},
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3'
}
