# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class SNCustomDataset(models.Model):
    _name = 'sn.custom.dataset'
    _description = 'Simply NEAT Custom Dataset'


