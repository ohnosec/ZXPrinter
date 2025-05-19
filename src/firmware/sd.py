import os
from micropython import const
from sdmanager import SDManager
from event import notifyevent

SDBUS       = const(0)
SDCLK       = const(18)
SDMOSI      = const(19)
SDMISO      = const(16)
SDCS        = const(17)
SDCD        = const(27)

async def eventhandler(hascard):
    await notifyevent("sdcard", hascard)

def create():
    sd = SDManager(bus=SDBUS, sck=SDCLK, mosi=SDMOSI, miso=SDMISO, cs=SDCS, cd=SDCD)
    sd.addhandler(eventhandler)
    os.chdir("/")
    return sd