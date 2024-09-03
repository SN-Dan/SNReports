# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class SNUserSettings(models.Model):
    _name = 'sn.user.settings'
    _description = 'Simply NEAT User Settings'


