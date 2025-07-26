# pyright: reportUndefinedVariable=false

from micropython import const
from asyncio import Lock
from phew import logging
from packbits import UnpackBitsFile
import time

# NOTE: only supports ESC/P and ESC/POS

# see https://forum.micropython.org/viewtopic.php?f=2&t=2480&start=10
# @micropython.viper
# def fillarray(x:ptr8, n:int, q:int):
#     for i in range(n):
#         x[i] = q

@micropython.asm_thumb
def fillarray(r0, r1, r2):
    label(loop)
    strb(r2, [r0, 0])
    add(r0, 1)
    sub(r1, 1)
    bne(loop)

enabled = False
linefeed = True
formfeed = False
leftmargin = 1
density = 0         # 0=60dpi, 1=120dpi
dotdensity = 0      # esp/p dot density (see esp/p table in docs)
xscale = 1

linebytes = const(32)

printerlock = Lock()

class Port:
    async def openport(self):
        pass

    async def writeport(self, line):
        pass

    async def closeport(self):
        pass

nullport = Port()
activeport = nullport

def setport(port):
    global activeport

    activeport = port

def setenabled(state):
    global enabled

    enabled = state
    if not enabled:
        setport(nullport)

def setlinefeed(state):
    global linefeed

    linefeed = state

def setformfeed(state):
    global formfeed

    formfeed = state

def setleftmargin(value):
    global leftmargin

    leftmargin = 1 if value<1 else value

def setdensity(value):
    global density
    global dotdensity
    global xscale

    density = 0 if value<0 or value>1 else value
    dotdensity = 0 if density == 0 else 1
    xscale = 1 if density == 0 else 2

class Protocol:
    async def begin(self):
        pass

    async def writerow(self, rowbuffer):
        pass

    async def end(self):
        pass

class EscpProtocol(Protocol):
    def __init__(self):
        maxxscale = const(2)
        self.buffer = bytearray(linebytes*8*maxxscale)
        self.row = 7

    async def begin(self):
        self.row = 7
        fillarray(self.buffer, len(self.buffer), 0)
        await activeport.writeport(b"\x1b@")               # initialize printer
        await activeport.writeport(b"\x1b3%c" % 24)        # set line spacing 24/180=8*1/60 (i.e. 8 dots @60 dpi)
        await activeport.writeport(b"\x1bP")               # set pitch to 10cpi
        await activeport.writeport(b"\x1bl%c" % leftmargin)# set left margin
        await self.endofline()

    async def endofline(self):
        await activeport.writeport(b"\r")
        if linefeed:
            await activeport.writeport(b"\n")

    async def writeline(self, buffer):
        await activeport.writeport(b"\x1b*%c\x00%c" % (dotdensity, xscale))
        await activeport.writeport(buffer)
        await self.endofline()

    async def writerow(self, rowbuffer):
        global xscale

        column = 0
        for byte in rowbuffer:
            for bit in bytes(range(7, -1, -1)):
                for _ in range(xscale):
                    if byte & (1<<bit) != 0:
                        self.buffer[column] |= (1<<self.row)
                    column += 1
        self.row -= 1
        if self.row < 0:
            await self.writeline(self.buffer)
            fillarray(self.buffer, len(self.buffer), 0)
            self.row = 7

    async def end(self):
        if self.row != 7:
            await self.writeline(self.buffer)
        if formfeed:
            await activeport.writeport(b"\r\f")
        else:
            await self.endofline()
        await activeport.writeport(b"\x1b@")               # initialize printer

escpprotocol = EscpProtocol()
activeprotocol = escpprotocol

def setprotocol(protocol):
    global activeprotocol

    activeprotocol = protocol

def setprotocolescp():
    global activeprotocol

    activeprotocol = escpprotocol

async def writeopen():
    await activeport.openport()
    await activeprotocol.begin()

async def writerow(row):
    await activeprotocol.writerow(row)

async def writeclose():
    await activeprotocol.end()
    await activeport.closeport()

class FileRowGeneratorAsync:
    def __init__(self, filename):
        self.filehandle = UnpackBitsFile(filename)
        self.row = bytearray(32)

    def __aiter__(self):
        return self

    async def __anext__(self):
        for rowpos in range(32):
            byte = self.filehandle.read()
            if byte is None:
                self.filehandle.close()
                raise StopAsyncIteration
            self.row[rowpos] = byte
        return self.row

async def printrows(rows, message, prefix, isforever):
    starttime = None
    opened = False
    locked = False
    logging.info(message)
    while True:
        try:
            async for row in rows:
                if starttime is None:
                    if not enabled:
                        continue
                    starttime = time.ticks_ms()
                if not locked:
                    locked = True
                    await printerlock.acquire() # type: ignore
                if not opened:
                    opened = True
                    await writeopen()
                await writerow(row)
            if opened:
                await writeclose()
                opened = False
            if starttime is not None:
                printtime = time.ticks_diff(time.ticks_ms(), starttime)
                logging.info(f"{prefix} print time: {printtime} ms")
                logging.info(f"{prefix} print finished")
                starttime = None
        finally:
            if locked:
                printerlock.release()
                locked = False
        if not isforever:
            break

async def capture(rows):
    await printrows(rows, 'Waiting for printout to parallel or serial', "ZX/TS", True)

async def printfile(filename):
    await printrows(FileRowGeneratorAsync(filename), f'Printing file {filename}', "File", False)
