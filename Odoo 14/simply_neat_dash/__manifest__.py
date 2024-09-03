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
        "views/templates.xml",
        "security/ir.model.access.csv"
    ],
    "qweb": ["static/src/xml/dashboard.xml", "static/src/xml/redirect.xml"],
    'images': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
