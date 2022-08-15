from os import path
import rpy2.robjects.vectors as vectors
from rpy2 import robjects
from rpy2.rinterface import NULL as NULL

from py2r.data_converter import convert_to_data, convert_matrix, convert_listvector, convert_html
from py2r.rDataset import load as loadDS
from py2r.config import images, empty_image_size


class blueSkyParser(object):
    def __init__(self):
        self.r = robjects.r
        self.type_mapping = {
            vectors.Matrix: convert_matrix,
            vectors.ListVector: convert_listvector,
            vectors.StrVector: convert_html
        }
    
    def check_queue_not_empty(self):
        res, _ = convert_to_data(self.r("""
        BSkyQueue = BSkyGetHoldFormatObjList()
is.null(BSkyQueue)
        """), 10)
        return res

    def bskyformat_parser(self, cmd='', limit=20, updateDataSet=False,
                          datasetName=None, parent_id=None, output_id=None,
                          code=200, filename='', object_index=None,
                          image_index=None, till_the_end=False):
        
        queue_length = convert_to_data(self.r("length(BSkyQueue)"))[0]
        image_index = 0 if not image_index else image_index
        start_index = object_index if object_index else 1
        end_index = object_index + 1 if object_index and not till_the_end else queue_length + 1
        for resp_index in range(start_index, end_index):
            r_type = self.r(f'BSkyQueue[[{resp_index}]]')[0][0]
            if isinstance(r_type, vectors.StrVector) and r_type[0] == 'BSkyFormat' and not till_the_end:
                r_response = self.r(f'BSkyQueue[[{resp_index}]]')[0][1]
                for message in self.process_BSKy_format(r_response, cmd=cmd, limit=limit,
                                                        updateDataSet=updateDataSet,
                                                        datasetName=datasetName, parent_id=parent_id,
                                                        output_id=output_id, code=code):
                    yield message
            elif r_type == 'BSkyGraphicsFormat' and not till_the_end:
                for msg in self.process_images(cmd=cmd, datasetName=datasetName, parent_id=parent_id,
                                               output_id=output_id, code=code, filename=filename,
                                               image_index=image_index, single=True):
                    image_index = msg['image_index']
                    yield msg
            elif r_type == 'BSkyDataGridRefresh':
                r_response = self.r(f'BSkyQueue[[{resp_index}]]')[1]
                for message in loadDS(r_response[0]):
                    yield message

    def process_images(self, cmd='', datasetName=None, parent_id=None,
                       output_id=None, code=200, filename='', image_index=1,
                       single=False):
        image_missing = False
        while True:
            image_path = filename.replace("%03d", f'{image_index:03d}')
            if path.exists(image_path) and path.getsize(image_path) > empty_image_size:
                yield {
                    "message": filename.replace("%03d", f'{image_index:03d}'),
                    "caption": "",
                    "type": images,
                    "code": code,
                    "updateDataSet": False,
                    "name": datasetName,
                    "cmd": cmd,
                    "eval": True,
                    "parent_id": parent_id,
                    "output_id": output_id,
                    "image_index": image_index
                }
                image_index += 1
                if single:
                    break
            else:
                if image_missing:
                    break
                else:
                    image_missing = True
                    image_index += 1
                    image_path = filename.replace("%03d", f'{image_index:03d}')
                    if path.exists(image_path) and path.getsize(image_path) > empty_image_size:
                        yield {
                            "message": filename.replace("%03d", f'{image_index:03d}'),
                            "caption": "",
                            "type": images,
                            "code": code,
                            "updateDataSet": False,
                            "name": datasetName,
                            "cmd": cmd,
                            "eval": True,
                            "parent_id": parent_id,
                            "output_id": output_id,
                            "image_index": image_index
                        }
                        image_index += 1
                        if single:
                            break

    def process_BSKy_format(self, data, cmd='', limit=20, updateDataSet=False,
                            datasetName=None, parent_id=None, output_id=None,
                            code=200):
        rett_type = "console"
        caption = ""
        for index in range(int(data[6][0])):
            if isinstance(data[7][index], vectors.ListVector) and data[7][index][0][0] == "ewtable":
                message = str(data[7][index])
                rett_type = "log"
            elif type(data[7][index]) in self.type_mapping:
                message, rett_type = self.type_mapping[type(data[7][index])](data[7][index])
            else:
                message = str(data[7][index])
                rett_type = "log"
            if rett_type != "log":
                yield {
                    "message": message,
                    "caption": caption,
                    "type": rett_type,
                    "code": code,
                    "updateDataSet": updateDataSet,
                    "name": datasetName,
                    "cmd": cmd,
                    "eval": True,
                    "parent_id": parent_id,
                    "output_id": output_id
                }
            else:
                yield {
                    "message": message,
                    "type": rett_type
                }
    