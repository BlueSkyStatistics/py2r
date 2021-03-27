from os import path
from json import loads
from py2r import rDriver


def __init__r():
    r=rDriver.RDriver()
    r.initiate_libs()
    return r

def test_simple_out():
    r = __init__r()
    for each in r.run("""df1 <- data.frame(A=c(3,6,4), B=c("Aa","Bb","Cc"))
BSkyFormat(df1)""", test=True):
        print(each)

def test_help():
    r = __init__r()
    for each in r.rhelp("""help(geom_bar, package=ggplot2)"""):
        print(each)
    from time import sleep
    sleep(120)

def test_wrapped_tibble():
    r = __init__r()
    for each in r.run("""library(ggplot2)
library(dplyr)

smaller <- diamonds %>% 
  filter(carat <= 2.5)
smaller"""):
        print(each)

def test_list_output_formatting():
    r = __init__r()
    for each in r.run("""require(neuralnet);
require(NeuralNetTools);
#Setting a seed
set.seed(12345);
BSkyloadDataset('D:/Development/BlueSkyJS/testData/Boston scaled.RData', 'RDATA', worksheetName=NULL, replace_ds=TRUE, load.missing=FALSE, csvHeader=TRUE, character.to.factor=TRUE, isBasketData=FALSE, trimSPSStrailing=FALSE, sepChar=',', deciChar='.', datasetName='Boston_scaled')
#Creating the model
aaaa<-neuralnet::neuralnet( formula=medv ~ crim+zn+indus+chas+nox+rm+age+dis+rad+tax+ptratio+black+lstat, data = Boston_scaled, hidden = 5,threshold =0.01,  stepmax = 100000, rep =1, algorithm= "rprop+",learningrate.factor = list(minus = 0.5, plus = 1.2),lifesign = 'none', lifesign.step = 1000, err.fct = 'sse', act.fct = 'logistic', linear.output = TRUE,  likelihood = FALSE)
if (!is.null(aaaa))
{
NeuralNetTools::neuralweights(aaaa)
}"""):
        print(each)

if __name__ == "__main__":
    test_list_output_formatting()


# import rpy2.rinterface as ri
# import rpy2.robjects as robjects

# r = robjects.r

# r("""fp <- file("tmp", open = "wt")
# options("warn" = 1)
# sink(fp)
# sink(fp, type = "message")""")

# m = r("""help(geom_bar, package=ggplot2)""")

# r("""sink(type = "message")
# sink()
# flush(fp)
# close(fp)""")