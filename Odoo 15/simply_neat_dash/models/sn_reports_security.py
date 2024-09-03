import logging
from odoo import fields, models, api, _
from cryptography.fernet import Fernet

_logger = logging.getLogger(__name__)

class SNReportsSecurity(models.Model):
    _name = 'sn.reports.security'
    _description = 'Simply NEAT Reports Security'
    sn_secret_key = fields.Char('Secret Key')

    def create(self, values):
        fernet_key = Fernet.generate_key()
        fernet_key_string = fernet_key.decode()
        values['sn_secret_key'] = fernet_key_string
        return super(SNReportsSecurity, self).create(values)


    def write(self, values):
        if 'sn_secret_key' in values:
            del values['sn_secret_key']
        return super(SNReportsSecurity, self).write(values)