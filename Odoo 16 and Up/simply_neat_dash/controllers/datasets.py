import json

import logging
from odoo import sql_db
from odoo import http
from odoo.http import request
from contextlib import closing
from psycopg2 import sql
import re
from .helpers import update_dataset, get_column_calculation_code, calculate_column, create_dataset, has_model_field, has_dataset, is_query_valid, get_create_dataset_sql, has_field_in_query, get_odoo_access_rights, get_demo_row_sql, validate_query, validate_columns, get_first_row_sql, get_rows_sql, get_data_type_sql, get_model_fields, get_dataset_options, has_field, get_fields_from_query, get_sql
_logger = logging.getLogger(__name__)

class Datasets(http.Controller):
    def __init__(self):
        self.dataset_key_pattern = re.compile("^(?!_)\w+(?<!_)$")
    @http.route('/sn_datasets/has_field', type='json', auth='user', methods=['POST'])
    def has_field_endpoint(self, model, field, token):
        fields = has_field(model, field, token)
        return {'data': fields, 'status': 200}

    @http.route('/sn_datasets/get_fields_from_query', type='json', auth='user')
    def get_fields_from_query_endpoint(self, query):
        fields = get_fields_from_query(query, [])
        return {'data': fields, 'status': 200}

    @http.route('/sn_datasets/get_options', type='json', auth='user')
    def get_dataset_options_endpoint(self, token, nativeAllowedOnly = True):
        models = get_dataset_options(token, nativeAllowedOnly)
        return { 'data': models, 'status': 200 }

    @http.route('/sn_datasets/get_fields', type='json', auth='user')
    def get_dataset_fields(self, modelName, token, nativeAllowedOnly = True):
        fields = get_model_fields(modelName, token, nativeAllowedOnly)
        if fields is None:
            return { 'status': 500 }
        return { 'data': fields, 'status': 200 }

    @http.route('/sn_datasets/validate', type='json', auth='user')
    def validate_custom_dataset(self, query, calculationColumns, token):
        result = validate_query(token, query)
        if not result:
            return {'data': None, 'status': 403 }
        if not result['is_valid']:
            return { 'data': result, 'status': 200 }
        db = sql_db.db_connect(http.request.env.cr.dbname)
        with closing(db.cursor()) as sn_cr:
            try:
                row = get_first_row_sql(query, sn_cr, [])
                keys = list(row.keys())
                for col in calculationColumns:
                    keys.append(col['alias'])
                res = validate_columns(keys, token)
                if not res:
                    return { 'data': None, 'status': 403 }
                if not res['is_valid']:
                    return { 'data': res, 'status': 200 }
            except Exception as e:
                _logger.error("An exception occurred", exc_info=e)
                return { 'data': { 'error': { 'code': 'GENERAL_EXECUTION_FAIL' }, 'is_valid': False }, 'status': 200 }

        return { 'data': { 'error': None, 'is_valid': True }, 'status': 200 }

    @http.route('/sn_datasets/get_demo_data', type='json', auth='user')
    def get_demo_data(self, buildMethod, query, queryBuilder, token):
        try:
            sql_text = get_sql(token, buildMethod, query, queryBuilder)
            _logger.info("get_demo_data sql_text: %s", sql_text)
            if sql_text == 400:
                return { 'data': { 'data': [], 'columns': [] }, 'status': 200 }
            if sql_text is None:
                return { 'status': 403 }
            calculationColumns = []
            if buildMethod == 'queryBuilder':
                calculationColumns = queryBuilder['calculationColumns']
            validation_result = self.validate_custom_dataset(sql_text, calculationColumns, token)
            _logger.info("get_demo_data validation_result: %s", validation_result)
            if not validation_result['data']['is_valid']:
                return {'data': {'data': [], 'columns': []}, 'status': 200 }
            db = sql_db.db_connect(http.request.env.cr.dbname)
            with closing(db.cursor()) as sn_cr:
                data = get_demo_row_sql(sql_text, sn_cr)
                calculation_columns = []
                if buildMethod == 'queryBuilder':
                    calculation_columns = queryBuilder['calculationColumns']
                for item in data:
                    for col in calculation_columns:
                        calculation = get_column_calculation_code(col['column']['columnCalculationBuilder'], col['column']['highPrecisionMode'], item)
                        result = calculate_column(calculation, col['column']['highPrecisionMode'])
                        item[col['alias']] = result
                sql_text_columns = get_sql(token, buildMethod, query, queryBuilder, True)
                columns = get_fields_from_query(sql_text_columns, calculation_columns)
                return {'data': { 'data': data, 'columns': columns }, 'status': 200}
        except Exception as e:
            _logger.error("An exception occurred", exc_info=e)
            return { 'data': { 'data': [], 'columns': [] }, 'status': 200 }

    @http.route('/sn_datasets/get_group_options', type='json', auth='user')
    def get_group_options(self):
        groups = http.request.env['res.groups'].search([]).read(['id', 'full_name'])
        return { 'data': list(map(lambda x: { 'label': x['full_name'], 'value': x['id'] }, groups)), 'status': 200 }

    @http.route('/sn_datasets/get_user_options', type='json', auth='user', methods=['POST'])
    def get_user_options(self):
        users = http.request.env['res.users'].search([]).read(['id', 'name'])
        return {'data': list(map(lambda x: {'label': x['name'], 'value': x['id']}, users)), 'status': 200}

    @http.route('/sn_datasets/get_sql_table_options', type='json', auth='user', methods=['POST'])
    def get_sql_table_options(self):
        db = sql_db.db_connect(http.request.env.cr.dbname)
        with closing(db.cursor()) as sn_cr:
            rows = get_rows_sql("SELECT table_name AS label, table_name AS value FROM information_schema.tables WHERE table_schema='public'", sn_cr, [], "")
            return { 'data': rows, 'status': 200 }

    @http.route('/sn_datasets/get_sql_tables_column_options', type='json', auth='user', methods=['POST'])
    def get_sql_tables_column_options(self, tables):
        grouped_tables = {}
        for table in tables:
            if table['name'] not in grouped_tables:
                grouped_tables[table['name']] = []
            grouped_tables[table['name']].append(table)
        db = sql_db.db_connect(http.request.env.cr.dbname)
        with closing(db.cursor()) as sn_cr:
            sql_array = [sql.SQL("""
            SELECT 
                column_name AS value, 
                column_name AS label, 
                data_type,
                table_name
            FROM information_schema.columns
            WHERE table_name IN (""")]

            sql_array.append(sql.SQL(',').join(list(map(lambda x: sql.Literal(x), grouped_tables.keys()))))
            sql_array.append(sql.SQL(")"))
            comp = sql.Composed(sql_array)
            sql_result = comp.as_string(sn_cr._obj)
            rows = get_rows_sql(sql_result, sn_cr, [], "")
            fields = []
            for row in rows:
                data_type = row['data_type']
                if data_type == 'txid_snapshot' or data_type == 'pg_snapshot' or data_type == 'tsvector' or data_type == 'point' or data_type == 'polygon' or data_type == 'path' or data_type == 'box' or data_type == 'bytea' or data_type == 'circle' or data_type == 'line' or data_type == 'lseg':
                    continue
                group_array = grouped_tables[row['table_name']]
                for table in group_array:
                    if 'alias' in table:
                        alias = table['alias']
                    else:
                        alias = None
                    new_field = {
                        'label': row['label'],
                        'value': row['value'],
                        'data_type': get_data_type_sql(data_type),
                        'table_name': alias
                    }
                    fields.append(new_field)

            return { 'data': fields, 'status': 200 }

    @http.route('/sn_datasets/get_odoo_access_rights', type='json', auth='user', methods=['POST'])
    def get_odoo_access_rights(self):
        return get_odoo_access_rights()

    @http.route('/sn_datasets/create', type='json', auth='user', methods=['POST'])
    def create_data_set(self, dataset, token):
        query_response = get_create_dataset_sql(dataset, token)
        if not query_response:
            return { 'status': 500 }
        if query_response['status'] != 200:
            return query_response

        query = query_response['data']
        calculation_columns = []
        if dataset['buildMethod'] == 'queryBuilder':
            calculation_columns = dataset['queryBuilder']['calculationColumns']
        columns_sql = get_sql(token, dataset['buildMethod'], dataset['query'], dataset['queryBuilder'], True)
        validation_result = is_query_valid(query, columns_sql, calculation_columns)
        is_valid = validation_result['is_valid']
        if not is_valid:
            _logger.info('create validation 6')
            return {'status': 400}
        columns_validation_result = validate_columns(validation_result['columns'], token)
        if not columns_validation_result['is_valid']:
            _logger.info('create validation 7')
            return {'status': 400}
        has_redirect_field = has_field_in_query(columns_sql, dataset['redirectField'])
        if not has_redirect_field:
            _logger.info('create validation 8')
            return {'status': 400}
        has_dataset_res = has_dataset(dataset['redirectMapModel'], token)
        if not has_dataset_res:
            _logger.info('create validation 9')
            return {'status': 400}
        has_redirect_map_field = has_field(dataset['redirectMapModel'], dataset['redirectMapField'], token)
        has_model_field_res = has_model_field(dataset['redirectMapModel'], dataset['redirectMapField'])
        if not has_redirect_map_field and not has_model_field_res:
            _logger.info('create validation 10')
            return {'status': 400}

        dataset_key_exists = has_dataset(dataset['dataSetKey'], token)
        if dataset_key_exists:
            return {'status': 400}
        return create_dataset(dataset, token)


    @http.route('/sn_datasets/update', type='json', auth="user", methods=['POST'])
    def update_data_set(self, dataset, token):
        query_response = get_create_dataset_sql(dataset, token)
        if not query_response:
            return {'status': 500}
        if query_response['status'] != 200:
            return query_response

        query = query_response['data']
        calculation_columns = []
        if dataset['buildMethod'] == 'queryBuilder':
            calculation_columns = dataset['queryBuilder']['calculationColumns']
        columns_sql = get_sql(token, dataset['buildMethod'], dataset['query'], dataset['queryBuilder'], True)
        validation_result = is_query_valid(query, columns_sql, calculation_columns)
        is_valid = validation_result['is_valid']
        if not is_valid:
            _logger.info('update validation 1')
            return {'status': 400}
        columns_validation_result = validate_columns(validation_result['columns'], token)
        if not columns_validation_result['is_valid']:
            _logger.info('update validation 2')
            return {'status': 400}
        has_redirect_field = has_field_in_query(columns_sql, dataset['redirectField'])
        if not has_redirect_field:
            _logger.info('update validation 3')
            return {'status': 400}
        has_redirect_map_model = has_dataset(dataset['redirectMapModel'], token)
        if not has_redirect_map_model:
            _logger.info('update validation 4')
            return {'status': 400 }
        has_redirect_map_field = has_field(dataset['redirectMapModel'], dataset['redirectMapField'], token)
        has_model_field_res = has_model_field(dataset['redirectMapModel'],  dataset['redirectMapField'])
        if not has_redirect_map_field and not has_model_field_res:
            _logger.info('update validation 5')
            return {'status': 400 }
        return update_dataset(dataset, token)

    @http.route('/sn_datasets/validate_key', type='json', auth="user", methods=['POST'])
    def validate_key(self, key, token):
        has_dataset_res = has_dataset(key, token)
        return { 'data': { 'is_valid': not has_dataset_res }, 'status': 200 }

    @http.route('/sn_datasets/get_foreign_keys', type='json', auth="user", methods=['POST'])
    def get_foreign_keys(self, model):
        db = sql_db.db_connect(http.request.env.cr.dbname)
        with closing(db.cursor()) as sn_cr:
            sql_array = [sql.SQL("""
            SELECT
kcu.table_name, kcu.column_name, 
ccu.table_name AS foreign_table_name,
ccu.column_name AS foreign_column_name 
FROM 
information_schema.key_column_usage AS kcu
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = kcu.constraint_name
WHERE (kcu.position_in_unique_constraint = 1 AND kcu.table_name=""")]
            sql_array.append(sql.Literal(model))
            sql_array.append(sql.SQL(") OR (ccu.table_name="))
            sql_array.append(sql.Literal(model))
            sql_array.append(sql.SQL(" AND ccu.column_name = 'id')"))
            comp = sql.Composed(sql_array)
            sql_result = comp.as_string(sn_cr._obj)
            try:
                rows = get_rows_sql(sql_result, sn_cr, [], "")
                lines = list(map(lambda x:
                {
                    'label_left': x['table_name'] + "." + x['column_name'],
                    'label_right': x['foreign_table_name'] + "." + x["foreign_column_name"],
                    'value': x['table_name'] + "." + x['column_name'] + "__" + x['foreign_table_name'] + "." + x["foreign_column_name"]
                }, rows))
            except Exception as e:
                _logger.error("An exception occurred", exc_info=e)
                return {'data': [], 'status': 200}
        return { 'data': lines, 'status': 200 }







