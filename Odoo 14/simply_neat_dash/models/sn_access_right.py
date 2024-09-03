# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class SNAccessRight(models.Model):
    _name = 'sn.access.right'
    _description = 'Simply NEAT Access Right'


