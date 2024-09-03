import json

import logging
from odoo import sql_db
from odoo import http
import math
from odoo.http import request
from contextlib import closing
from psycopg2 import sql
import requests
from odoo.modules.module import get_module_resource
from decimal import Decimal
from datetime import datetime, timedelta, date, time
import re
_logger = logging.getLogger(__name__)
sn_url = 'https://xgxl6uegelrr4377rvggcakjvi0djbts.lambda-url.eu-central-1.on.aws/api'
forbidden_models = ['sn.auth', 'sn.reports.security']

def get_config():
    path = get_module_resource('simply_neat_dash', 'config/', 'config.json')
    file = open(path, 'r')
    conf = json.loads("".join(file.readlines()))
    return conf
def is_custom_dataset(modelName, token):
    response = requests.get(sn_url + "/Datasets/is_custom_dataset?dataset=" + modelName, headers={
        'Authorization': token
    })
    if not response.ok:
        return False
    res = response.json()
    is_custom = res['isCustomDataset']
    return is_custom

def get_create_dataset_sql(dataset, token):
    response = requests.post(
        sn_url + "/Datasets/get_create_sql",
        json=dataset,
        headers={'content-type': 'application/json', 'Authorization': token})

    if not response.ok:
        if response.status_code == 500:
            return None
        return {'status': response.status_code}
    res = response.json()
    return { 'status': 200, 'data': res['query'] }

def create_dataset(dataset, token):
    response = requests.post(
        sn_url + "/Datasets/create",
        json=dataset,
        headers={'content-type': 'application/json', 'Authorization': token})

    if not response.ok:
        return {'status': response.status_code}
    return { 'status': 200, 'data': dataset['dataSetKey'] }

def update_dataset(dataset, token):
    response = requests.post(
        sn_url + "/Datasets/update",
        json=dataset,
        headers={'content-type': 'application/json', 'Authorization': token})

    if not response.ok:
        return {'status': response.status_code}
    return { 'status': 200, 'data': dataset['dataSetKey'] }

def is_query_valid(query, columns_query, calculation_columns):
    db = sql_db.db_connect(http.request.env.cr.dbname)
    with closing(db.cursor()) as sn_cr:
        try:
            _logger.info("is_query_valid query: %s", query)
            row = get_first_row_sql(query, sn_cr, [])
            row = get_first_row_sql(columns_query, sn_cr, [])
            keys = list(row.keys())
            for col in calculation_columns:
                keys.append(col['alias'])
            return { 'is_valid': True, 'columns': keys }
        except Exception as e:
            _logger.error("An exception occurred", exc_info=e)
            return { 'is_valid': False, 'columns': [] }


def get_first_row_sql(query, sn_cr, columns):
    if len(columns) > 0:
        custom_query = """
        SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;
        BEGIN TRANSACTION;
            SET statement_timeout=10000;
            SELECT """ + ', '.join(columns) + """ FROM (%s) AS FirstRow LIMIT 1;
        """ % query
    else:
        custom_query = """
        SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;
        BEGIN TRANSACTION;
            SET statement_timeout=10000;
            SELECT * FROM (%s) AS FirstRow LIMIT 1;
        """ % query
    sn_cr.execute(custom_query)
    row = sn_cr.dictfetchone()
    sn_cr.execute("ROLLBACK;")

    return row
def is_date(var):
    return isinstance(var, datetime)

# Calculate the difference between two dates
def date_difference(p_start_date, p_end_date, period):
    period_diff = None
    if type(p_start_date) == date:
        start_date = datetime.combine(p_start_date, datetime.min.time())
    elif type(p_start_date) == time:
        today_date = datetime.today().date()
        start_date = datetime.combine(today_date, p_start_date)
    else:
        start_date = p_start_date

    if type(p_end_date) == date:
        end_date = datetime.combine(p_end_date, datetime.min.time())
    elif type(p_end_date) == time:
        today_date = datetime.today().date()
        end_date = datetime.combine(today_date, p_end_date)
    else:
        end_date = p_end_date
    if start_date is not None and end_date is not None:

        difference = end_date - start_date
        if period == 'seconds':
            period_diff = abs(difference.total_seconds())
        elif period == 'minutes':
            period_diff = abs(difference.total_seconds()) / 60
        elif period == 'hours':
            period_diff = (abs(difference.total_seconds()) / 60) / 60
        elif period == 'days':
            period_diff = (abs(difference.total_seconds()) / 60) / 60 / 24
        elif period == 'weeks':
            period_diff = (abs(difference.total_seconds()) / 60) / 60 / 24 / 7
        elif period == 'months':
            period_diff = abs(start_date.month - end_date.month) + (abs(start_date.year - end_date.year) * 12)
        elif period == 'quarters':
            period_diff = math.floor((abs(start_date.month - end_date.month) + (abs(start_date.year - end_date.year) * 12)) / 3)
        elif period == 'years':
            period_diff = abs(start_date.year - end_date.year)


    return period_diff

def get_column_calculation_code(columnCalculationBuilder, highPrecisionMode, item):
    code = ''
    if columnCalculationBuilder['mainColumn']['type'] is None:
        return None
    if columnCalculationBuilder['mainColumn']['type'] == 'column':
        if highPrecisionMode == 'yes':
            code += "Decimal(str("

        if columnCalculationBuilder['mainColumn']['column'] == '__number_value__':
            num_value = columnCalculationBuilder['mainColumn']['columnNumberValue']
        elif is_date(item[columnCalculationBuilder['mainColumn']['column']]):
            spl = columnCalculationBuilder['mainColumn']['rangeColumn'].split('___')
            num_value = date_difference(item[columnCalculationBuilder['mainColumn']['column']], item[spl[1]], spl[0])
        else:
            num_value = item[columnCalculationBuilder['mainColumn']['column']]
        if num_value is not None and columnCalculationBuilder['mainColumn']['column'] != '__number_value__' and 'rounding' in columnCalculationBuilder['mainColumn'] and columnCalculationBuilder['mainColumn']['rounding'] != 'none' and columnCalculationBuilder['mainColumn']['rounding'] != None:
            if columnCalculationBuilder['mainColumn']['rounding'] == 'up':
                num_value = math.ceil(num_value)
            elif columnCalculationBuilder['mainColumn']['rounding'] == 'down':
                num_value = math.floor(num_value)
            else:
                num_value = round(num_value)
        code += str(num_value)
        if highPrecisionMode == 'yes':
            code += "))"
    else:
        partial_code = get_column_calculation_code(columnCalculationBuilder['mainColumn']['columnCalculationBuilder'], highPrecisionMode, item)
        if partial_code:
            if 'rounding' in columnCalculationBuilder['mainColumn'] and columnCalculationBuilder['mainColumn']['rounding'] != 'none' and columnCalculationBuilder['mainColumn']['rounding'] != None:
                if columnCalculationBuilder['mainColumn']['rounding'] == 'up':
                    code += "math.ceil"
                elif columnCalculationBuilder['mainColumn']['rounding'] == 'down':
                    code += "math.floor"
                else:
                    code += "round"
            code += "(" + partial_code + ")"
    for col in columnCalculationBuilder['columns']:
        co = col['calculationOperator']
        if co != '/' and co != '*' and co != '+' and co != '-':
            return None
        code += co
        if col['type'] is None:
            return None
        if col['type'] == 'column':
            if highPrecisionMode == 'yes':
                code += "Decimal(str("
            if col['column'] == '__number_value__':
                num_value = col['columnNumberValue']
            elif is_date(item[col['column']]):
                spl = col['rangeColumn'].split('___')
                num_value = date_difference(item[col['column']], item[spl[1]], spl[0])
            else:
                num_value = item[col['column']]
            if num_value is not None and col['column'] != '__number_value__' and 'rounding' in col and col['rounding'] != 'none' and col['rounding'] != None:
                if col['rounding'] == 'up':
                    num_value = math.ceil(num_value)
                elif col['rounding'] == 'down':
                    num_value = math.floor(num_value)
                else:
                    num_value = round(num_value)
            code += str(num_value)
            if highPrecisionMode == 'yes':
                code += "))"
        else:
            partial_code = get_column_calculation_code(
                col['columnCalculationBuilder'], highPrecisionMode, item)
            if partial_code:
                if 'rounding' in col and col['rounding'] != 'none' and col['rounding'] != None:
                    if col['rounding'] == 'up':
                        code += "math.ceil"
                    elif col['rounding'] == 'down':
                        code += "math.floor"
                    else:
                        code += "round"
                code += "(" + partial_code + ")"
    return code


def calculate_column(calculation, highPrecisionMode):
    try:
        # Create a namespace dictionary with parameters for exec() and eval()
        namespace = {'result': None}

        # Using exec() to execute the Python code
        exec("result = " + calculation, globals(), namespace)

        # Using eval() to get the result
        if highPrecisionMode == 'yes':
            result = float(namespace.get('result'))
        else:
            result = namespace.get('result')
        return result
    except Exception as e:
        _logger.error("An exception occurred", exc_info=e)
        return None

def get_demo_row_sql(query, sn_cr):
    custom_query = """
    SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;
    BEGIN TRANSACTION;
        SET statement_timeout=60000;
        SELECT * FROM (%s) AS FirstRow LIMIT 100;
    """ % query
    sn_cr.execute(custom_query)
    row = sn_cr.dictfetchall()
    sn_cr.execute("ROLLBACK;")
    return row

def get_rows_sql(query, sn_cr, columns, where):
    if len(columns) > 0:
        custom_query = """
        SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;
        BEGIN TRANSACTION;
            SET statement_timeout=720000;
            SELECT """ + ', '.join(columns) + """ FROM (""" + query + """) AS FirstRow """ + where + """;"""
    else:
        custom_query = """
        SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;
        BEGIN TRANSACTION;
            SET statement_timeout=720000;
            SELECT * """ + """ FROM (""" + query + """) AS FirstRow """ + where + """;"""
    _logger.info("SQL RES %S", custom_query)
    sn_cr.execute(custom_query)
    rows = sn_cr.dictfetchall()
    sn_cr.execute("ROLLBACK;")

    return rows

def get_data_type_sql(data_type):
    if data_type == 'txid_snapshot' or data_type == 'pg_snapshot' \
            or data_type == 'tsvector' or data_type == 'point' \
            or data_type == 'polygon' or data_type == 'path' \
            or data_type == 'box' or data_type == 'bytea' \
            or data_type == 'circle' or data_type == 'line' \
            or data_type == 'lseg':
        return None
    if data_type == 'boolean' or data_type == 'bool':
        return 'bool'
    elif data_type == 'real' or data_type == 'float4' \
            or data_type == 'smallint' or data_type == 'int2' \
            or data_type == 'smallserial' or data_type == 'serial2' \
            or data_type == 'serial' or data_type == 'serial4' \
            or data_type == 'numeric' or data_type == 'decimal' \
            or data_type == 'money' or data_type == 'bigint' \
            or data_type == 'int8' or data_type == 'serial8' \
            or data_type == 'bigserial' or data_type == 'double precision' \
            or data_type == 'float8' or data_type == 'integer' \
            or data_type == 'int' or data_type == 'int4':
        return 'number'
    elif data_type == 'date' or data_type == 'datetime' or 'time' in data_type:
        return 'date'
    elif data_type == 'jsonb':
        return 'json'
    else:
        return 'text'
def get_data_type(value):
    if value['type'] == 'boolean':
        return 'bool'
    elif value['type'] == 'monetary' or value['type'] == 'float' \
            or value['type'] == 'many2one_reference' or value['type'] == 'many2one' \
            or value['type'] == 'integer':
        return 'number'
    elif value['type'] == 'date' or value['type'] == 'datetime':
        return 'date'
    elif value['type'] == 'selection' or value['type'] == 'text':
        return 'text'
    elif value['type'] == 'one2many' or value['type'] == 'reference' or value['type'] == 'many2many':
        return 'text'
    else:
        return 'text'

def get_sql_from_dataset(dataset_id, token, exclude_filters = False):
    response = requests.post(
        sn_url + "/Datasets/get_sql_from_dataset",
        json={'dataset_id': dataset_id, 'exclude_filters': exclude_filters},
        headers={'content-type': 'application/json', 'Authorization': token})
    if not response.ok:
        return None
    res = response.json()
    query = res
    return query

def get_allowed_native_columns(modelName, token):
    response = requests.get(sn_url + "/NativeDatasets/get_columns?model=" + modelName, headers={
        'Authorization': token
    })
    if not response.ok:
        return { 'hasAccess': False, 'columns': [] }
    res = response.json()
    return res
def get_model_fields(modelName, token, nativeAllowedOnly = True):
    if is_custom_dataset(modelName, token):
        try:
            res = get_sql_from_dataset(modelName, token, True)
            if res is None:
                return []
            query = res['sql_text']
            calculation_columns = res['calculation_columns']
        except Exception as e:
            _logger.error("An exception occurred", exc_info=e)
            return { 'status': 400 }
        db = sql_db.db_connect(http.request.env.cr.dbname)
        with closing(db.cursor()) as sn_cr:
            try:
                row = get_first_row_sql(query, sn_cr, [])
                if row is None:
                    return []
                keys = list(row.keys())
                columns = list(map(lambda x: "pg_typeof(" + x + ") AS " + x, keys))
                _logger.info('Testing Columns %s', columns)
                types = get_first_row_sql(query, sn_cr, columns)
                fields = []
                for key, value in types.items():
                    data_type = get_data_type_sql(value)
                    if data_type is None:
                        continue
                    new_field = {
                        'label': ' '.join(list(map(lambda x: x.capitalize(), key.split('_')))),
                        'value': key,
                        'type': data_type,
                        'is_odoo_partial_column': False,
                        'searchable': True
                    }
                    if data_type == 'json':
                        new_field['searchable'] = False
                    if data_type == 'bool':
                        new_field['isgroup'] = True
                    elif data_type == 'number':
                        if key.endswith('_id') or key == 'id':
                            new_field['isgroup'] = True
                        else:
                            new_field['ismeasure'] = True
                    elif data_type == 'date':
                        new_field['isgroup'] = True
                    else:
                        new_field['isgroup'] = True
                    fields.append(new_field)
                for col in calculation_columns:
                    new_field = {
                        'label': ' '.join(list(map(lambda x: x.capitalize(), col['alias'].split('_')))),
                        'value': col['alias'],
                        'type': 'number',
                        'searchable': False,
                        'is_odoo_partial_column': False,
                        'ismeasure': True
                    }
                    fields.append(new_field)
                return fields
            except Exception as e:
                _logger.error("An exception occurred", exc_info=e)
                return None
    else:
        if modelName in forbidden_models:
            return []
        unprocessed_fields = http.request.env[modelName].fields_get()
        fields = []
        native_allowed_columns = []
        if nativeAllowedOnly:
            native_allowed_columns = get_allowed_native_columns(modelName, token)['columns']
            _logger.info('native columns %s', native_allowed_columns)
        unprocessed_field_items = unprocessed_fields.items()
        _logger.info('unprocessed field items %s', unprocessed_field_items)
        for key, value in unprocessed_field_items:
            if nativeAllowedOnly and key in native_allowed_columns:
                continue
            data_type = get_data_type(value)
            label = value['string']
            searchable = False
            if 'searchable' in value:
                searchable = value['searchable']
            if key.endswith("_id"):
                text_field = {
                    'label': label + " Name",
                    'value': key + "_name",
                    'type': "text",
                    'searchable': False,
                    'is_odoo_partial_column': True,
                    'isgroup': True
                }
                fields.append(text_field)

            new_field = {
                'label': label,
                'value': key,
                'type': data_type,
                'searchable': searchable,
                'is_odoo_partial_column': False,
            }
            if data_type == 'bool':
                new_field['isgroup'] = True
            elif data_type == 'number' and (value['type'] == 'many2one_reference' or value['type'] == 'many2one'):
                new_field['isgroup'] = True
            elif data_type == 'number' and value['type'] == 'integer':
                if key.endswith('_id') or key == 'id':
                    new_field['isgroup'] = True
                else:
                    new_field['ismeasure'] = True
            elif data_type == 'number':
                new_field['ismeasure'] = True
            elif data_type == 'date':
                new_field['isgroup'] = True
            elif data_type == 'text' and not (value['type'] == 'one2many' or value['type'] == 'reference' or value['type'] == 'many2many'):
                new_field['isgroup'] = True

            fields.append(new_field)
        return fields

def get_custom_dataset_options(token):
    response = requests.get(sn_url + "/Datasets/get_custom_options", headers={
        'Authorization': token
    })
    if not response.ok:
        return []
    res = response.json()
    return res

def validate_query(token, query):
    response = requests.post(
        sn_url + "/Datasets/validate_query",
        json= { 'query': query },
        headers={'content-type': 'application/json', 'Authorization': token})
    if not response.ok:
        if response.status_code == 400:
            return {'error': None, 'is_valid': True}
        return None
    content = response.json()
    return content

def validate_columns(columns, token):
    response = requests.post(
        sn_url + "/Datasets/validate_query_columns",
        json={ 'columns': columns },
        headers={'content-type': 'application/json', 'Authorization': token})
    if not response.ok:
        return None
    content = response.json()
    return content

def get_allowed_native_models(token):
    response = requests.get(sn_url + "/NativeDatasets/get_allowed_models", headers={
        'Authorization': token
    })
    if not response.ok:
        return []
    res = response.json()
    return res

def get_dataset_options(token, nativeAllowedOnly = True):
    dataset_models = get_custom_dataset_options(token)
    if nativeAllowedOnly:
        models = get_allowed_native_models(token)
        unprocessed_models = http.request.env['ir.model'].sudo().search([('model', 'not in', forbidden_models), ('model', 'in', models)]).read(
            ['model', 'name'])
    else:
        unprocessed_models = http.request.env['ir.model'].sudo().search([('model', 'not in', forbidden_models)]).read(['model', 'name'])
    models = dataset_models + list(map(lambda x: { 'value': x['model'], 'label': x['name'] }, unprocessed_models))
    return models

def get_all_dataset_keys():
    datasets = http.request.env['sn.custom.dataset'].search([]).read(['dataset_id'])
    dataset_keys = []
    for dataset in datasets:
        dataset_keys.append(dataset['dataset_id'])
    unprocessed_models = http.request.env['ir.model'].sudo().search([]).read(['model'])
    keys = dataset_keys + list(map(lambda x: x['model'], unprocessed_models))
    return keys

def has_dataset(model, token):
    is_custom = is_custom_dataset(model, token)
    is_model = model not in forbidden_models and len(http.request.env['ir.model'].sudo().search([('model', '=', model)]).read(['id'])) > 0
    return is_custom or is_model
def has_field(modelName, field, token):
    fields = get_model_fields(modelName, token, False)
    if fields is None:
        return False
    filtered_fields = list(filter(lambda x: x['value'] == field and x['is_odoo_partial_column'] is False, fields))
    return len(filtered_fields) > 0

def has_model_field(model, field):
    unprocessed_models = http.request.env['ir.model'].sudo().search([('model', '=', model)]).read(['model'])
    if len(unprocessed_models) == 0 or model in forbidden_models:
        return json.dumps({'data': False, 'status': 200})
    unprocessed_fields = http.request.env[model].sudo().fields_get()
    has_field = False
    for key, value in unprocessed_fields.items():
        if key == field:
            has_field = True
    return has_field
def has_field_in_query(query, field):
    db = sql_db.db_connect(http.request.env.cr.dbname)
    with closing(db.cursor()) as sn_cr:
        try:
            row = get_first_row_sql(query, sn_cr, [])
            return field in row
        except Exception as e:
            _logger.error("An exception occurred", exc_info=e)
            return False
    return False

def get_fields_from_query(query, calculation_columns):
    db = sql_db.db_connect(http.request.env.cr.dbname)
    with closing(db.cursor()) as sn_cr:
        try:
            row = get_first_row_sql(query, sn_cr, [])
            keys = list(row.keys())
            columns = list(map(lambda x: "pg_typeof(" + x + ") AS " + x, keys))
            types = get_first_row_sql(query, sn_cr, columns)
            fields = []
            for key, value in types.items():
                curr_value = get_data_type_sql(value)
                if curr_value is None:
                    continue
                new_field = {'label': ' '.join(list(map(lambda x: x.capitalize(), key.split('_')))), 'value': key, 'type': curr_value }
                fields.append(new_field)
            for col in calculation_columns:
                new_field = {'label': ' '.join(list(map(lambda x: x.capitalize(), col['alias'].split('_')))), 'value': col['alias'],
                             'type': 'number'}
                fields.append(new_field)
            return fields
        except Exception as e:
            _logger.error("An exception occurred", exc_info=e)
            return []

def get_filter_value(filter, data_type):
    value = filter["value"]
    if value == "${userId}":
        if not data_type or data_type == 'number':
            value = http.request.uid
        else:
            value = str(http.request.uid)
    if value == "${null}":
        value = False
    if value == "${companyId}":
        if not data_type or data_type == 'number':
            value = http.request.env.company.id
        else:
            value = str(http.request.env.company.id)
    if isinstance(value, str) and data_type == 'number':
        value = int(value)
    return value

def get_sql_comparator(curr_filter, data_type):
    comparator = '='
    if 'compare' in curr_filter:
        value = get_filter_value(curr_filter, data_type)
        if curr_filter['compare'] == 'equals' and value == False:
            comparator = 'is'
        elif curr_filter['compare'] == 'not_contains':
            comparator = 'not like'
        elif curr_filter['compare'] == 'contains':
            comparator = 'like'
        elif curr_filter['compare'] == 'not_equals' and value == False:
            comparator = 'is not'
        elif curr_filter['compare'] == 'not_equals':
            comparator = '!='
        elif curr_filter['compare'] == 'more_or_equals':
            comparator = '>='
        elif curr_filter['compare'] == 'less_or_equals':
            comparator = '<='
        elif curr_filter['compare'] == 'more':
            comparator = '>'
        elif curr_filter['compare'] == 'less':
            comparator = '<'
    return comparator

def get_sql(token, build_method, query, query_builder, exclude_filters = False):
    response = requests.post(
        sn_url + "/Datasets/get_sql",
        json= { 'query': query, 'buildMethod': build_method, 'queryBuilder': query_builder, 'excludeFilters': exclude_filters },
        headers={'content-type': 'application/json', 'Authorization': token})
    _logger.info("get_sql response: %s", response)
    if not response.ok:
        if response.status_code == 400:
            return 400
        return None
    content = response.json()
    try:
        db = sql_db.db_connect(http.request.env.cr.dbname)
        with closing(db.cursor()) as sn_cr:
            comp = sql.Composed([sql.SQL(content['query'])])
            sql_result = comp.as_string(sn_cr._obj)
    except:
        return None
    content = response.json()
    return content['query']


def get_flat_item(item):
    flat_item = {**item}
    for key, value in item.items():
        if key.endswith("_id") and isinstance(value, tuple) and len(value) == 2:
            flat_item[key] = value[0]
            flat_item[key + "_name"] = str(value[1])
    return flat_item

def get_comparator(curr_filter, data_type):
    comparator = '='
    if 'compare' in curr_filter:
        value = get_filter_value(curr_filter, data_type)
        if curr_filter['compare'] == 'equals' and value and isinstance(value, str):
            comparator = '=ilike'
        elif curr_filter['compare'] == 'not_contains':
            comparator = 'not ilike'
        elif curr_filter['compare'] == 'contains':
            comparator = 'ilike'
        elif curr_filter['compare'] == 'not_equals':
            comparator = '!='
        elif curr_filter['compare'] == 'more_or_equals':
            comparator = '>='
        elif curr_filter['compare'] == 'less_or_equals':
            comparator = '<='
        elif curr_filter['compare'] == 'more':
            comparator = '>'
        elif curr_filter['compare'] == 'less':
            comparator = '<'
    return comparator

def get_default_converted_filters(default_filters):
    default_converted_filters = []
    for default_filter in default_filters:
        data_type = default_filter['dataType']
        if data_type == 'date':
            val = get_dynamic_date(default_filter['type'], default_filter['period'], default_filter['back'],
                                   default_filter['date'])
            default_converted_filters.append((default_filter['field'], '>=', val['start_date']))
            default_converted_filters.append((default_filter['field'], '<=', val['end_date']))
        elif default_filter['value'] is None and default_filter['type'] == 'with_null':
            _logger.info('SimplyNeatDashTest: Went Into Select All Active')
            default_converted_filters.append((default_filter['field'], 'in', [True, False]))
        else:
            comparator = get_comparator(default_filter, data_type)
            _logger.info('SimplyNeatDashTest: Went Into Select %s', default_filter)
            value = get_filter_value(default_filter, data_type)
            default_converted_filters.append((default_filter['field'], comparator, value))

    return default_converted_filters


def get_filtered_ids(filters, default_converted_filters, modelName):
    converted_filters = default_converted_filters.copy()
    filter_ids = []
    index = 0
    for curr_filter in filters:
        data_type = curr_filter['dataType']
        if index != 0 and curr_filter['operator'] == 'or':
            _logger.info('SimplyNeatDashTest: Or Converted Filters %s', converted_filters)
            curr_records = http.request.env[modelName].search(converted_filters).read(['id'])
            for record in curr_records:
                filter_ids.append(record['id'])
            converted_filters = default_converted_filters.copy()

        if data_type == 'date':
            val = get_dynamic_date(curr_filter['type'], curr_filter['period'], curr_filter['back'],
                                   curr_filter['date'])
            converted_filters.append((curr_filter['field'], '>=', val['start_date']))
            converted_filters.append((curr_filter['field'], '<=', val['end_date']))
        elif curr_filter['value'] is None and curr_filter['type'] == 'with_null':
             converted_filters.append((curr_filter['field'], 'in', [True, False]))
        else:
            comparator = get_comparator(curr_filter, data_type)
            value = get_filter_value(curr_filter, data_type)
            converted_filters.append((curr_filter['field'], comparator, value))
        index+=1

    if len(converted_filters) > 0:
        curr_records = http.request.env[modelName].search(converted_filters).read(['id'])
        for record in curr_records:
            filter_ids.append(record['id'])

    return filter_ids

def format_date(input_date):
    year = str(input_date.year)
    month = str(input_date.month).zfill(2)  # zero-fill to ensure two digits
    day = str(input_date.day).zfill(2)      # zero-fill to ensure two digits

    return '-'.join([year, month, day])


def subtract_months(current_date, months):
    year = current_date.year
    month = current_date.month
    for _ in range(months):
        if month == 1:
            year -= 1
            month = 12
        else:
            month -= 1

    return datetime(year, month, 1)

def add_months(current_date, months):
    year = current_date.year
    month = current_date.month
    for _ in range(months):
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1

    return datetime(year, month, 1)
def get_dynamic_date(date_type, period, back, date):
    if date_type == 'dynamic_range':
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if period == 'day':
            start_date -= timedelta(days=back)
            end_date -= timedelta(days=back)
            end_date += timedelta(days=1)
        elif period == 'week':
            day = start_date.weekday()
            adjusted_day = (day if day != 0 else 7)
            start_date -= timedelta(days=adjusted_day + (back * 7))
            end_date = start_date + timedelta(days=6)
        elif period == 'month':
            start_date =  subtract_months(start_date, back)
            end_date = add_months(start_date, 1) - timedelta(days=1)
        elif period == 'last_30_days':
            end_date -= timedelta(days=back * 30)
            start_date -= timedelta(days=(back + 1) * 30)
        elif period == 'quarter':
            quarter = ((start_date.month - 1) // 3) + 1
            start_date = datetime(start_date.year, quarter * 3, 1)
            start_date = subtract_months(start_date, (back * 3) + 2)
            end_date = add_months(start_date, 3) - timedelta(days=1)
        elif period == 'year':
            start_date = datetime(start_date.year - back, 1, 1)
            end_date = datetime(start_date.year, 12, 31)
        elif period == 'two_years':
            start_date = datetime(start_date.year - (back * 2), 1, 1)
            end_date = datetime(start_date.year + 2, 12, 31)
        result = {'start_date': format_date(start_date), 'end_date': format_date(end_date)}
        _logger.info('get_dynamic_date: %s', result)
        return result
    else:
        return {'start_date': date['startDate'], 'end_date': date['endDate']}

def get_default_converted_filters_sql(default_filters, cr):
    default_converted_filters = []
    for default_filter in default_filters:
        params = []
        data_type = default_filter['dataType']
        if data_type == 'date':
            val = get_dynamic_date(default_filter['type'], default_filter['period'], default_filter['back'], default_filter['date'])
            params.append(sql.Identifier(default_filter["field"]))
            params.append(sql.SQL(" >= "))
            params.append(sql.Literal(val['start_date']))
            params.append(sql.SQL(" AND "))
            params.append(sql.Identifier(default_filter["field"]))
            params.append(sql.SQL(" <= "))
            params.append(sql.Literal(val['end_date']))
        elif default_filter['value'] is None and default_filter['type'] == 'with_null':
            _logger.info('SimplyNeatDashTest: Went Into Select All Active')
            params.append(sql.Identifier(default_filter["field"]))
            params.append(sql.SQL(' IN(True, False)'))
        else:
            comparator = get_sql_comparator(default_filter, data_type)
            params.append(sql.Identifier(default_filter["field"]))
            value = get_filter_value(default_filter, data_type)
            if value == False:
                params.append(sql.SQL(" " + comparator + " NULL"))
            else:
                params.append(sql.SQL(" " + comparator + " "))
                if comparator == 'like' or comparator == 'not like':
                    params.append(sql.SQL(" '%' || "))
                    params.append(sql.Literal(value))
                    params.append(sql.SQL(" || '%'"))
                else:
                    params.append(sql.Literal(value))
        comp = sql.Composed(params)
        res = comp.as_string(cr._obj)
        default_converted_filters.append(res)
    return ' AND '.join(default_converted_filters)

def get_converted_record_rules_sql(matched_record_rules, sn_cr):
    converted_filters = []
    records_index = 0
    for filters in matched_record_rules:
        index = 0
        if len(filters) > 0:
            converted_filters.append("(")
            for curr_filter in filters:
                params = []
                data_type = curr_filter['dataType']
                if index != 0 and curr_filter['operator'] == 'or':
                    converted_filters.append("OR")
                elif index > 0:
                    converted_filters.append("AND")

                if data_type == 'date':
                    val = get_dynamic_date(curr_filter['type'], curr_filter['period'], curr_filter['back'],
                                           curr_filter['date'])
                    params.append(sql.Identifier(curr_filter["field"]))
                    params.append(sql.SQL(" >= "))
                    params.append(sql.Literal(val['start_date']))
                    params.append(sql.SQL(" AND "))
                    params.append(sql.Identifier(curr_filter["field"]))
                    params.append(sql.SQL(" <= "))
                    params.append(sql.Literal(val['end_date']))
                elif curr_filter['value'] is None and curr_filter['type'] == 'with_null':
                    params.append(sql.Identifier(curr_filter["field"]))
                    params.append(sql.SQL(' IN(True, False)'))
                else:
                    comparator = get_sql_comparator(curr_filter, data_type)
                    params.append(sql.Identifier(curr_filter["field"]))
                    value = get_filter_value(curr_filter, data_type)
                    if value == False:
                        params.append(sql.SQL(" " + comparator + " NULL"))
                    else:
                        params.append(sql.SQL(" " + comparator + " "))
                        if comparator == 'like' or comparator == 'not like':
                            params.append(sql.SQL(" '%' || "))
                            params.append(sql.Literal(value))
                            params.append(sql.SQL(" || '%'"))
                        else:
                            params.append(sql.Literal(value))

                comp = sql.Composed(params)
                res = comp.as_string(sn_cr._obj)
                converted_filters.append(res)
                index+=1
            converted_filters.append(")")
            if  records_index < len(matched_record_rules) - 1:
                converted_filters.append("OR")
            records_index+=1

    return ' '.join(converted_filters)


def get_filter_query_sql(filters, default_converted_filters, converted_record_rules, sn_cr):
    converted_filters = []
    whereQuery = ""
    if len(filters) > 0 or len(default_converted_filters) > 0 or len(converted_record_rules) > 0:
        whereQuery = " WHERE "

    if len(converted_record_rules) > 0:
        _logger.info('Record Rules:  %s', converted_record_rules)
        converted_filters.append("(")
        converted_filters.append(converted_record_rules)
        converted_filters.append(")")
        if len(filters) > 0 or len(default_converted_filters) > 0:
            converted_filters.append("AND")
            converted_filters.append("(")

    if len(default_converted_filters) > 0:
        converted_filters.append(default_converted_filters)
        if len(filters) > 0:
            converted_filters.append("AND")

    index = 0
    for curr_filter in filters:
        params = []
        data_type = curr_filter['dataType']
        if index != 0 and curr_filter['operator'] == 'or':
            converted_filters.append("OR")
            converted_filters.append(default_converted_filters)
        elif index > 0:
            converted_filters.append("AND")

        if data_type == 'date':
            val = get_dynamic_date(curr_filter['type'], curr_filter['period'], curr_filter['back'], curr_filter['date'])
            params.append(sql.Identifier(curr_filter["field"]))
            params.append(sql.SQL(" >= "))
            params.append(sql.Literal(val['start_date']))
            params.append(sql.SQL(" AND "))
            params.append(sql.Identifier(curr_filter["field"]))
            params.append(sql.SQL(" <= "))
            params.append(sql.Literal(val['end_date']))
        elif curr_filter['value'] is None and curr_filter['type'] == 'with_null':
            params.append(sql.Identifier(curr_filter["field"]))
            params.append(sql.SQL(' IN(True, False)'))
        else:
            comparator = get_sql_comparator(curr_filter, data_type)
            params.append(sql.Identifier(curr_filter["field"]))
            value = get_filter_value(curr_filter, data_type)
            if value == False:
                params.append(sql.SQL(" " + comparator + " NULL"))
            else:
                params.append(sql.SQL(" " + comparator + " "))
                if comparator == 'like' or comparator == 'not like':
                    params.append(sql.SQL(" '%' || "))
                    params.append(sql.Literal(value))
                    params.append(sql.SQL(" || '%'"))
                else:
                    params.append(sql.Literal(value))

        comp = sql.Composed(params)
        res = comp.as_string(sn_cr._obj)
        converted_filters.append(res)
        index+=1
    if len(converted_record_rules) > 0 and  (len(filters) > 0 or len(default_converted_filters) > 0):
        converted_filters.append(")")
    return whereQuery + ' '.join(converted_filters)

def get_odoo_access_rights():
    dashboard_env = http.request.env['sn.dashboard']
    widget_env = http.request.env['sn.widget']
    custom_dataset_env = http.request.env['sn.custom.dataset']
    general_settings_env = http.request.env['sn.general.settings']
    custom_dataset_access_rights_env = http.request.env['sn.access.right']
    user_settings_env = http.request.env['sn.user.settings']
    auth_env = http.request.env['sn.auth']
    sn_dashboard_group_access = http.request.env['sn.dashboard.group.access']
    sn_dashboard_user_access = http.request.env['sn.dashboard.user.access']
    return {
        'data': {
            'dashboard': {
                'read': dashboard_env.check_access_rights('read', raise_exception=False),
                'write': dashboard_env.check_access_rights('write', raise_exception=False),
                'create': dashboard_env.check_access_rights('create', raise_exception=False),
                'unlink': dashboard_env.check_access_rights('unlink', raise_exception=False),
            },
            'dashboard_access_rights': {
                'read': sn_dashboard_group_access.check_access_rights(
                    'read', raise_exception=False) and sn_dashboard_user_access.check_access_rights('read', raise_exception=False),
                'write': sn_dashboard_group_access.check_access_rights(
                    'write', raise_exception=False) and sn_dashboard_user_access.check_access_rights('write', raise_exception=False),
                'create': sn_dashboard_group_access.check_access_rights(
                    'create', raise_exception=False) and sn_dashboard_user_access.check_access_rights('create', raise_exception=False),
                'unlink': sn_dashboard_group_access.check_access_rights(
                    'unlink', raise_exception=False) and sn_dashboard_user_access.check_access_rights('unlink', raise_exception=False),
            },
            'widget': {
                'read': widget_env.check_access_rights('read', raise_exception=False),
                'write': widget_env.check_access_rights('write', raise_exception=False),
                'create': widget_env.check_access_rights('create', raise_exception=False),
                'unlink': widget_env.check_access_rights('unlink', raise_exception=False),
            },
            'custom_dataset': {
                'read': custom_dataset_env.check_access_rights('read', raise_exception=False),
                'write': custom_dataset_env.check_access_rights('write', raise_exception=False),
                'create': custom_dataset_env.check_access_rights('create', raise_exception=False),
                'unlink': custom_dataset_env.check_access_rights('unlink', raise_exception=False),
            },
            'custom_dataset_access_rights': {
                'read': custom_dataset_access_rights_env.check_access_rights('read', raise_exception=False),
                'write': custom_dataset_access_rights_env.check_access_rights('write', raise_exception=False),
                'create': custom_dataset_access_rights_env.check_access_rights('create', raise_exception=False),
                'unlink': custom_dataset_access_rights_env.check_access_rights('unlink', raise_exception=False),
            },
            'user_settings': {
                'read': user_settings_env.check_access_rights('read', raise_exception=False),
                'write': user_settings_env.check_access_rights('write', raise_exception=False),
                'create': user_settings_env.check_access_rights('create', raise_exception=False),
                'unlink': user_settings_env.check_access_rights('unlink', raise_exception=False),
            },
            'auth': {
                'read': auth_env.check_access_rights('read', raise_exception=False),
                'write': auth_env.check_access_rights('write', raise_exception=False),
                'create': auth_env.check_access_rights('create', raise_exception=False),
                'unlink': auth_env.check_access_rights('unlink', raise_exception=False),
            },
            'general_settings': {
                'read': general_settings_env.check_access_rights('read', raise_exception=False),
                'write': general_settings_env.check_access_rights('write', raise_exception=False),
                'create': general_settings_env.check_access_rights('create', raise_exception=False),
                'unlink': general_settings_env.check_access_rights('unlink', raise_exception=False),
            }

        },
        'status': 200
    }