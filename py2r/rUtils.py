import random
import string
from .pylogger import logger

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


def execute_r(cmd, eval=True, limit=20):
    #logger.info(f"execute_r: {cmd}")
    message = robjects.r(cmd)
    #logger.info(f"execute_r: {message}")
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
