from os import path
from py2r import rDriver
from py2r.rUtils import execute_r
from py2r.blueskyparser import blueSkyParser
# import rDriver


def __init__r():
    r=rDriver.RDriver()
    r.initiate_libs()
    return r

def test_convert_matrix_3x4():
    cmd = """mydf <- data.frame(A=c(1,2,3,4), B=c('M', 'F', 'F', 'M'), D=c(1.1, 2.2, 3.3, 4.4))
BSkyFormat(mydf)
"""
    r = __init__r()
    message, return_type = execute_r(cmd, eval=False)
    r.check_queue_not_empty()
    for msg in r.bskyformat_parser():
        assert isinstance(msg, dict)

def test_convert_matrix_3x3():
    cmd = """BSkySetKableAndRmarkdownFormatting(BSkyKableFormatting = TRUE, BSkyRmarkdownFormatting = FALSE)
mydf <- data.frame(A=c(1,2,3), B=c('M', 'F', 'F'), D=c(1.1, 2.2, 3.3))
BSkyFormat(mydf)
"""
    r = __init__r()
    message, return_type = execute_r(cmd, eval=False)
    bsky = blueSkyParser()
    bsky.check_queue_not_empty()
    for msg in bsky.bskyformat_parser():
        assert isinstance(msg, dict)

def test_convert_matrix_4x3():
    cmd = """mydf <- data.frame(A=c(1,2,3), B=c('M', 'F', 'F'), C=c(11, 21, 31), D=c(1.1, 2.2, 3.3))
BSkyFormat(mydf)
"""
    r = __init__r()
    message, return_type = r._execute_r(cmd, eval=False)
    r.check_queue_not_empty()
    for msg in r.bskyformat_parser():
        assert isinstance(msg, dict)

def test_queue_is_empty():
    r = __init__r()
    assert r.check_queue_not_empty() == True

def test_queue_is_not_empty():
    r = __init__r()
    cmd = """mydf <- data.frame(A=c(1,2,3,4), B=c('M', 'F', 'F', 'M'), D=c(1.1, 2.2, 3.3, 4.4))
BSkyFormat(mydf)
"""
    message = r._execute_r(cmd, eval=False)
    assert r.check_queue_not_empty() == False

def test_named_matrix():
    r = __init__r()
    cmd = """mydf <- data.frame(A=c(1,2,3,4), B=c('M', 'F', 'F', 'M'), D=c(1.1, 2.2, 3.3, 4.4))
BSkyFormat(mydf, singleTableOutputHeader="some name")
"""
    message = r._execute_r(cmd)
    r.check_queue_not_empty()
    resp = list(r.bskyformat_parser())
    assert resp[0]["caption"] == "some name"

def test_csv_with_empty_col_name():
    p = path.abspath("testData\\A_empty.csv")
    r = __init__r()
    ds = []
    for msg in r.open(p.replace("\\", "/"), "test_ds"):
        ds.append(msg)
    assert len(ds[1]["cols"]) == 6 

def test_csv_with_empty_data():
    p = path.abspath("testData\\Titanic_empty_data.csv")
    r = __init__r()
    ds = []
    for msg in r.open(p.replace("\\", "/"), "test_ds"):
        ds.append(msg)
    assert len(ds[1]["cols"]) == 6 
    assert len(ds[1]["df"][0]) == 6 

def test_csv_with_na_and_empty_data():
    p = path.abspath("testData\\TitanicBlankAndNA.csv")
    r = __init__r()
    ds = []
    for msg in r.open(p.replace("\\", "/"), "test_ds"):
        print(f'this is msg: {msg}')
        ds.append(msg)
    assert len(ds[1]["cols"]) == 6 
    assert len(ds[1]["df"][0]) == 6 

def test_crosstab_multiway():
    p = path.abspath("testData\\Titanic.RData")
    r = __init__r()
    ds = []
    for msg in r.open(p.replace("\\", "/"), "Titanic_RData"):
        print(f'this is msg: {msg}')
    cmd = """BSky_Multiway_Cross_Tab = BSkyCrossTable(
x=c('Sex'),
y=c('Survived'), 
layers=c('Age'), 
weight= c('Freq'), 
datasetname='Titanic_RData', 
chisq = FALSE,mcnemar =FALSE,fisher=FALSE,prop.r=FALSE,prop.c=FALSE,resid=FALSE,sresid=FALSE,expected=FALSE,asresid=FALSE)
BSkyFormat(BSky_Multiway_Cross_Tab)"""
    message, return_type = r._execute_r(cmd, eval=False)
    r.check_queue_not_empty()
    for msg in r.bskyformat_parser():
        assert isinstance(msg, dict)


if __name__ == "__main__":
    test_convert_matrix_3x3()
    # test_crosstab_multiway()
    # test_named_matrix()
    # test_convert_matrix_3x4()
    # test_convert_matrix_4x4()
    # test_convert_matrix_4x3()
    # test_queue_is_empty()
    # test_queue_is_not_empty()