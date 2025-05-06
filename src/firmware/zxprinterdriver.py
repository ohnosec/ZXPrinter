# pyright: reportUndefinedVariable=false

from micropython import const
from rp2 import PIO, StateMachine, asm_pio, DMA
from machine import Pin, mem32
import time
import asyncio
from system import isrp2350

# GPIO
PORTRD          = const(6)
PORTCS          = const(7)

D0              = const(3)
D7OUT           = const(4)
D7IN            = const(5)

# status
READY           = const(D0)
ONPAPER         = const(D7OUT)

READY_MASK      = const(0b01)
ONPAPER_MASK    = const(0b10)

NOTREADY_MASK   = const(0b00)
OFFPAPER_MASK   = const(0b00)

OFFPAPER_STATUS = const(OFFPAPER_MASK | READY_MASK)
READY_STATUS    = const(ONPAPER_MASK  | READY_MASK)
BUSY_STATUS     = const(ONPAPER_MASK  | NOTREADY_MASK)

# command
PIXEL_ON        = const(D7IN)

# pins
PORTRD_PIN      = Pin(PORTRD, Pin.IN, Pin.PULL_UP)
PORTCS_PIN      = Pin(PORTCS, Pin.IN, Pin.PULL_UP)

READY_PIN       = Pin(READY, Pin.OUT)
ONPAPER_PIN     = Pin(ONPAPER, Pin.OUT)

PIXEL_ON_PIN    = Pin(PIXEL_ON, Pin.IN, Pin.PULL_UP)

PIO0_BASE       = const(0x50200000)
PIO1_BASE       = const(0x50300000)
SMX_EXECCTRL    = const(0x0cc)
STATUS_MASK     = const(0b1111111)  if isrp2350 else const(0b11111)
STATUS_SEL_TX   = const(0<<5)       if isrp2350 else const(0<<4)
STATUS_SEL_RX   = const(1<<5)       if isrp2350 else const(1<<4)
STATUS_LEVEL    = const(0b1111)

DREQ_PIOX_RXBASE= const(4)
PIOX_RXFBASE    = const(0x020)
DMA_SIZE_BYTE   = const(0)

# PIO status is all 1's if FIFO length is less than level, else all 0's
def configpiostatus(smid:int, istx:bool, level:int):
    piobase = PIO0_BASE if smid < 4 else PIO1_BASE
    execctrl = piobase + (SMX_EXECCTRL + (24 * (smid%4)))
    fifo = STATUS_SEL_TX if istx else STATUS_SEL_RX
    mem32[execctrl] &= ~STATUS_MASK
    mem32[execctrl] |= fifo | (level & STATUS_LEVEL)

# flow controlled by the fifo status
# fifo returns pixel
@asm_pio(
    sideset_init=(PIO.OUT_LOW,PIO.OUT_LOW),
    in_shiftdir=PIO.SHIFT_LEFT,
    out_shiftdir=PIO.SHIFT_RIGHT,
    autopush=True,
    push_thresh=8
    )
def port():
    label("nextrow")                                    # wait for row start
    set(x, 10)                                          # x = "off paper" read count
    label("offread")
    wait(1, gpio, PORTCS)       .side(OFFPAPER_STATUS)  # wait for end of read/write
    wait(0, gpio, PORTCS) [3]                           # wait for start of read/write
    jmp(pin, "nextrow")                                 # if write (i.e. not read) restart row
    jmp(x_dec, "offread")                               # if read count not finished get more

    label("getrow")
    mov(osr, invert(null))                              # x = 256 pixel count (0-255)
    out(x, 8)                   .side(READY_STATUS)

    label("nextpixel")
    wait(1, gpio, PORTCS)                               # wait for end of read/write
    wait(0, gpio, PORTCS) [3]                           # wait for start of read/write
    jmp(pin, "pixel")                                   # if write (i.e. not read)

    label("status")                                     # read status
    mov(y, status)                                      # is the fifo full?
    jmp(not_y, "nextpixel")     .side(BUSY_STATUS)      # yes...set status to busy
    jmp("nextpixel")            .side(READY_STATUS)     # no...set status to ready

    label("pixel")                                      # write pixel
    in_(pins, 1)                                        # get pixel and push
    jmp(x_dec, "nextpixel")                             # if same row get next pixel
    wrap()                                              # otherwise next row

PORT_ID = const(0)
PORT_FREQ = const(125_000_000)
PORT = StateMachine(PORT_ID, port, freq=PORT_FREQ, in_base=PIXEL_ON, sideset_base=D0, jmp_pin=PORTRD)
configpiostatus(PORT_ID, False, 2) # set status when RX FIFO reaches this level
PORT.active(1)

rowbuf = bytearray(32)
rowdma = DMA()

def configdma(smid: int):
    global rowbuf
    global rowdma

    piobase = PIO0_BASE if smid<4 else PIO1_BASE
    dreqrx = DREQ_PIOX_RXBASE + (smid//4 << 3) + smid%4 # see 2.5.3.1 in RP2040 datasheet
    piorxfifo = piobase + PIOX_RXFBASE + smid%4*4 # see 3.7 in RP2040 datasheet
    ctrl = rowdma.pack_ctrl(
        treq_sel=dreqrx,            # pace to the PIO RX FIFO
        inc_read=False,             # don't inc RX FIFO read address
        inc_write=True,             # inc array write address
        size=DMA_SIZE_BYTE,         # transfer one byte at a time
        )
    rowdma.config(
        read=piorxfifo,             # read from PIO RX FIFO
        write=rowbuf,               # write to row buffer
        count=len(rowbuf),
        ctrl=ctrl
        )

def startdma():
    rowdma.config(write=rowbuf, trigger=True)

def isrunningdma():
    return rowdma.count > 0

def rowserver():
    configdma(PORT_ID)
    while True:
        startdma()
        while isrunningdma():
            yield None
        yield rowbuf

class RowServerAsync:
    def __init__(self, timeout):
        configdma(PORT_ID)
        self.started = False
        self.timeout = timeout
        self.lasttime = time.ticks_ms()

    def __aiter__(self):
        return self

    async def __anext__(self):
        startdma()
        while isrunningdma():
            await asyncio.sleep_ms(0)
            if time.ticks_diff(time.ticks_ms(), self.lasttime) > self.timeout:
                if self.started:
                    self.started = False
                    raise StopAsyncIteration
        self.started = True
        self.lasttime = time.ticks_ms()
        return rowbuf

if __name__ == "__main__":
    print('waiting for print')

    for row in rowserver():
        if row is not None:
            for byte in row[0:16]:
                for bit in range(7,-1,-1):
                    print('*' if byte&(1<<bit) else ' ', end='')
            print("")
