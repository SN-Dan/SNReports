# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class SNDashboardGroupAccess(models.Model):
    _name = 'sn.dashboard.group.access'
    _description = 'Simply NEAT Dashboard Group Access'


