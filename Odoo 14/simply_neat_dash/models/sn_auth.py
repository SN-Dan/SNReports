# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class SNAuth(models.Model):
    _name = 'sn.auth'
    _description = 'Simply NEAT Auth'
    serial_number = fields.Text('Serial Number', required=True, readonly=False, store=True)
    scope = fields.Text('Scope', required=True, readonly=False, store=True)


