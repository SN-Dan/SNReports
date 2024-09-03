# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from . import crm_lead

_logger = logging.getLogger(__name__)

class CRMLeadVelocity(models.Model):
    _name = 'crm.lead.velocity'
    _description = 'CRM Lead Velocity'

    end_date = fields.Datetime(
        'End Date', compute='_compute_end_date', readonly=True, store=True)
    lead_id = fields.Many2one('crm.lead', string='Lead', index=True, store=True)
    stage_id = fields.Many2one(
        'crm.stage', string='Stage', index=True, tracking=True, readonly=False, store=True,
        copy=False, ondelete='restrict')

    @api.depends('create_date')
    def _compute_end_date(self):
        for lead_velocity in self:
            velocities = lead_velocity.lead_id.lead_velocity_ids
            if len(velocities) > 1:
                for vel in velocities:
                    if not vel.end_date and vel.id != lead_velocity.id:
                        vel.end_date = fields.Datetime.now()


