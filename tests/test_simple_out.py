from os import path
from json import loads
import rDriver


def __init__r():
    r=rDriver.RDriver()
    r.initiate_libs()
    return r

def test_simple_out():
    r = __init__r()
    for each in r.run("""df1 <- data.frame(A=c(3,6,4), B=c("Aa","Bb","Cc"))
BSkyFormat(df1)""", test=True):
        print(each)

if __name__ == "__main__":
    test_simple_out()
