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
    for each in r.run("""## [Bar Chart With Counts]
require(ggplot2);
require(ggthemes);
require(stringr);
plot <- ggplot(data=cholStudy, aes(x=gender,y=cho1)) +
	geom_bar(position="stack",alpha=0.5,stat="identity") +
	labs(x="gender",y="cho1",title= "Bar chart for X axis: gender,Y axis: cho1 ") +
	xlab("gender") +
	ylab("cho1") + 	theme_grey() + 
	theme(text=element_text(family="sans",face="plain",color="#000000",size=12,hjust=0.5,vjust=0.5))
print(plot)"""):
        print(each)

if __name__ == "__main__":
    test_wrapped_tibble()


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