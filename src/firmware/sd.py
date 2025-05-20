import os
from micropython import const
from sdmanager import SDManager
from event import notifyevent, addconnecthandler

SDBUS       = const(0)
SDCLK       = const(18)
SDMOSI      = const(19)
SDMISO      = const(16)
SDCS        = const(17)
SDCD        = const(27)

async def mounthandler(hascard):
    await notifyevent("sdcard", hascard)

async def connecthandler(sd):
    await notifyevent("sdcard", sd.ismounted())

def create():
    sd = SDManager(bus=SDBUS, sck=SDCLK, mosi=SDMOSI, miso=SDMISO, cs=SDCS, cd=SDCD)
    sd.addhandler(mounthandler)
    addconnecthandler(connecthandler, sd)
    os.chdir("/")
    return sd