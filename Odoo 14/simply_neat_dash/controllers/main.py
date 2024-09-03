import json

from psycopg2 import sql
import logging
from odoo import http
from odoo import sql_db
from contextlib import closing
import requests

_logger = logging.getLogger(__name__)
from .helpers import forbidden_models, get_column_calculation_code, calculate_column, sn_url, is_custom_dataset, get_rows_sql, get_model_fields, get_flat_item, get_default_converted_filters, get_filtered_ids, get_default_converted_filters_sql, get_converted_record_rules_sql, get_filter_query_sql

class Main(http.Controller):
    @http.route('/reports/get_data', type='json', auth='user', methods=['POST'])
    def get_data(self, defaultFilters, filters, modelName, fields, token):
        current_fields = []
        all_fields = fields
        if all_fields is None or len(all_fields) == 0:
            all_fields = get_model_fields(modelName, token)
            if all_fields is None:
                return { 'status': 500 }
            all_fields = list(filter(lambda x: x['is_odoo_partial_column'] is False, all_fields))
        current_fields = list(map(lambda x: x['value'], all_fields))
        _logger.info('SimplyNeatDashTest: current_fields %s', current_fields)
        if 'onchange_studio_item_built' in current_fields:
            current_fields.remove("onchange_studio_item_built")
        if is_custom_dataset(modelName, token):
            response = requests.get(sn_url + "/Datasets/get_custom_dataset_sql_for_data?dataset=" + modelName, headers={
                'Authorization': token
            })
            if not response.ok:
                if response.status_code != 500:
                    return { 'status': response.status_code }
                _logger.info('get_custom_dataset_sql_for_data Response Failed:  %s', response)
                return { 'status': 500 }
            res = response.json()
            query = res['query']
            matched_record_rules = res['matched_record_rules']
            calculation_columns = res['calculation_columns']
            db = sql_db.db_connect(http.request.env.cr.dbname)
            with closing(db.cursor()) as cr:
                default_converted_filters = get_default_converted_filters_sql(defaultFilters, cr)
                converted_record_rules = get_converted_record_rules_sql(matched_record_rules, cr)
                where_query = get_filter_query_sql(filters, default_converted_filters, converted_record_rules, cr)
                try:
                    rows = get_rows_sql(query, cr, [], where_query)
                    for item in rows:
                        for col in calculation_columns:
                            calculation = get_column_calculation_code(col['column']['columnCalculationBuilder'], col['column']['highPrecisionMode'], item)
                            result = calculate_column(calculation, col['column']['highPrecisionMode'])
                            item[col['alias']] = result
                    return {'data': rows, 'status': 200}
                except Exception as e:
                    _logger.error("An exception occurred", exc_info=e)
                    _logger.info('Query Execution Failed:  %s', query)
                    return {'status': 500}
        else:
            if len(current_fields) == 0:
                return { 'data': [], 'status': 200 }
            if len(defaultFilters) > 0 or len(filters) > 0:
                default_converted_filters = get_default_converted_filters(defaultFilters)
                filter_ids = list(set(get_filtered_ids(filters, default_converted_filters, modelName)))
                data = http.request.env[modelName].search([('id', 'in', filter_ids)]).read(current_fields)
            else:
                if modelName in forbidden_models:
                    return { 'status': 401 }
                data = http.request.env[modelName].search([]).read(current_fields)

        return { 'data': list(map(lambda x: get_flat_item(x), data)), 'status': 200 }
