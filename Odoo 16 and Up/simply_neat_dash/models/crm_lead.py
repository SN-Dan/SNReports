# -*- coding: utf-8 -*-

from odoo import fields, models, api

from . import crm_lead_velocity

class Lead(models.Model):
    _inherit = 'crm.lead'

    lead_velocity_ids = fields.One2many('crm.lead.velocity', 'lead_id', compute='_compute_add_velocity', string='Lead Velocity', index=True, store=True)

    @api.depends('stage_id')
    def _compute_add_velocity(self):
        for lead in self:
            self.env['crm.lead.velocity'].create({
                'lead_id': lead.id,
                'stage_id': lead.stage_id.id
            })
