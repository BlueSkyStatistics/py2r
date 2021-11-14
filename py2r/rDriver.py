import re
import webbrowser
from os import path, environ
from time import sleep, time
from json import dumps
from tempfile import gettempdir
from traceback import format_exc
from sys import platform


import rpy2.rinterface as ri
try:
    from rpy2.rinterface_lib.embedded import RRuntimeError
except:
    from rpy2.rinterface import RRuntimeError
import rpy2.robjects as robjects
import rpy2.robjects.vectors as vectors
from rpy2.robjects.packages import importr

from py2r.data_converter import *
from py2r.config import *
from py2r.blueskyparser import blueSkyParser
from py2r.rUtils import execute_r, randomString, str2bool
import py2r.rDataset as ds

r = robjects.r
bsky = blueSkyParser()

class RDriver:
    if 'win' not in platform or 'darwin' in platform:
        tmpdir = gettempdir()
    else:
        tmpdir = environ.get('TMP', environ.get('TEMP', gettempdir()))
    tmpdir = tmpdir.replace("\\", "/")
    sinkfile = path.join(tmpdir, 'sink.txt')
    sinkhtml = path.join(tmpdir, 'help.html')
    sinkfile = sinkfile.replace("\\", "/")
    sinkhtml = sinkhtml.replace("\\", "/")

    def initiate_libs(self):
        # opening sink file
        r(f"""fp <- file("{self.sinkfile}", open = "wt")
options("warn" = 1)
sink(fp)
sink(fp, type = "message")""")
        r('''require('gdata')
require('stringr')
require("openxlsx")
require("haven")
require("readr")
require("readxl")
require("data.table")
require("foreign")
require("BlueSky")
require("kableExtra")
require("tidyverse")
require('formatR')
''')
        r(f'''BSkySetGraphicsDirPath("{self.tmpdir}")
BSkySetRCommandDisplaySetting(echo = TRUE, echoInline = TRUE)
BSkySetKableAndRmarkdownFormatting(BSkyKableFormatting = TRUE, BSkyRmarkdownFormatting = FALSE)
BSkySetHtmlStylingSetting ()
BSkySetHtmlStylingSetting (tableTheme = "kable_styling", tableHeaderBackgroundColor = "", tableOuterBorder = FALSE, columHeaderScrollFixed = TRUE)
BSkyGetPvalueDisplaySetting()
''')
# closing sink file
        r("""sink(type = "message")
sink()
flush(fp)
close(fp)""")
        yield {"message": "started", "type": "rinfo"}

    @staticmethod
    def wrap_with_space(match):
        return f"print({match.group(0).strip()})\n"

    def wrapRcommand(self, cmd, dataset_name):
        if "%ds" in cmd:
            cmd = cmd.replace("%ds", dataset_name)
        # cmd_arr = cmd.split("\n")
        # cmd = ''
        # for each in cmd_arr:
        #     if any(each.strip().endswith(a) for a in [",", "+", "%>%"]):
        #         cmd += f" {each.strip()}"
        #     else: 
        #         if cmd.endswith("\n"):
        #             cmd += f"{each.strip()}\n"
        #         else:
        #             cmd += f" {each.strip()}\n"
        stringif = cmd.replace('"','\\"')
        return cmd, f'"{stringif}"'

    def openblankds(self, datasetName='Dataset1'):
        for message in ds.openblankdataset(datasetName):
            yield message
    
    @staticmethod
    def clean(output):
        out = ''
        for line in output.split("\n"):
            if not any(line.startswith(a) for a in [">", "+"]):
                out += f'{line.rstrip()}\n'
        return out

    def open(self, file_path=None, datasetName=None, wsName='NULL',
             replace_ds='TRUE', csvHeader='TRUE', char_to_factor='TRUE',
             basket_data='FALSE', csv_sep=',', delim='.'):
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
            for message in ds.open(file_path, filetype, wsName, 
                                    replace_ds, csvHeader, 
                                    char_to_factor, basket_data, 
                                    csv_sep, delim, datasetName):
                yield message


    def refresh(self, datasetName, reloadCols=True, fromrowidx=1, torowidx=20):
        try:
            for message in ds.refresh(datasetName, reloadCols, fromrowidx, torowidx):
                yield message
        except:
            yield {"message": format_exc(), "type": "log"}

    @staticmethod
    def close_devices():
        # Weird workaround to make ggplot work
        r("""dev.set(1)
dev.off()
""")
        r("""dev.set(2)
dev.off()""")

    def rhelp(self, cmd):
        res = r(f"""fp = file("{self.sinkhtml}", open = "wt")
file <- {cmd}
pkgname <- basename(dirname(dirname(file)))
temp <- tools::Rd2HTML(utils:::.getHelpFile(file), out=fp, package = pkgname)""")
        webbrowser.open(f"file://{self.sinkhtml}", new=2)
        r("""close(fp)""")
        return "Done"

    def run(self, cmd, eval=True, limit=20, updateDataSet=False, datasetName=None, 
            parent_id=None, output_id=None, test=False, splitIgnore='FALSE', 
            echo='TRUE', echoInline='TRUE', imagesType=images, 
            plotHeight=image_height, plotWidth=image_wigth, 
            log_command=False, numExpr=-1, startPosition=-1, endPosition=-1, jumpCursor=False):
        error_message = None
        code = 200
        return_type = None
        sanitized_cmd, stringified = self.wrapRcommand(cmd, datasetName)
        filename = "/".join([self.tmpdir, f"{randomString()}%03d.{images}"])
        filename = filename.replace("\\", "/")
        if log_command:
            yield {"message": stringified, "type": "log"}
            if startPosition > 0 or endPosition > 0:
                yield {"message": f"Shrinked command: {stringified[startPosition:endPosition]}", "type": "log"}
        if imagesType == 'svg' and plotHeight > 100 and plotWidth > 100:
            plotHeight = plotHeight / 100
            plotWidth = plotWidth / 100
        plotWidth = plotWidth if plotWidth > 1 else 1
        plotHeight = plotHeight if plotHeight > 1 else 1
        try:
            # opening graphics device
            r(f"""{imagesType}(filename='{filename}', width={plotWidth}, height={plotHeight})""")
            # opening sink file
            r(f"""fp <- file("{self.sinkfile}", open = "wt")
options("warn" = 1)
sink(fp)
sink(fp, type = "message")""")
            # Executing R
            res = r(f"""
dev.set(2)
BSkyEvalRcommand(RcommandString = {stringified}, currentDatasetName = "{datasetName}", ignoreSplitOn = {splitIgnore}, echo = {echo}, echoInline = {echoInline}, numExprParse = {numExpr}, selectionStartpos = {startPosition}, selectionEndpos = {endPosition})
"""
)
            # closing sink file
            r("""sink(type = "message")
sink()
flush(fp)
close(fp)""")
            # turning off graphical device
            if jumpCursor:
                try:
                    # yield {"message": str(res), "type":"log"}
                    if (res[0][0] != -1):
                        yield {"position": int(res[5][0]), "type":"jumpCursor"}
                except:
                    yield {"message": f"Jump cursor failed due to {format(format_exc())}", "type":"log"}
        except RRuntimeError as err:
            code = 400
            return_type = "exception"
            message = self.clean(f"SERVER STATE EXCEPTION: \n {format(format_exc())}")
            yield {"message": self.clean(message.split('.RRuntimeError:')[1].strip()), "type": "log"}
            error_message = {"message": str(err),
                "error": message.split('.RRuntimeError:')[1].strip(),
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
        if code != 500 and not test:
            code = 200
            output_buffer = ""
            object_index = 1
            image_index = 1
            # initializing bskyqueue
            bsky.check_queue_not_empty()
            # processing lines from sinkfile
            with open(self.sinkfile) as f:
                for line in f.readlines():
                    if any(a in line for a in ["BSkyFormatInternalSyncFileMarker", 
                                               "BSkyGraphicsFormatInternalSyncFileMarker", 
                                               "BSkyDataGridRefresh"]):
                        if output_buffer.strip():
                            for msg in self.process_message(self.clean(output_buffer).strip(), 
                                                            '', cmd=cmd, eval=False, limit=limit, 
                                                            updateDataSet=updateDataSet, datasetName=datasetName, 
                                                            parent_id=parent_id, output_id=output_id, code=code):
                                msg["type"] = "markdown"
                                yield msg
                        output_buffer = ""
                        for msg in bsky.bskyformat_parser(cmd=cmd, limit=limit, 
                                                          updateDataSet=updateDataSet, datasetName=datasetName, 
                                                          parent_id=parent_id, output_id=output_id, code=code, 
                                                          filename=filename, object_index=object_index, image_index=image_index):
                            if msg["type"] == images:
                                return_type = msg["type"]
                                image_index = msg['image_index'] + 1
                                del msg['image_index']
                            yield msg
                        object_index += 1
                    else:
                        if line.strip():
                            output_buffer += f"{line.rstrip()}\n"
            # Trying to process output if no BSKy format was in place
            # if object_index == 1:
            #     for msg in self.process_message(message, filename, cmd=cmd, eval=eval, 
            #                                     limit=limit, updateDataSet=updateDataSet, 
            #                                     datasetName=datasetName, parent_id=parent_id, 
            #                                     output_id=output_id, code=code):
            #         return_type = msg["type"]
            #         if msg["message"]:
            #             yield msg
            # Process remaining bskyformats
            for msg in bsky.bskyformat_parser(cmd=cmd, limit=limit, updateDataSet=updateDataSet, 
                                              datasetName=datasetName, parent_id=parent_id, output_id=output_id, 
                                              code=code, filename=filename, object_index=object_index, 
                                              image_index=image_index, till_the_end=True):
                if msg["type"] == images:
                    return_type = msg["type"]
                    image_index = msg['image_index'] + 1
                    del msg['image_index']
                yield msg
            # Adding remaining images
            # for msg in bsky.process_images(cmd=cmd, datasetName=datasetName, parent_id=parent_id, 
            #                                output_id=output_id, code=code, filename=filename, 
            #                                image_index=image_index):
            #     if "type" in msg:
            #         return_type = msg["type"]
            #     else:
            #         return_type = "Close device"
            #     yield msg
            # processing remaining console outputs
            if output_buffer.strip():
                for msg in self.process_message(self.clean(output_buffer).strip(), '', 
                                                cmd=cmd, eval=False, 
                                                limit=limit, updateDataSet=updateDataSet, 
                                                datasetName=datasetName, parent_id=parent_id, 
                                                output_id=output_id, code=code, 
                                                error_message=error_message):
                    msg["type"] = "markdown"
                    yield msg
            if "Error:" in output_buffer:
                yield {"message": f"Output buffer: {output_buffer}", "type": "log"}
        if error_message:
            yield error_message
        yield {
            "message": "",
            "caption": "",
            "type": "processing_done",
            "code": code,
            "updateDataSet": updateDataSet,
            "name": datasetName,
            "cmd": cmd,
            "eval": True,
            "parent_id": parent_id,
            "output_id": output_id
        }
        # Weird workaround #2 to make ggplot work
        if return_type and return_type == images:
            r("""dev.set(2)
dev.off()""")


    def process_message(self, message, filename, cmd='', eval=True, limit=20, updateDataSet=False, 
                        datasetName=None, parent_id=None, output_id=None, code=200, error_message=None):
        if str(message) and message != ri.NULL:
            if not str2bool(eval):
                message = str(message)
                if 'BSkyHelpCommandMarker' in message:
                    arr_message = message.split('\n')
                    message = ''
                    for line in arr_message:
                        if 'BSkyHelpCommandMarker' in line:
                            f_path = line.replace('BSkyHelpCommandMarker', '').replace('\\', '/').strip()
                            if path.exists(f_path):
                                webbrowser.open(f"file://{f_path}", new=2)
                        else:
                            message += f'{line}\n'
                if error_message:
                    message = message.replace(error_message['error'], '')
                return_type = 'console'
            elif message and str(message):
                message, return_type = convert_to_data(message, limit)
            else:
                return_type = "log"
                message = str(message)
            if message:
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
