import json
import uuid
import logging
import time
from odoo import http
from .helpers import get_odoo_access_rights, sn_url
import requests
from cryptography.fernet import Fernet
_logger = logging.getLogger(__name__)

def get_secret_key():
    sc_rows = http.request.env['sn.reports.security'].sudo().search([]).read(['sn_secret_key'])
    if len(sc_rows) == 0:
        pr = http.request.env['sn.reports.security'].sudo().create({'sn_secret_key': 'str'})
        secret_key = pr.sn_secret_key
    else:
        secret_key = sc_rows[0]['sn_secret_key']
    return secret_key
def decrypt(token):
    fernet_key = get_secret_key()
    fernet = Fernet(fernet_key)
    return fernet.decrypt(token.encode()).decode()

def encrypt(message):
    fernet_key = get_secret_key()
    fernet = Fernet(fernet_key)
    return fernet.encrypt(message.encode()).decode()

class Main(http.Controller):
    @http.route('/sn_auth/get_token', type='json', auth='user', methods=['POST'])
    def get_token(self):
        result = http.request.env['sn.auth'].search([]).read(['serial_number', 'scope'])
        if len(result) == 0:
            return { 'status': 200, 'data': None }
        access = get_odoo_access_rights()['data']
        try:
            first_result = result[0]
            serial_number = decrypt(first_result['serial_number'])
            scope = 'main'
            if 'scope' in first_result and first_result['scope']:
                scope = first_result['scope']
        except Exception as e:
            _logger.error("An exception occurred", exc_info=e)
            http.request.env['sn.auth'].search([]).unlink()
            return {'status': 200, 'data': None}
        current_user = http.request.env.user
        ue = current_user.email
        response = requests.post(sn_url + "/Licenses/token", json={
            'serial_number': serial_number,
            'scope': scope,
            'uid': http.request.uid,
            'ue': ue,
            'cid': http.request.env.company.id,
            'access': access,
            'has_admin_group': http.request.env.user.has_group('base.group_erp_manager'),
            'user_group_ids': http.request.env.user.groups_id.ids,
            'referer': http.request.httprequest.headers['Referer']
        }, headers={'content-type': 'application/json'})

        if not response.ok:
            if response.status_code == 402:
                return {'status': 402}
            return { 'status': 500 }
        res = response.json()
        return { 'data': res, 'status': 200 }

    @http.route('/sn_auth/set_serial_number', type='json', auth='user', methods=['POST'])
    def set_serial_number(self, serial_number, scope):
        res = http.request.env['sn.auth'].search([]).read(['id'])
        sn_token = encrypt(serial_number)
        if len(res) == 0:
            http.request.env['sn.auth'].create({ 'serial_number': sn_token, 'scope': scope })
        else:
            auth = http.request.env['sn.auth'].search([], limit=1)
            auth.write({
                'serial_number': sn_token,
                'scope': scope
            })

        return { 'status': 200 }

    @http.route('/sn_auth/set_app_config', type='json', auth='user', methods=['POST'])
    def set_app_config(self, scope):
        res = http.request.env['sn.auth'].search([]).read(['id'])
        if len(res) == 0:
            return { 'status': 404 }
        else:
            auth = http.request.env['sn.auth'].search([], limit=1)
            auth.write({
                'scope': scope
            })

        return { 'status': 200 }

    @http.route('/sn_auth/get_app_config', type='json', auth='user', methods=['POST'])
    def get_app_config(self):
        res = http.request.env['sn.auth'].search([]).read(['scope'])
        if len(res) == 0:
            return { 'status': 404 }

        return { 'status': 200, 'data': { 'scope': res[0]['scope'] } }

    @http.route('/sn_auth/handshake', type='http', auth='public', methods=['POST'], csrf=False,
                cors='*')
    def handshake(self):
        r = json.loads(http.request.httprequest.data)
        code = r.get('code')
        res = http.request.env['sn.hs.code'].sudo().search([]).read(['code'])
        if len(res) == 0:
            return '404'
        for item in res:
            if item['code'] == code:
                http.request.env['sn.hs.code'].sudo().search([]).unlink()
                return '200'

        http.request.env['sn.hs.code'].sudo().search([]).unlink()
        return '401'

    @http.route('/sn_auth/register', type='json', auth='user', methods=['POST'])
    def register(self, scope, email, name, password, temp_id, company_size, receive_marketing, terms_accepted, phone=None, vat=None, company=None):
        referer = http.request.httprequest.headers['Referer']
        code = str(uuid.uuid4())
        http.request.env['sn.hs.code'].sudo().create({'code': code})
        http.request.env.cr.commit()
        current_user = http.request.env.user
        ue = current_user.email
        values = {
            'email': email,
            'userEmail': ue,
            'name': name,
            'phone': phone,
            'vat': vat,
            'tempId': temp_id,
            'password': password,
            'company': company,
            'referer': referer,
            'hsCode': code,
            'companySize': company_size,
            'receiveMarketing': receive_marketing,
            'termsAccepted': terms_accepted
        }
        response = requests.post(
            sn_url + "/Licenses/register",
            json=values,
            headers={'content-type': 'application/json'})
        if not response.ok:
            return {'data': None, 'status': 400}
        data = response.json()
        res = http.request.env['sn.auth'].search([]).read(['id'])
        sn_token = encrypt(data['token'])
        if len(res) == 0:
            http.request.env['sn.auth'].create({'serial_number': sn_token, 'scope': scope})
        else:
            auth = http.request.env['sn.auth'].search([], limit=1)
            auth.write({
                'serial_number': sn_token,
                'scope': scope
            })
        return {'data': { 'freeTrial': data['freeTrial'] }, 'status': 200}

    @http.route('/sn_auth/login', type='json', auth='user', methods=['POST'])
    def login(self, email, password, scope):
        referer = http.request.httprequest.headers['Referer']
        values = {
            'email': email,
            'password': password,
            'referer': referer,
        }
        response = requests.post(
            sn_url + "/Licenses/login",
            json=values,
            headers={'content-type': 'application/json'})
        if not response.ok:
            return {'data': None, 'status': 400}
        data = response.json()
        res = http.request.env['sn.auth'].search([]).read(['id'])
        sn_token = encrypt(data['token'])
        if len(res) == 0:
            http.request.env['sn.auth'].create({ 'serial_number': sn_token, 'scope': scope })
        else:
            auth = http.request.env['sn.auth'].search([], limit=1)
            auth.write({
                'serial_number': sn_token,
                'scope': scope
            })

        return { 'status': 200 }

    @http.route('/sn_auth/logout', type='json', auth='user', methods=['POST'])
    def logout(self):
        http.request.env['sn.auth'].search([], limit=1).unlink()
        return {'status': 200 }