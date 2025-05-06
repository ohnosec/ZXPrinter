# pyright: reportUndefinedVariable=false

import time
from micropython import const
from rp2 import DMA, PIO, StateMachine, asm_pio, asm_pio_encode
from machine import mem32
from uctypes import addressof
from array import array
from machine import Timer
from system import isrp2350

# see 3.7 in RP2040 datasheet
PIO0_BASE           = const(0x50200000)
PIO1_BASE           = const(0x50300000)
PIOX_TXFX           = const(0x010)

# see 2.5.7 in RP2040 datasheet
DMA_BASE            = const(0x50000000)
CHAN_ABORT          = const(DMA_BASE+0x464) if isrp2350 else const(DMA_BASE+0x444)
CHX_BASE            = const(0x000)
CHX_SIZE            = const(0x040)
CHX_AL1_CTRL        = const(0x010)
CTRL_CHAIN_TO_BITS  = const(0x00007800)
CTRL_CHAIN_TO_LSB   = const(11)

def resetdma():
    for ctrloffset in range(CHX_BASE+CHX_AL1_CTRL, CHX_BASE+CHX_SIZE*12+CHX_AL1_CTRL, CHX_SIZE):
      mem32[DMA_BASE+ctrloffset] = 0

    mem32[CHAN_ABORT] = 0xff
    while mem32[CHAN_ABORT]!=0:
        pass

def resetpio():
    PIO(0).remove_program()
    PIO(1).remove_program()

def reset():
    resetdma()
    resetpio()

T1              = const(2)
T2              = const(5)
T3              = const(3)
cycles_per_bit  = const(T1 + T2 + T3)

class Driver:
    # bits are encoded as short or long pulses
    # short for a zero
    #    <-- T1 --><-- T2 --><-- T3 -->
    #     ________
    # ___/        \____________________
    #
    # long for a one
    #    <-- T1 --><-- T2 --><-- T3 -->
    #     __________________
    # ___/                  \__________
    @staticmethod
    @asm_pio(
        sideset_init=(PIO.OUT_HIGH),
        out_shiftdir=PIO.SHIFT_LEFT,
        in_shiftdir=PIO.SHIFT_LEFT
        )
    def pixel():
        pull()                      .side(0)
        out(isr, 8)                                     # load delay into isr
        in_(null, 16)                                   # and multiply by shifting
        label("nextbit")
        out(x, 1)                   .side(0) [T3-1]     # get next bit.......set low for T3
        jmp(not_x, "zero")          .side(1) [T1-1]     # what is the bit?...set high for T1
        jmp(not_osre, "nextbit")    .side(1) [T2-1]     # bit is one.........keep high for T2
        label("zero")
        jmp(not_osre, "nextbit")    .side(0) [T2-1]     # bit is zero........set low for T2
        mov(x, isr)                                     # get delay into x
        label("delay")
        label("stop")
        jmp(not_y, "stop")                              # if stop then spin lock
        jmp(x_dec, "delay")                             # and wait for x time
        wrap()

    def __init__(self, id, pin=None):
        self.id = id
        self._reset_inst = asm_pio_encode("set(x, 0)", 0)
        self._start_inst = asm_pio_encode("set(y, 1)", 0)
        self._stop_inst  = asm_pio_encode("set(y, 0)", 0)
        self._pull_inst  = asm_pio_encode("pull(noblock)", 0)
        if pin is not None:
            self.init(pin)

    def init(self, pin):
        self._sm = StateMachine(self.id, self.pixel, freq=800_000*cycles_per_bit, sideset_base=pin)
        self.start()

    def start(self):
        self._sm.exec(self._reset_inst)
        self._sm.exec(self._start_inst)
        self._sm.restart()
        self._sm.active(1)

    def stop(self):
        self._sm.exec(self._stop_inst)
        time.sleep_ms(1)
        self._sm.active(0)

    def reset(self):
        self._sm.active(0)
        self.flush()
        self.start()

    def flush(self):
        for _ in range(4):
            self._sm.exec(self._pull_inst)

@micropython.viper
def set_chain_to(ctrl: int, chain_to: int) -> int:
    return (ctrl & ~CTRL_CHAIN_TO_BITS) | (chain_to << CTRL_CHAIN_TO_LSB)

@micropython.viper
def make_pixel(r: int, g: int, b: int, wait:int) -> int:
    return wait<<24 | r<<8 | g<<16 | b

# ~mask (not invert) is not supported in MPv1.22
# @micropython.viper
# def set_pixel(pixelbuf, index: int, value: int, mask: int):
#     buf = ptr32(pixelbuf)
#     buf[index] &= ~mask
#     buf[index] |= value

@micropython.native
def set_pixel(pixelbuf, index: int, value: int, mask: int):
    pixelbuf[index] &= ~mask
    pixelbuf[index] |= value

class Canvas:
    def __init__(self, size):
        self._buf = array('L', [0]*size)

    @property
    def buf(self):
        return self._buf

class Controller:
    def __init__(self, id, pin):
        self._driver = Driver(id, pin)
        self._isstarted = False
        self._pixeldma = DMA()
        self._repeatdma = DMA()
        self._bufaddr = array('L', [0])
        self._buf = None

    # if the last pixel doesn't have a delay the neopixel doen't reset
    # force some delay on the last pixel
    def _fixbuf(self, buf):
        if (buf[len(buf)-1] & (0xff << 24)) == 0:
            buf[len(buf)-1] |= 0x01 << 24

    def _start(self, buf, repeat):
        self._fixbuf(buf)

        self._repeatdma.active(0)
        self._pixeldma.active(0)
        # DREQ_PIOx_TXx see 2.5.3.1 in RP2040 datasheet
        dreqtx = self._driver.id//4*8 + self._driver.id%4
        pixelchain = self._repeatdma.channel if repeat else self._pixeldma.channel
        ctrl = self._pixeldma.pack_ctrl(
            treq_sel=dreqtx,                    # pace to this PIO TX FIFO
            chain_to=pixelchain,                # trigger repeat DMA when done
            inc_write=False,                    # don't inc TX FIFO write address
            inc_read=True,                      # inc array read address
            bswap=False,                        # don't reverse bytes
            )
        # TXFx see 3.7 in RP2040 datasheet
        piobase = PIO0_BASE if self._driver.id<4 else PIO1_BASE
        piotx = piobase + PIOX_TXFX + self._driver.id%4*4
        self._pixeldma.config(
            read=addressof(buf),                # read from pixel buffer
            write=piotx,                        # write to PIO TX FIFO
            count=len(buf),
            ctrl=ctrl
            )
        ctrl = self._repeatdma.pack_ctrl(
            chain_to=self._pixeldma.channel,    # trigger pixel DMA when done
            inc_write=False,                    # don't inc DMA write address
            inc_read=False,                     # don't inc array read address
            bswap=False,                        # don't reverse bytes
        )
        self._bufaddr[0] = addressof(buf)
        pixelreadaddr = self._pixeldma.registers[0:1]
        self._repeatdma.config(
            read=addressof(self._bufaddr),      # read from address of pixel buffer
            write=pixelreadaddr,                # write to READ_ADDR of pixel DMA
            count=1,
            ctrl=ctrl
            )
        self._buf = buf
        if repeat:
            self._repeatdma.active(1)
        self._pixeldma.active(1)

    def _restart(self, buf, repeat):
        self._fixbuf(buf)

        self._driver.stop()

        self._pixeldma.count = 0
        while(self._pixeldma.count > 0):
            self._driver.flush()
        self._pixeldma.active(0)
        self._repeatdma.active(0)

        self._driver.reset()

        self._bufaddr[0] = addressof(buf)
        pixelchain = self._repeatdma.channel if repeat else self._pixeldma.channel
        ctrl = set_chain_to(self._pixeldma.ctrl, pixelchain)
        self._pixeldma.config(
            read=addressof(buf),
            count=len(buf),
            ctrl=ctrl
            )
        self._buf = buf
        if repeat:
            self._repeatdma.active(1)
        self._pixeldma.active(1)

    def render(self, buf, repeat = True):
        if isinstance(buf, Canvas):
            buf = buf.buf
        if not self._isstarted:
            self._start(buf, repeat)
            self._isstarted = True
        else:
            self._restart(buf, repeat)

def get_pixel_shift(mask: int):
    return (3-mask.to_bytes(4, 'big').index(b'\xff'))*8

class Pixel:
    RED = 1
    GREEN = 2
    BLUE = 3

    red_mask = make_pixel(0xff, 0, 0, 0)
    green_mask = make_pixel(0, 0xff, 0, 0)
    blue_mask = make_pixel(0, 0, 0xff, 0)

    red_shift = get_pixel_shift(red_mask)
    green_shift = get_pixel_shift(green_mask)
    blue_shift = get_pixel_shift(blue_mask)

    def __init__(self, color, buf, index=0, intensity=255):
        if color == Pixel.RED:
             self.mask = Pixel.red_mask
             self.shift = Pixel.red_shift
        elif color == Pixel.GREEN:
             self.mask = Pixel.green_mask
             self.shift = Pixel.green_shift
        elif color == Pixel.BLUE:
             self.mask = Pixel.blue_mask
             self.shift = Pixel.blue_shift
        else:
            raise ValueError("Color must be Pixel.RED, Pixel.GREEN, or Pixel.BLUE")
        if isinstance(buf, Canvas):
            buf = buf.buf
        self.buf = buf
        self.index = index
        self.on_intensity = intensity
        self.timer = Timer()
        self.flashdone = True
        self.retrigger = False

    def intensity(self, value = None):
        if value is None:
            return (self.buf[self.index]>>self.shift) & 0xff
        else:
            set_pixel(self.buf, self.index, value<<self.shift, self.mask)

    def _flashdone(self, milliseconds, rearm):
        self.flashdone = True
        if self.flashcancel:
            return
        if self.retrigger:
            self.flash(milliseconds, rearm=milliseconds if rearm is None else rearm, retrigger=True)

    def _flashoff(self, milliseconds, rearm):
        if self.flashcancel:
            self.flashdone = True
            return
        self.intensity(0)
        if rearm is None:
            self._flashdone(milliseconds, rearm)
        else:
            self.timer.init(period=rearm, mode=Timer.ONE_SHOT, callback=lambda t:self._flashdone(milliseconds, rearm))

    def flash(self, milliseconds, rearm=None, retrigger=False):
        if not self.flashdone:
            return
        self.intensity(self.on_intensity)
        self.flashdone = False
        self.flashcancel = False
        self.retrigger = retrigger
        self.timer.init(period=milliseconds, mode=Timer.ONE_SHOT, callback=lambda t:self._flashoff(milliseconds, rearm))

    def on(self):
        self.flashcancel = True
        self.retrigger = False
        self.intensity(self.on_intensity)

    def off(self):
        self.retrigger = False
        self.flashcancel = True
        self.intensity(0)

    def toggle(self):
        self.retrigger = False
        self.flashcancel = True
        if self.intensity() != 0:
            self.off()
        else:
            self.on()
