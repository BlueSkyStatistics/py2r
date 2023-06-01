import tempfile
import os
import logging
from logging.handlers import RotatingFileHandler

temp_dir = tempfile.gettempdir()
log_file_path = os.path.join(temp_dir, "pylog.txt")
logger = logging.getLogger("pyLogger")
logger.setLevel(logging.INFO)
fileHandler = RotatingFileHandler(log_file_path, backupCount=5, maxBytes=2046)
fileHandler.namer = lambda name: name.replace(".log", "") + ".log"
logFormatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
fileHandler.setFormatter(logFormatter)
logger.addHandler(fileHandler)
