from json import loads
from rpy2 import robjects

from py2r.rUtils import execute_r

def openblankdataset(datasetName):
    open_cmd = f"BSkyOpenNewDataset(datasetName='{datasetName}', noOfRows=80,noOfCols=15)" 
    yield {"message": open_cmd, "name":datasetName, "type": "log"}
    robjects.r(open_cmd)
    #print("R cmd executed...")
    for message in getrowcountcolprops(datasetName):
        yield message["message"]

def open(file_path, filetype, wsName, replace_ds, csvHeader, char_to_factor, basket_data, csv_sep, delim, datasetName):
    if filetype == 'SAV':
        filetype = 'SPSS'
    open_cmd = f"BSkyloadDataset('{file_path}', " \
                    f"'{filetype}', " \
                    f"worksheetName={wsName}, " \
                    f"replace_ds={replace_ds}, " \
                    f"load.missing=FALSE, " \
                    f"csvHeader={csvHeader}, " \
                    f"character.to.factor={char_to_factor}, " \
                    f"isBasketData={basket_data}, " \
                    f"trimSPSStrailing=FALSE, " \
                    f"sepChar='{csv_sep}', " \
                    f"deciChar='{delim}', " \
                    f"datasetName='{datasetName}')"
    yield {"message": open_cmd, "name":datasetName, "type": "syntax"}
    robjects.r(open_cmd)
    #print("R cmd executed...")
    for message in getrowcountcolprops(datasetName):
        yield message["message"]


def close(datasetName):
    pass


def refresh(datasetName, reloadCols=True, fromrowidx=1, torowidx=20):
    res = {}
    for message in getrowcountcolprops(datasetName, reloadCols=reloadCols):
        res = message
    if(res['message']['rowcount'] < torowidx):
        torowidx=res['message']['rowcount']
    df, _ = execute_r(f'jsonlite::toJSON({datasetName}[{fromrowidx}:{torowidx},], na=NULL)')
    df = loads(df[0])
    try:
        df_list = [list(df[0].keys())]
        for row in df:
            df_list.append(list(row.values()))
            #cols no needed in following and reloadCols should be False
    except AttributeError:
        df_list = []
        for row in df:
            df_list.append([row]) 
    res["message"]["df"] = df_list
    res["message"]["fromidx"] = fromrowidx
    res["message"]["toidx"] = torowidx
    yield {
        "message": res,
        "refresh": True,
        "name": datasetName,
        "fromidx":fromrowidx,
        "toidx":torowidx
    }


def load(datasetName):
    yield {"message": f"Loading Dataset {datasetName}", "name": datasetName, "type": "log"}
    for message in getrowcountcolprops(datasetName):
        yield message["message"]

def getrowcountcolprops(datasetName, reloadCols=True):
    rc, _ = execute_r(f'jsonlite::toJSON(nrow(.GlobalEnv${datasetName}))')
    rc = loads(rc[0])
    cc, _ = execute_r(f'jsonlite::toJSON(ncol(.GlobalEnv${datasetName}))')
    cc = loads(cc[0])
    res = {"name": datasetName, "cols": [], "rowcount": rc[0], "colcount":cc[0], "type":"rccolprop"} #rccolprop = rowcount-colprop
    if reloadCols:
        for index in range(1, cc[0]+1):
            col_details_cmd = f"data=UAgetColProperties(dataSetNameOrIndex='.GlobalEnv${datasetName}', colNameOrIndex={index}, " \
                            f"asClass=FALSE, isDSValidated=TRUE);"             
            execute_r(col_details_cmd)
            col, _ = execute_r("jsonlite::toJSON(data, na = NULL)")
            res["cols"].append(loads(col[0]))
    yield {
        "message": res,
        "refresh": True,
        "name": datasetName
    }