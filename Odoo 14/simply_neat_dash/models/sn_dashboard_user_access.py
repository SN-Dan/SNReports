# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class SNDashboardUserAccess(models.Model):
    _name = 'sn.dashboard.user.access'
    _description = 'Simply NEAT Dashboard User Access'


