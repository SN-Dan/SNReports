# -*- coding: utf-8 -*-
{
    'name': "Simply NEAT Reports",
    'author': 'Simply NEAT',
    'category': 'Productivity',
    'summary': """ The best charts for Odoo """,
    'website': 'http://www.simply-neat.com',
    'license': 'OPL-1',
    'description': """ Simply put the best reports dashboard in Odoo! """,
    'version': '1.0',
    'depends': ['sale', 'base', 'crm'],
    'external_dependencies': {
        'python': ['cryptography', 'hashlib']
    },
    'data': [
        "views/dashboard.xml",
        "security/ir.model.access.csv"
    ],
    'assets': {
       'web.assets_qweb': [
             'simply_neat_dash/static/src/**/*.xml',
        ],
        'web.assets_backend': [
            'simply_neat_dash/static/src/**/*.js',
            'https://dw0v6gfluwf8p.cloudfront.net/v1/odooCharts.env.js'
        ],
    },
    'images': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
