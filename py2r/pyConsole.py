

from ast import parse as ast_parse, \
    literal_eval, Module, Interactive
from rpy2 import robjects
from traceback import format_exc
from io import StringIO
from contextlib import redirect_stdout
r = robjects.r
try:
    from ast import unparse as ast_unparse
except ImportError:
    try:
        from astunparse import unparse as ast_unparse
    except ModuleNotFoundError:
        raise ModuleNotFoundError(
            "Can't find a ast unparse function -- you'll need python 3.9+ "
            "or (pip/conda) install astunparse"
        )

import sys
from contextlib import redirect_stdout, redirect_stderr, contextmanager


@contextmanager
def capture_displayhook(acc):
    def dh(value):
        acc.append(value)

    old_dh = sys.displayhook
    try:
        sys.displayhook = dh
        yield
    finally:
        sys.displayhook = old_dh

def extract_executable_strings(code_str: str):
    """
    A variant of exec that can run multi line,
    and capture sys_displayhook
    """
    for each in ast_parse(code_str).body:
        command = ast_unparse(each)
        if 'print(' in command:
            f = StringIO()
            with redirect_stdout(f):
                exec(command, globals(), locals())
            yield f.getvalue().strip()
        else:
            acc = []
            with capture_displayhook(acc):
                exec(compile(Interactive([each]), "<pyConsole>", "single"), globals(), locals())
            if len(acc) == 1:
                yield acc[0]
            else:
                yield None


def run_py(cmd, updateDataSet=False, datasetName=None,
           parent_id=None, output_id=None, **kwargs):
    try:
        for result in extract_executable_strings(cmd):
            if result:
                yield {
                    "message": str(result),
                    "caption": "",
                    "type": "console",
                    "code": 200,
                    "updateDataSet": updateDataSet,
                    "name": datasetName,
                    "cmd": cmd,
                    "eval": True,
                    "parent_id": parent_id,
                    "output_id": output_id
                }
    except:
        yield {
            "message": format_exc(),
            "caption": "",
            "type": 'console',
            "code": 500,
            "updateDataSet": updateDataSet,
            "name": datasetName,
            "cmd": cmd,
            "eval": True,
            "parent_id": parent_id,
            "output_id": output_id
        }
    finally:
        yield {
            "message": "",
            "caption": "",
            "type": "processing_done",
            "code": 200,
            "updateDataSet": updateDataSet,
            "name": datasetName,
            "cmd": cmd,
            "eval": True,
            "parent_id": parent_id,
            "output_id": output_id
        }