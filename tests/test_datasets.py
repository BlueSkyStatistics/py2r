from os import path
from json import loads
import rDriver
from blueskyparser import blueSkyParser
from rUtils import execute_r
bsky = blueSkyParser()


def __init__r():
    r=rDriver.RDriver()
    r.initiate_libs()
    return r

def test_slid_dataset():
    r = __init__r()
    p = path.abspath("testData\\SLID (Study of labor and income dynamics).RData")
    ds = []
    for msg in r.open(p.replace("\\", "/"), "test_ds"):
        print(f'this is msg: {msg}')
        ds.append(msg)
    assert len(ds[1]["cols"]) == 5
    for msg in r.refresh("test_ds", False):
        assert isinstance(msg["message"]["df"], list)

def test_xlsx_worksheets():
    r = __init__r()
    p = path.abspath("testData\\AA.xlsx")
    ds = []
    for msg in r.open(p.replace("\\", "/"), "test_ds"):
        print(f'this is msg: {msg}')
        ds.append(msg)
    assert len(ds[1]["cols"]) == 5
    for msg in r.refresh("test_ds", False):
        assert isinstance(msg["message"]["df"], list)


def test_results_has_levels():
    r = __init__r()
    p = path.abspath("testData\\carsales nas removed.RData")
    ds = []
    for msg in r.open(p.replace("\\", "/"), "test_ds"):
        print(f'this is msg: {msg}')
        ds.append(msg)
    cmd = """require(tidyverse)
test_ds %>% select(model) %>% map(levels)"""
    message, return_type = r._execute_r(cmd, eval=True)
    print(message)


def test_BSkyLoadRefreshDataframe():
    r = __init__r()
    cmd = """df1 <- data.frame(A=c(3,6,4), B=c("Aa","Bb","Cc"))
BSkyLoadRefresh('df1')
    """
    message, return_type = execute_r(cmd, eval=True)
    print(message)
    bsky.check_queue_not_empty()
    for message in bsky.bskyformat_parser():
        print(message)
    


def test_bSkyGrafics():
    r = __init__r()
    p = path.abspath("testData\\caranalysis.RData")
    r.open(p.replace("\\", "/"), "test_ds")
    for msg in r.open(p.replace("\\", "/"), "test_ds"):
        print(msg)
    cmd = """local({
LinearRegModel1= BSkyRegression(depVars = 'mpg', indepVars = c('engine','horse','weight','accel'), dataset="test_ds")
#Plots residuals vs. fitted,normal Q-Q,theoretical quantiles,residuals vs. leverage

if(TRUE)
{
### Display 2 of the 4 graphs that plot generates
BSkyGraphicsFormat(noOfGraphics=2)
### Plot generates 4 graphs
plot(LinearRegModel1)
}

df <- data.frame(A=c(1,2,3), B=c(4,5,6))
BSkyFormat(df)
### Display the 3rd graph
BSkyGraphicsFormat(noOfGraphics=1)
df <- data.frame(A=c(10,12,30), B=c(44,55,66))
BSkyFormat(df)
### Display the 4th or all the remaining graphs
})"""
    message, return_type = r.run(cmd, test=True)
    print(message)
    bsky.check_queue_not_empty()
    resp = list(r.bskyformat_parser())

if __name__ == "__main__":
    test_BSkyLoadRefreshDataframe()