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

async def nullwrite(data):
    pass

enabled = False
linefeed = True
formfeed = False
leftmargin = 1
density = 0         # 0=60dpi, 1=120dpi
dotdensity = 0      # esp/p dot density (see esp/p table in docs)
xscale = 1

linebytes = const(32)
maxxscale = const(2)
buffer = bytearray(linebytes*8*maxxscale)
row = 7

printerlock = Lock()

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

def setenabled(state):
    global write
    global enabled

    if not state:
        write = nullwrite

    enabled = state

setenabled(False)

async def endofline():
    await write(b"\r")
    if linefeed:
        await write(b"\n")

async def writebuffer(buffer):
    await write(b"\x1b*%c\x00%c" % (dotdensity, xscale))
    await write(buffer)
    await endofline()

async def writerow(rowbuffer):
    global linebytes
    global xscale
    global buffer
    global row

    column = 0
    for byte in rowbuffer:
        for bit in bytes(range(7, -1, -1)):
            for _ in range(xscale):
                if byte & (1<<bit) != 0:
                    buffer[column] |= (1<<row)
                column += 1
    row -= 1
    if row < 0:
        await writebuffer(buffer)
        fillarray(buffer, len(buffer), 0)
        row = 7

async def writeopen():
    global linebytes
    global xscale
    global buffer
    global row

    row = 7
    fillarray(buffer, len(buffer), 0)
    await write(b"\x1b@")               # initialize printer
    await write(b"\x1b3%c" % 24)        # set line spacing 24/180=8*1/60 (i.e. 8 dots @60 dpi)
    await write(b"\x1bP")               # set pitch to 10cpi
    await write(b"\x1bl%c" % leftmargin)# set left margin
    await endofline()

async def writeclose():
    global row
    global buffer

    if row != 7:
        await writebuffer(buffer)
    if formfeed:
        await write(b"\r\f")
    else:
        await endofline()
    await write(b"\x1b@")               # initialize printer

class FileRowGeneratorAsync:
    def __init__(self, filename):
        self.filehandle = UnpackBitsFile(filename)
        self.chunk = bytearray(32)

    def __aiter__(self):
        return self

    async def __anext__(self):
        for rowpos in range(32):
            byte = self.filehandle.read()
            if byte is None:
                self.filehandle.close()
                raise StopAsyncIteration
            self.chunk[rowpos] = byte
        return self.chunk

async def print(rows, message, prefix, isforever):
    starttime = None
    rowbyte = 0
    rowbit = 7
    rowbuffer = bytearray(linebytes)
    rowbufferpos = 0
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
                for byte in row:
                    for bytebit in range(7,-1,-1):
                        pixel = byte & (1<<bytebit)
                        if pixel:
                            rowbyte = rowbyte | (1<<rowbit)
                        rowbit -= 1
                        if rowbit<0:
                            rowbuffer[rowbufferpos] = rowbyte
                            rowbufferpos += 1
                            if rowbufferpos>=linebytes:
                                await writerow(rowbuffer)
                                fillarray(rowbuffer, len(rowbuffer), 0)
                                rowbufferpos = 0
                            rowbit = 7
                            rowbyte = 0
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
    await print(rows, 'Waiting for printout to parallel or serial', "ZX/TS", True)

async def printfile(filename):
    await print(FileRowGeneratorAsync(filename), f'Printing file {filename}', "File", False)
