from os import path
from json import loads
import rDriver


def __init__r():
    r=rDriver.RDriver()
    r.initiate_libs()
    return r


def test_openempty_dataset():
    r = __init__r()
    p = path.abspath("D:/UniqueID.csv")
    ds = []
    for msg in r.openblankds('Dataset1'):
        print(f'this is msg: {msg}')
        ds.append(msg)
    assert len(ds[1]["cols"]) == 6
    rowc = ds[1]["rowcount"]
    for msg in r.refresh("Dataset1", True,0,rowc):
        assert isinstance(msg["message"]["df"], list)

# open a dataset and modify one value of one column
# Whoever is testing must set the correct path to file
# accordingly set following:
#   dataset name, column name to be modified, 
#   row index in that column , the new value and the hard 
#   coded 3 which is column count in UniqueID.csv".
def test_opendynamic_dataset():
    r = __init__r()
    p = path.abspath("D:/UniqueID.csv")
    ds = []
    for msg in r.open(p.replace("\\", "/"), "UniqueID_csv"):
        print(f'this is msg: {msg}')
        ds.append(msg)
    r._execute_r("BSkyEditDatagrid(colname='id', colceldata='567', rowindex=1, dataSetNameOrIndex='UniqueID_csv',rdateformat='Not Applicable')")    
    assert len(ds[1]["cols"]) == 3
    rowc = ds[1]["rowcount"]
    for msg in r.refresh("UniqueID_csv", True,0,rowc):
        assert isinstance(msg["message"]["df"], list)

def test_opendynamic_dataset2():
    r = __init__r()
    p = path.abspath("D:/cols270.RData")
    ds = []
    for msg in r.open(p.replace("\\", "/"), "cols270_RData"):#manycols
        print(f'this is msg: {msg}')
        ds.append(msg)
    #r._execute_r("BSkyEditDatagrid(colname='id', colceldata='567', rowindex=1, dataSetNameOrIndex='UniqueID_csv',rdateformat='Not Applicable')")    
    assert len(ds[1]["cols"]) == 270
    rowc = ds[1]["rowcount"]
    for msg in r.refresh("UniqueID_csv", True,0,rowc):
        assert isinstance(msg["message"]["df"], list)

if __name__ == "__main__":
    test_openempty_dataset()