import tempfile
import os
import logging
from logging.handlers import RotatingFileHandler

# Read TMP from the environment directly so the custom temp path set by Electron
# (via subprocess_config.pyOptions.env.TMP) is honoured. tempfile.gettempdir()
# caches the OS default at import time and misses env vars injected by the parent
# process. Fallback chain: TMP → TEMP → system default.
temp_dir = os.environ.get("TMP") or os.environ.get("TEMP") or tempfile.gettempdir()
log_file_path = os.path.join(temp_dir, "pylog.txt")
logger = logging.getLogger("pyLogger")
logger.setLevel(logging.INFO)
fileHandler = RotatingFileHandler(log_file_path, backupCount=5, maxBytes=2046)
fileHandler.namer = lambda name: name.replace(".log", "") + ".log"
logFormatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
fileHandler.setFormatter(logFormatter)
logger.addHandler(fileHandler)
