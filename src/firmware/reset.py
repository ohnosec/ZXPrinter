from micropython import const
from rp2 import PIO
from machine import mem32
from system import isrp2350

# see 2.5.7 in RP2040 datasheet
DMA_BASE            = const(0x50000000)
CHAN_ABORT          = const(DMA_BASE+0x464) if isrp2350 else const(DMA_BASE+0x444)
CHX_BASE            = const(0x000)
CHX_SIZE            = const(0x040)
CHX_AL1_CTRL        = const(0x010)

def resetdma():
    for ctrloffset in range(CHX_BASE+CHX_AL1_CTRL, CHX_BASE+CHX_SIZE*12+CHX_AL1_CTRL, CHX_SIZE):
      mem32[DMA_BASE+ctrloffset] = 0

    mem32[CHAN_ABORT] = 0xff
    while mem32[CHAN_ABORT]!=0:
        pass

def resetpio():
    PIO(0).remove_program()
    PIO(1).remove_program()

def resetall():
    resetdma()
    resetpio()
