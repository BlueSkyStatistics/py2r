from math import isnan
from rpy2.rinterface import NULL as NULL
from rpy2.rinterface import NAIntegerType

from py2r.config import rtypes, max_columns

def convert_listvector(r_response, limit=100):
    rett_type = "table"
    result, rett_type = convert_matrix(r_response[6])
    return result, rett_type

def convert_matrix(r_response, limit=100):
    rett_type = 'table'
    result = []
    for row in range(r_response.nrow):
        result.append([])
    for index in range(len(r_response)):
        data, _ = convert_to_data(r_response[index], limit, True)
        result[index % r_response.nrow].append(data)
    if hasattr(r_response, "colnames") and r_response.colnames != NULL:
        result = [list(r_response.colnames)]+result
    if hasattr(r_response, "rownames") and r_response.rownames != NULL:
        pass
    return result, rett_type

def convert_table(r_response, limit=20):
    data = {}
    rett_type = 'table'
    response = []
    if hasattr(r_response, "colnames"):
        for index, each in enumerate(r_response.colnames):
            data[each] = []
            data[each], _ = convert_to_data(r_response[index], limit, True)
    elif hasattr(r_response, "names"):
        if r_response.names != NULL:
            if (list(r_response.names) == ['value', 'visible']):
                return convert_to_data(r_response[0], limit=limit)
            for index, each in enumerate(r_response.names):
                data[each] = []
                data[each], _ = convert_to_data(r_response[index], limit, False)
    if list(data.keys()):
        keys = list(data.keys())[:max_columns]
        response = [keys]
        longest = []
        for x in data.keys():
            try:
                longest.append(len(data[x]))
            except:
                longest.append(0)
        max_index = max(longest)
        try:
            for i in range(max_index if max_index < limit else limit):
                _arr = []
                for j in range(len(keys)):
                    try:
                        _arr.append(data[keys[j]][i])
                    except IndexError:
                        _arr.append("")
                response.append(_arr[:limit+1])
        except TypeError:
            _arr = []
            for _, value in data.items():
                _arr.append(value)
                if len(_arr) == max_columns:
                    response.append(_arr)
                    _arr = []
                if len(response) == limit:
                    break
    return response, rett_type


def convert_to_data(r_response, limit=20, is_table=False):
    is_factor = hasattr(r_response, "levels")
    _array = r_response
    if is_table:
        _array = r_response[:limit]
    if not hasattr(r_response, "typeof"):
        return r_response, type(r_response)
    if isinstance(r_response.typeof, int):
        type_name = rtypes[r_response.typeof]
    else:
        type_name = r_response.typeof.name
    if is_factor:
        isNA = isinstance(_array[0], NAIntegerType)
        response =['NA'] if isNA else [r_response.levels[x - 1] for x in _array]
        rett_type = 'array'
    elif type_name == 'REALSXP':
        response = [_clear_nan(x) for x in _array]
        rett_type = 'array'
        if len(response) == 1:
            response = response[0]
            rett_type = 'float'
    elif type_name == 'INTSXP':
        response = []
        for x in _array:
            try:
                response.append(_clear_nan(x))
            except:
                response.append(0)
        rett_type = 'array'
        if len(response) == 1:
            response = response[0]
            rett_type = 'int'
    elif type_name == 'VECSXP':
        response, rett_type = convert_table(r_response, limit=limit)
    elif type_name == 'STRSXP':
        rett_type = 'array'
        response = [str(x) for x in _array]
    elif type_name == "LGLSXP":
        rett_type = 'boolean'
        response = r_response[0]
    elif type_name == "NILSXP":
        rett_type = rtypes[r_response.typeof]
        response = r_response
    else:
        rett_type = rtypes[r_response.typeof]
        response = str(r_response)
    return response, rett_type

def _clear_nan(x):
    return "" if isnan(x) else x