import os
import time
import asyncio
from micropython import const
from machine import SPI, Pin
from phew import logging
from sdcard import SDCard

CARDDETECTMS = const(250)

class SDManager:
    def __init__(self, bus, sck, mosi, miso, cs, cd, mount_point='/sd'):
        self.mount_point = mount_point

        clkpin = Pin(sck, Pin.OUT)
        mosipin = Pin(mosi, Pin.OUT)
        misopin = Pin(miso, Pin.IN, Pin.PULL_UP)

        self.cspin = Pin(cs, Pin.OUT)
        self.spi = SPI(bus, baudrate=24_000_000, sck=clkpin, mosi=mosipin, miso=misopin)
        self.card = None

        self.mountex = None
        self.mounted = False

        self.cdhandlers = []
        self.cdtime = time.ticks_ms()
        self.cdpin = Pin(cd, Pin.IN, Pin.PULL_UP)
        self.cdhascard = False
        self.cdtask = asyncio.create_task(self._cardwatch())

    def ismounted(self):
        return self._hascard() and self.mounted

    def _hascard(self):
        return not self.cdpin.value()

    def mount(self):
        try:
            self.mountex = None
            logging.info("Init SD card")
            self.card = SDCard(self.spi, self.cspin)
            logging.info("Mount SD card")
            os.mount(self.card, self.mount_point) # type: ignore
            self.mounted = True
        except Exception as ex:
            logging.error(f"Mount exception: {ex}")
            self.mountex = ex
        return self.mounted

    def unmount(self):
        try:
            self.mountex = None
            logging.info("Unmount SD card")
            os.umount(self.mount_point) # type: ignore
            self.card = None
            self.mounted = False
        except Exception as ex:
            logging.error(f"Unmount exception: {ex}")
            self.mountex = ex
        return self.mounted

    def addhandler(self, handler):
        self.cdhandlers.append(handler)

    async def _cardwatch(self):
        while True:
            hascard = self._hascard()
            if hascard != self.cdhascard:
                if hascard:
                    self.mount()
                else:
                    self.unmount()
                self.cdhascard = hascard
                for handler in self.cdhandlers:
                    await handler(hascard)
            await asyncio.sleep_ms(CARDDETECTMS) # type: ignore
