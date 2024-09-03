# -*- coding: utf-8 -*-

from odoo import fields, models, api

from . import crm_lead_velocity

class Stage(models.Model):
    _inherit = 'crm.stage'

    lead_velocity_ids = fields.One2many('crm.lead.velocity', 'stage_id', string='Lead Mining Request', index=True, store=True)
