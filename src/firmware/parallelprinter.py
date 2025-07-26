from parallelprinterdriver import printbytesdmaasync
import physicalprinter

class ParallelPort(physicalprinter.Port):
    async def writeport(self, line):
        await printbytesdmaasync(line)

parallelport = ParallelPort()

def setdefaultprotocol():
    physicalprinter.setprotocolescp()

def setactive():
    setdefaultprotocol()
    physicalprinter.setport(parallelport)
    physicalprinter.setenabled(True)
