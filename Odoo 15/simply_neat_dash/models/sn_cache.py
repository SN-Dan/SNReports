from odoo import models, fields, api
import datetime

class SNCache(models.Model):
    _name = 'sn.cache'
    _description = 'SN Cache'

    key = fields.Char(required=True, index=True)
    value = fields.Text(required=True)
    expire_time = fields.Datetime(required=True)
    user_id = fields.Integer('UserId', required=True, readonly=False, store=True)

