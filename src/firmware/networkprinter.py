from micropython import const
import asyncio
import struct
import math
from phew import logging
import physicalprinter
from system import hasnetwork
from bitmap import packbits_encode, bitmap_to_escpr

if hasnetwork():
    import socket

RAWPORT = 9100

address = None

def getaddress():
    global address

    return address

def setaddress(newaddress):
    global address

    address = newaddress

class NetworkPort(physicalprinter.Port):
    def __init__(self):
        self.sock = None
        self.writer = None

    async def openport(self):
        global address

        if not hasnetwork():
            self.sock = None
            self.writer = None
            logging.error("Can't network print as there's no WIFI on this device")
            return
        if not address:
            self.sock = None
            self.writer = None
            logging.error("Network printer failed: no address set")
            return
        logging.info(f"Network printer connecting to '{address}'")
        try:
            self.sock = socket.socket()
            self.server = socket.getaddrinfo(address, RAWPORT)[0][-1]
            self.sock.connect(self.server)
            self.writer = asyncio.StreamWriter(self.sock, {})
        except Exception as ex:
            await self.closeport()
            logging.error(f"Network printer failed to connect: {ex}")

    async def closeport(self):
        if self.sock:
            self.sock.close()
            self.sock = None
            self.writer = None

    async def writeport(self, data):
        if self.writer:
            try:
                self.writer.write(data) # type: ignore
                await self.writer.drain() # type: ignore
            except OSError:
                await self.closeport()

networkport = NetworkPort()

A4 = (210.000, 297.000)
LETTER = (215.900, 279.400)

# paper = A4              # media size: A4
paper = LETTER          # media size: LETTER
margin = (3, 3, 3, 3)   # 3mm borders
dpi = const(360)        # 360dpi
pd = const(0x00)        # page direction: bidirectional
# cmode = const(0)        # not compressed
cmode = const(1)        # compressed

scale = const(6)        # 6x
leftedge = const(30)    # x position

mm2in = 1.0 / 25.4
def todpi(value, dpi):
    return value * mm2in * dpi

def toir(dpi):
    ir = 0
    if dpi == 720:
        ir = 1
    elif dpi == 300:
        ir = 2
    elif dpi == 600:
        ir = 3
    elif dpi == 360:
        ir = 0
    else:
        raise ValueError(f"Unsupported DPI value: {dpi}")
    return ir

class EscprProtocol(physicalprinter.Protocol):
    def __init__(self):
        self.line = bytearray(physicalprinter.linebytes*8*scale)
        self.compressedline = bytearray(len(self.line)*2)
        self.compressedlinemv = memoryview(self.compressedline)

    def compress(self, linelen):
        length = packbits_encode(self.line, linelen, self.compressedline)
        return self.compressedlinemv[:length]

    async def begin(self):
        await self.write(b"\x00\x00\x00\x1b\x01@EJL 1284.4\n@EJL     \n")   # exit packet mode
        await self.write(b"\x1b@")                                          # initialize printer
        await self.write(b"\x1b(R\x06\x00\x00ESCPR")                        # set ESC/P-R mode

        # plain paper, high quality, color palette=(black, white)
        quality = bytearray(b'\x00\x02\x00\x00\x00\x00\x01\x00\x06\x00\x00\x00\xff\xff\xff')
        await self.writecmd(b"q", b"setq", quality)                         # quality

        paperwidth =  math.ceil(todpi(paper[0], dpi))
        paperheight = math.ceil(todpi(paper[1], dpi))
        marginleft = math.floor(todpi(margin[0], dpi))
        margintop = math.floor(todpi(margin[1], dpi))
        marginright = math.floor(todpi(margin[2], dpi))
        marginbottom = math.floor(todpi(margin[3], dpi))
        printwidth = paperwidth - marginleft - marginright
        printheight = paperheight - margintop - marginbottom
        job = struct.pack(">LLHHLLBB", paperwidth, paperheight, margintop, marginleft, printwidth, printheight, toir(dpi), pd)
        await self.writecmd(b"j", b"setj", job)                             # job

        pageno = 1                                                          # page number: 1
        await self.writecmd(b"p", b"sttp")                                  # start page
        await self.writecmd(b"p", b"setn", bytearray(pageno))               # page number

        self.y = 0

    async def write(self, data):
        await physicalprinter.activeport.writeport(data)

    async def writecmd(self, cmd, code, data=None, datalen=None):
        if data is None:
            data = b""
        if datalen is None:
            datalen = len(data)
        await self.write(b"\x1b" + cmd + struct.pack("<L", datalen) + code + data)

    async def writeline(self, line, x, y):
        data = struct.pack(">HHBH", x, y, cmode, len(line))
        await self.writecmd(b"d", b"dsnd", data, len(data)+len(line))
        await self.write(line)

    async def writerow(self, rowbuffer):
        linelen = bitmap_to_escpr(rowbuffer, self.line, scale)
        line = self.compress(linelen)
        for _ in range(scale): # yscale
            await self.writeline(line, leftedge, self.y)
            self.y += 1

    async def end(self):
        pagesleft = 0
        await self.writecmd(b"p", b"endp", bytearray(pagesleft))            # end page
        await self.writecmd(b"j", b"endj")                                  # end job
        await self.write(b"\x1b@")                                          # initialize printer

escpprotocol = EscprProtocol()

def setprotocolescpr():
    physicalprinter.setprotocol(escpprotocol)

def setdefaultprotocol():
    setprotocolescpr()

def setactive():
    setdefaultprotocol()
    physicalprinter.setport(networkport)
    physicalprinter.setenabled(True)
