from parallelprinterdriver import printbytesdmaasync
import physicalprinter

class ParallelPort(physicalprinter.Port):
    async def writeport(self, line):
        await printbytesdmaasync(line)

parallelport = ParallelPort()

def setactive():
    physicalprinter.resetprotocol()
    physicalprinter.setport(parallelport)
    physicalprinter.setenabled(True)
