from parallelprinterdriver import printbytesdmaasync
import physicalprinter

def setactive():
    physicalprinter.write = printbytesdmaasync
    physicalprinter.setenabled(True)
