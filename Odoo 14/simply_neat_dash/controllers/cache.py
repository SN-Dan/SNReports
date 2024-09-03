import json

import logging
from odoo import http
from datetime import datetime
_logger = logging.getLogger(__name__)

class Cache(http.Controller):
    @http.route('/sn_cache/set_cache', type='json', auth='user', methods=['POST'])
    def set_cache(self, key, value, expire_timestamp):
        expire_time_divide = expire_timestamp / 1000.0
        expire_time = datetime.fromtimestamp(expire_time_divide)

        existing_cache = http.request.env['sn.cache'].search([('user_id', '=', http.request.uid), ('key', '=', key)])
        if existing_cache:
            existing_cache.write({'value': json.dumps(value), 'expire_time': expire_time})
        else:
            http.request.env['sn.cache'].create({'key': key, 'value': json.dumps(value), 'user_id': http.request.uid, 'expire_time': expire_time})
        return { 'status': 200, 'data': None }
    @http.route('/sn_cache/get_cache', type='json', auth='user', methods=['POST'])
    def get_bulk_cache(self, keys):
        http.request.env['sn.cache'].search([('user_id', '=', http.request.uid), ('expire_time', '<', datetime.utcnow())]).unlink()
        cache = http.request.env['sn.cache'].search([('user_id', '=', http.request.uid), ('key', 'in', keys)]).read(['key', 'value'])
        caches = {}
        for c in cache:
            caches[c['key']] = json.loads(c['value'])
        return {'status': 200, 'data': caches}

    @http.route('/sn_cache/expire_cache', type='json', auth='user', methods=['POST'])
    def expire_cache(self, keys):
        http.request.env['sn.cache'].search([('user_id', '=', http.request.uid), ('key', 'in', keys)]).unlink()
        return {'status': 200, 'data': None}
