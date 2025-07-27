import random
import string
from .pylogger import logger


from rpy2.robjects import vectors

try:
    logger.info("initializing R...")
    logger.info("If you do not see a success message below this message then that means R failed to launch.")
    import rpy2.robjects as robjects 
    logger.info("R initialized successfully")
except RuntimeError as e:
    logger.exception("Error initializing R from rutils")
    raise e

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


# Convert ListVector to plain Python dict
def listvector_to_dict(lv):
    result = {}
    for i, key in enumerate(lv.names):
        item = lv[i]  # access by index, NOT key
        sub_dict = {}
        for j, subkey in enumerate(item.names):
            val = item[j]  # also access by index
            # Convert R scalar string to Python str
            sub_dict[subkey] = str(val[0]) if len(val) > 0 else None
        result[key] = sub_dict
    return result

def execute_r_complete_list(cmd, eval=True, limit=20):
    message = robjects.r(cmd)
    message = listvector_to_dict(message)
    if str2bool(eval):
        # message, return_type = convert_to_data(message, limit)
        logger.info("the rain in spain limit" +str(limit))
        return_type ="list"
    else:
        message = str(message)
        return_type = 'console'
    return message, return_type


def execute_r(cmd, eval=True, limit=20):
    message = robjects.r(cmd)
    if str2bool(eval):
        message, return_type = convert_to_data(message, limit)
    else:
        message = str(message)
        return_type = 'console'
    return message, return_type

# this function is a copy of the 'execute_r' function above. 
# This function will only be used  in rDataset.getrowcountcolprops() to support Chinese/Turkish column names
# try-except must be used in this function otherwise rpy2 is throwing exception when it finds non-English column names
# and then the column does not load and hence dataset does not refresh. And for this special requirement I do not want 
# to use this the 'execute_r' function above. try-except will make sure that the dataset loading process is not 
# interrupted when non-English column name is found
def execute_r2(cmd, eval=True, limit=20):
    try:
        robjects.r(cmd)
    except Exception:
        return None
    return None
