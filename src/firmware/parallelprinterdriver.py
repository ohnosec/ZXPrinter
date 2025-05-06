# pyright: reportUndefinedVariable=false

from micropython import const
from rp2 import DMA, PIO, StateMachine, asm_pio, asm_pio_encode
from machine import Pin
from machine import mem32
from array import array
import asyncio
from system import isrp2350

D0              = const(8)
D1              = const(9)
D2              = const(10)
D3              = const(11)
D4              = const(12)
D5              = const(13)
D6              = const(14)
D7              = const(15)
DATAWR          = const(20)         # normal
STATUSRD        = const(21)         # inverse
STROBE          = const(22)         # inverse

STATUSBUSY      = const(D1)

ACK_MASK        = const(1<<0)
BUSY_MASK       = const(1<<1)
PAPEROUT_MASK   = const(1<<2)
SELECT_MASK     = const(1<<3)
ERROR_MASK      = const(1<<4)

DATAWR_MASK     = const(1<<0)
NODATAWR_MASK   = const(0)
STATUSRD_MASK   = const(0)
NOSTATUSRD_MASK = const(1<<1)
STROBE_MASK     = const(1<<2)
NOSTROBE_MASK   = const(0)

SET_IDLE        = const(NOSTROBE_MASK | NOSTATUSRD_MASK | NODATAWR_MASK)
SET_DATAWR      = const(NOSTROBE_MASK | NOSTATUSRD_MASK | DATAWR_MASK)
SET_STATUSRD    = const(NOSTROBE_MASK | STATUSRD_MASK   | NODATAWR_MASK)
SET_STROBE      = const(STROBE_MASK   | NOSTATUSRD_MASK | NODATAWR_MASK)

SET_IDLE_PIO    = tuple(map(lambda b : PIO.OUT_HIGH if b=='1' else PIO.OUT_LOW, f'{SET_IDLE:03b}'))

d0pin           = Pin(D0, Pin.IN, Pin.PULL_DOWN)
d1pin           = Pin(D1, Pin.IN, Pin.PULL_DOWN)
d2pin           = Pin(D2, Pin.IN, Pin.PULL_DOWN)
d3pin           = Pin(D3, Pin.IN, Pin.PULL_DOWN)
d4pin           = Pin(D4, Pin.IN, Pin.PULL_DOWN)
d5pin           = Pin(D5, Pin.IN, Pin.PULL_DOWN)
d6pin           = Pin(D6, Pin.IN, Pin.PULL_DOWN)
d7pin           = Pin(D7, Pin.IN, Pin.PULL_DOWN)
datawritepin    = Pin(DATAWR,   Pin.OUT, value=int(f'{SET_IDLE:03b}'[2]))
statusreadpin   = Pin(STATUSRD, Pin.OUT, value=int(f'{SET_IDLE:03b}'[1]))
strobepin       = Pin(STROBE,   Pin.OUT, value=int(f'{SET_IDLE:03b}'[0]))

datapins        = [d0pin, d1pin, d2pin, d3pin, d4pin, d5pin, d6pin, d7pin]

# see 3.7 in RP2040 datasheet
PIO0_BASE       = const(0x50200000)
PIO1_BASE       = const(0x50300000)
PIOX_TXFX       = const(0x010)
PIO_IRQ         = const(0x030)

# see 2.5.7 in RP2040 datasheet
DMA_BASE        = const(0x50000000)
DMA_SIZE_BYTE   = const(0)
CHAN_ABORT      = const(DMA_BASE+0x464) if isrp2350 else const(DMA_BASE+0x444)
CHX_BASE        = const(0x000)
CHX_SIZE        = const(0x040)
CHX_AL1_CTRL    = const(0x010)

PORT_IRQ         = const(0)

def resetdma():
    for ctrloffset in range(CHX_BASE+CHX_AL1_CTRL, CHX_BASE+CHX_SIZE*12+CHX_AL1_CTRL, CHX_SIZE):
      mem32[DMA_BASE+ctrloffset] = 0

    mem32[CHAN_ABORT] = 0xff
    while mem32[CHAN_ABORT]!=0:
        pass

def getpioirq(smid:int, irq:int):
    piobase = PIO0_BASE if smid < 4 else PIO1_BASE
    return bool(mem32[piobase + PIO_IRQ] & (1<<irq))

def clearpioirq(smid:int, irq:int):
    piobase = PIO0_BASE if smid < 4 else PIO1_BASE
    mem32[piobase + PIO_IRQ] = 1<<irq

@asm_pio(
    set_init=SET_IDLE_PIO,
    out_init=(PIO.OUT_LOW,) * 8,
    out_shiftdir=PIO.SHIFT_LEFT
    )
def port():
    mov(osr, null)                      # set data bus direction to input
    out(pindirs, 8)
    set(pins, SET_STATUSRD)             # enable status read

    label("busy")                       # wait for command or not busy
    mov(osr, x)                         # is status command?
    out(y, 1)
    jmp(not_y, "status")
    jmp(pin, "busy")                    # wait for not busy

    label("getdataorcmd")               # get data or command
    pull(noblock)
    out(y, 1)
    jmp(not_y, "statusordata")
    jmp("getdataorcmd")                 # it's a write command
    label("statusordata")
    out(y, 1)
    jmp(not_y, "writedata")             # it's data

    label("status")                     # read status
    irq(block, PORT_IRQ)                # wait for status to be read
    jmp("busy")

    label("writedata")                  # write data
    out(null, 22)                       # move data to top 8 bits
    mov(y, osr)                         # save data
    set(pins, SET_IDLE)
    mov(osr, invert(null))              # set data bus direction to output
    out(pindirs, 8)
    mov(osr, y)                         # restore data
    out(pins, 8)
    set(pins, SET_DATAWR)
    set(pins, SET_STROBE)  [10]         # pulse strobe (~2.5us)
    # set(pins, SET_IDLE)               # NOTE: not enough room for this one extra instruction :)
    wrap()

WRITE_DATA_INST = asm_pio_encode("mov(x, invert(null))", 0)
READ_STATUS_INST = asm_pio_encode("mov(x, isr)", 0)

READ_COMMAND = const(0x7fffffff)

PORT_ID = const(5)

def init(sm):
    # put read status command into ISR
    sm.put(READ_COMMAND)
    sm.exec("pull()")
    sm.exec("mov(isr, osr)")

def setdata(sm):
    sm.exec(WRITE_DATA_INST)
    clearpioirq(PORT_ID, PORT_IRQ)

def waitforstatus(sm):
    sm.exec(READ_STATUS_INST)
    while not getpioirq(PORT_ID, PORT_IRQ):
        pass

PORT = StateMachine(PORT_ID, port, freq=10_000_000, set_base=DATAWR, in_base=D0, out_base=D0, jmp_pin=STATUSBUSY)
init(PORT)
setdata(PORT)
PORT.active(1)

def readstatus():
    waitforstatus(PORT)
    status = 0
    for i in range(8):
        status |= datapins[i].value() << i
    setdata(PORT)
    return status

def writedata(byte):
    PORT.put(byte)

def printstatus():
    status = readstatus()
    print(f'ACK:      {"Idle" if (status & ACK_MASK) == ACK_MASK else "Ack"}')
    print(f'BUSY:     {"Yes" if (status & BUSY_MASK) == BUSY_MASK else "No"}')
    print(f'PAPEROUT: {"Yes" if (status & PAPEROUT_MASK) == PAPEROUT_MASK else "No"}')
    print(f'SELECT:   {"Online" if (status & SELECT_MASK) == SELECT_MASK else "Offline"}')
    print(f'ERROR:    {"No" if (status & ERROR_MASK) == ERROR_MASK else "Fault"}')

def printmessage(message):
    for char in message:
        writedata(ord(char))

def printbytes(buf):
    for byte in buf:
        writedata(byte)

def islongarray(buf):
    if isinstance(buf, array):
        arraytype = str(buf).split("'")[1].split("'")[0]
        return arraytype == 'L'
    return false

portdma = DMA()

def configdma(smid: int):
    # DREQ_PIOx_TXx see 2.5.3.1 in RP2040 datasheet
    dreqtx = smid//4*8 + smid%4
    ctrl = portdma.pack_ctrl(
        treq_sel=dreqtx,                    # pace to this PIO TX FIFO
        inc_write=False,                    # don't inc TX FIFO write address
        inc_read=True,                      # inc array read address
        # size=DMA_SIZE_BYTE,                 # transfer one byte at a time
        )
    # TXFx see 3.7 in RP2040 datasheet
    piobase = PIO0_BASE if smid<4 else PIO1_BASE
    piotx = piobase + PIOX_TXFX + smid%4*4
    portdma.config(
        write=piotx,                        # write to PIO TX FIFO
        ctrl=ctrl
        )
    portdma.active(1)

def startdma(buf, buflen):
    portdma.config(read=buf, count=buflen, trigger=True)

def isrunningdma():
    return portdma.count > 0 # type: ignore

# resetdma()
configdma(PORT_ID)
CHUNKBUFLEN = const(32)
chunkbuf = array('L', [0]*CHUNKBUFLEN)

@micropython.native # type: ignore
def startchunkdma(buf, buflen, bufpos):
    chunklen = buflen if buflen < CHUNKBUFLEN else CHUNKBUFLEN
    for i in range(chunklen):
        chunkbuf[i] = buf[bufpos+i]
    startdma(chunkbuf, chunklen)
    return chunklen

def printbytesdma(buf):
    buflen = len(buf)
    bufpos = 0
    while buflen > 0:
        chunklen = startchunkdma(buf, buflen, bufpos)
        while isrunningdma():
            pass
        bufpos += chunklen
        buflen -= chunklen

async def printbytesdmaasync(buf):
    buflen = len(buf)
    bufpos = 0
    while buflen > 0:
        chunklen = startchunkdma(buf, buflen, bufpos)
        while isrunningdma():
            await asyncio.sleep_ms(0)
        bufpos += chunklen
        buflen -= chunklen

def test():
    printbytes(b"Hello\r\nThere\r\n")

def testb():
    for _ in range(20):
        printbytes(b"Hello\r\nThere\r\n")

def test2():
    printbytesdma(b"Hello\r\nThere\r\n")

def test2b():
    for _ in range(20):
        printbytesdma(b"Hello\r\nThere\r\n")

def test2c():
    printbytesdma(b"H"*130)

# PORT.put(b'0')
# PORT.tx_fifo()
# PORT.rx_fifo()
# PORT.get()
# PORT.exec("set(x, 0)")
