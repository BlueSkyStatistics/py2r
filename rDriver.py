import re
from os import path, environ
from time import sleep, time
from json import dumps
from tempfile import gettempdir
from traceback import format_exc
from sys import platform


import rpy2.rinterface as ri
import rpy2.robjects as robjects
import rpy2.robjects.vectors as vectors
from rpy2.robjects.packages import importr

from data_converter import *
from config import *
from blueskyparser import blueSkyParser
from rUtils import execute_r, randomString, str2bool
import rDataset as ds

r = robjects.r
bsky = blueSkyParser()

class RDriver:
    if 'win' not in platform or 'darwin' in platform:
        tmpdir = gettempdir()
    else:
        tmpdir = environ.get('TMP', environ.get('TEMP', ""))
    sinkfile = path.join(tmpdir, 'sink.txt')
    sinkfile = sinkfile.replace("\\", "/")

    def initiate_libs(self):
        importr("gdata")
        importr("stringr")
        importr("openxlsx")
        importr("haven")
        importr("readr")
        importr("readxl")
        importr("data.table")
        importr("foreign")
        importr("BlueSky")

    @staticmethod
    def wrap_with_space(match):
        return f"print({match.group(0).strip()})\n"

    def wrapRcommand(self, cmd, dataset_name):
        if "%ds" in cmd:
            cmd = cmd.replace("%ds", dataset_name)
        cmd_arr = cmd.split("\n")
        cmd = ''
        for each in cmd_arr:
            cmd += re.sub(r'^\s?[a-zA-Z0-9]+\n', self.wrap_with_space, f"{each}\n")
        return cmd.strip()

    def openblankds(self, datasetName='Dataset1'):
        for message in ds.openblankdataset(datasetName):
            yield message

    def open(self, file_path=None, datasetName=None, wsName='NULL',
             replace_ds='TRUE', csvHeader='TRUE', char_to_factor='TRUE',
             basket_data='FALSE', csv_sep=',', delim='.'):
        #print(rowendindex)
        filetype = file_path.split(".")[-1].upper()
        worksheets = []
        if filetype in ('XLS', 'XLSX') and wsName == 'NULL':
            worksheets, _ = execute_r(f'GetTableList(excelfilename="{file_path}", xlsx={str("XLSX" in filetype).upper()})')
        if len(worksheets) == 1: # assuming if there is only 1 ws this is it
            wsName = f'"{worksheets[0]}"'
        elif len(worksheets) > 1: # asking to prompt wsName
            yield {
                "message": worksheets,
                "type": 'worksheets',
                "code": 200,
                "updateDataSet": False,
                "name": datasetName,
                "cmd": {
                    "file_path": file_path, 
                    "datasetName": datasetName, 
                    "wsName": wsName,
                    "replace_ds": replace_ds,
                    "csvHeader": csvHeader,
                    "char_to_factor": char_to_factor,
                    "basket_data": basket_data,
                    "csv_sep": csv_sep,
                    "delim": delim
                }
            }
        if len(worksheets) == 0 or wsName != 'NULL':
            for message in ds.open(file_path, filetype, wsName, replace_ds, csvHeader, char_to_factor, basket_data, csv_sep, delim, datasetName):
                yield message


    def refresh(self, datasetName, reloadCols=True, fromrowidx=1, torowidx=20):
        for message in ds.refresh(datasetName, reloadCols, fromrowidx, torowidx):
            yield message

    @staticmethod
    def close_devices():
        # Weird workaround to make ggplot work
        r("""dev.set(1)
dev.off()
""")
        r("""dev.set(2)
dev.off()""")


    def run(self, cmd, eval=True, limit=20, updateDataSet=False, datasetName=None, parent_id=None, output_id=None, test=False):
        code = 200
        return_type = None
        sanitized_cmd = self.wrapRcommand(cmd, datasetName)
        filename = "/".join([self.tmpdir, f"{randomString()}%03d.{images}"])
        filename = filename.replace("\\", "/")
        yield {"message": sanitized_cmd, "type": "log"}
        try:
            # opening graphics device
            r(f"""{images}(filename='{filename}', width={image_wigth}, height={image_height})""")
            # opening sink file
            r(f"""fp <- file("{self.sinkfile}", open = "wt")
options("warn" = 1)
sink(fp)
sink(fp, type = "message")""")
            # Executing R
            message=r(f"""
dev.set(2)
{sanitized_cmd}
""")
            # closing sink file
            r("""sink(type = "message")
sink()
flush(fp)
close(fp)""")
            # turning off graphical device
        except ri.RRuntimeError as err:
            code = 400
            return_type = "exception"
            message = f"SERVER STATE EXCEPTION: \n {format(format_exc())}"
            yield {"message": str(message), "type": "log"}
            yield {"message": str(err),
                "type": return_type,
                "code": code,
                "updateDataSet": False,
                "name": datasetName,
                "cmd": cmd,
                "eval": False,
                "parent_id": parent_id,
                "output_id": output_id
            }
        except Exception as err:
            code = 500
            return_type = "exception"
            message = format(err)
            yield {"message": str(message), "type": "log"}
        finally:
            r("""dev.off()""")
        if code == 200 and not test:
            output_buffer = ""
            object_index = 1
            image_index = 1
            # initializing bskyqueue
            bsky.check_queue_not_empty()
            # processing lines from sinkfile
            with open(self.sinkfile) as f:
                for line in f.readlines():
                    if any(a in line for a in ["BSkyFormatInternalSyncFileMarker", "BSkyGraphicsFormatInternalSyncFileMarker", "BSkyDataGridRefresh"]):
                        if output_buffer.strip():
                            for msg in self.process_message(output_buffer.strip(), '', cmd=cmd, eval=False, limit=limit, updateDataSet=updateDataSet, datasetName=datasetName, parent_id=parent_id, output_id=output_id, code=code):
                                msg["type"] = "markdown"
                                yield msg
                        output_buffer = ""
                        for msg in bsky.bskyformat_parser(cmd=cmd, limit=limit, updateDataSet=updateDataSet, datasetName=datasetName, parent_id=parent_id, output_id=output_id, code=code, filename=filename, object_index=object_index):
                            if msg["type"] == images:
                                return_type = msg["type"]
                                image_index += 1
                            yield msg
                        object_index += 1
                    else:
                        if line.strip():
                            output_buffer += f"{line.strip()}\n"
            if output_buffer.strip():
                for msg in self.process_message(output_buffer.strip(), '', cmd=cmd, eval=False, 
                                                limit=limit, updateDataSet=updateDataSet, 
                                                datasetName=datasetName, parent_id=parent_id, 
                                                output_id=output_id, code=code):
                    msg["type"] = "markdown"
                    yield msg
            # Trying to process output if no BSKy format was in place
            if object_index == 1:
                for msg in self.process_message(message, filename, cmd=cmd, eval=eval, 
                                                limit=limit, updateDataSet=updateDataSet, 
                                                datasetName=datasetName, parent_id=parent_id, 
                                                output_id=output_id, code=code):
                    return_type = msg["type"]
                    if msg["message"]:
                        yield msg
            # Process remaining bskyformats
            for msg in bsky.bskyformat_parser(cmd=cmd, limit=limit, updateDataSet=updateDataSet, datasetName=datasetName, parent_id=parent_id, output_id=output_id, code=code, filename=filename, object_index=object_index, till_the_end=True):
                if msg["type"] == images:
                    return_type = msg["type"]
                    image_index += 1
                yield msg
            # Adding remaining images
            for msg in bsky.process_images(cmd=cmd, datasetName=datasetName, parent_id=parent_id, 
                                            output_id=output_id, code=code, filename=filename, 
                                            image_index=image_index):
                if "type" in msg:
                    return_type = msg["type"]
                else:
                    return_type = "Close device"
                yield msg
            yield {"message": f"Output buffer: {output_buffer}", "type": "log"}
        # Weird workaround #2 to make ggplot work
        if return_type and return_type == images:
            r("""dev.set(2)
dev.off()""")


    def process_message(self, message, filename, cmd='', eval=True, limit=20, updateDataSet=False, 
                        datasetName=None, parent_id=None, output_id=None, code=200):
        if str(message) and message != ri.NULL:
            if not str2bool(eval):
                message = str(message)
                return_type = 'console'
            elif message and str(message):
                message, return_type = convert_to_data(message, limit)
            else:
                return_type = "log"
                message = str(message)
            yield {
                "message": message,
                "caption": "",
                "type": return_type,
                "code": code,
                "updateDataSet": updateDataSet,
                "name": datasetName,
                "cmd": cmd,
                "eval": eval,
                "parent_id": parent_id,
                "output_id": output_id
            }
