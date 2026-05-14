import json

from py2r.rDriver import RDriver
from py2r.rUtils import execute_r


class RShellBase:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.r = RDriver()

    def _init_libs(self):
        """Initialize R libraries and return initialization messages."""
        for message in self.r.initiate_libs():
            yield message
        yield {"message": "initialized", "type": "init_done"}

    def _get_r_version(self):
        """Execute R version query and return the version message."""
        r_version_cmd = "RMajorMinorver =list(major = R.version$major, minor = R.version$minor)"
        execute_r(r_version_cmd)
        rc, _ = execute_r("jsonlite::toJSON(RMajorMinorver, na = NULL)")
        r_version = json.loads(rc[0])
        return {"message": r_version, "type": "rversion"}
