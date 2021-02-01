import random
import string

import rpy2.robjects as robjects

from py2r.data_converter import convert_to_data

def randomString(stringLength=8):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

def str2bool(eval):
    if isinstance(eval, bool):
        return eval
    if eval.lower() in ['true', '1', 'yes', 'y']:
        return True
    return False


def execute_r(cmd, eval=True, limit=20):
    message = robjects.r(cmd)
    if str2bool(eval):
        message, return_type = convert_to_data(message, limit)
    else:
        message = str(message)
        return_type = 'console'
    return message, return_type
