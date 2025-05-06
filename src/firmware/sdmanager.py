import os
import time
from micropython import const
from machine import SPI, Pin
from phew import logging
from sdcard import SDCard

DETECT_BOUNCE = const(200)

class SDManager:
    def __init__(self, bus, sck, mosi, miso, cs, cd, mount_point='/sd'):
        self.mount_point = mount_point

        cspin = Pin(cs, Pin.OUT, Pin.PULL_UP)
        clkpin = Pin(sck, Pin.OUT)
        mosipin = Pin(mosi, Pin.OUT)
        misopin = Pin(miso, Pin.IN, Pin.PULL_UP)

        spi = SPI(bus, sck=clkpin, mosi=mosipin, miso=misopin)
        self.card = SDCard(spi, cspin, init=False)

        self.mountex = None
        self.mounted = False
        self.mounts = 0

        self.cdtime = time.ticks_ms()
        self.cdpin = Pin(cd, Pin.IN, Pin.PULL_UP)
        self.cdpin.irq(self._cardchange, Pin.IRQ_RISING | Pin.IRQ_FALLING)

        if self._hascard():
            self.mount()

    def ismounted(self):
        return self._hascard() and self.mounted

    def _hascard(self):
        return not self.cdpin.value()

    def mount(self):
        try:
            self.mountex = None
            logging.info("Init SD card")
            self.card.init_card()
            logging.info("Mount SD card")
            os.mount(self.card, self.mount_point) # type: ignore
            self.mounted = True
        except Exception as ex:
            logging.error(f"mount exception: {ex}")
            self.mountex = ex
        return self.mounted

    def unmount(self):
        try:
            self.mountex = None
            self.mounted = False
            logging.info("Unmount SD card")
            os.umount(self.mount_point) # type: ignore
        except Exception as ex:
            logging.error(f"unmount exception: {ex}")
            self.mountex = ex
        return self.mounted

    def _cardchange(self, _):
        # this just ignores subsequent card detect changes,
        # but it can be triggered by transient changes an also miss changes
        # should really kick off a timer and wait till the card detect is stable
        if time.ticks_diff(time.ticks_ms(), self.cdtime)>DETECT_BOUNCE:
            self.mounts += 1
            if self._hascard():
                self.mount()
            else:
                self.unmount()
            self.cdtime = time.ticks_ms()