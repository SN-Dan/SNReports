# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class SNGeneralSettings(models.Model):
    _name = 'sn.general.settings'
    _description = 'Simply NEAT General Settings'


