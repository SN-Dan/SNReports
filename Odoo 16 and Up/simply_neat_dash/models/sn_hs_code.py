# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class HSCode(models.Model):
    _name = 'sn.hs.code'
    _description = 'Simply HS Code'
    code = fields.Text('Code', required=True, readonly=False, store=True)


