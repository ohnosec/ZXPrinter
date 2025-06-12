DEBUG = False

from reset import resetall
resetall()

from micropython import const
import pixeldriver
import pixel

PRTTIMEOUT = const(2000)

print("Initializing...")

pixel.initialize()
connectedpixel = pixel.create(pixeldriver.Pixel.GREEN)
capturepixel = pixel.create(pixeldriver.Pixel.RED)
connectedpixel.flash(500, 500, retrigger=True)

import asyncio
import sys
import io
import gc
from system import hasnetwork
from phew import logging
from zxprinterdriver import RowServerAsync
from producerconsumer import ProducerConsumer
import ledprinter
import fileprinter
import physicalprinter
import services
import serialserver
import settings
import sd

if DEBUG:
    logging.enable_logging_types(logging.LOG_ALL)
    logging.logger = print
else:
    logging.logger = logging.rotatefile_logger

def exceptionhandler(_, context):
    ex = context["exception"]
    exfile = io.StringIO()
    sys.print_exception(ex, exfile) # type: ignore
    exmessage = exfile.getvalue().strip() # type: ignore
    logging.error(f"Exception: {ex}\n{exmessage}")

webenabled = hasnetwork()

sdmanager = sd.create()

settings.initialize()
services.initialise(connectedpixel, sdmanager)
fileprinter.initialise(sdmanager)
if webenabled:
    import webserver
    webserver.initialize(connectedpixel)
serialserver.initialize()

print("Starting...")

eventloop = asyncio.get_event_loop()
eventloop.set_exception_handler(exceptionhandler)

printserver = ProducerConsumer(RowServerAsync(PRTTIMEOUT))
eventloop.create_task(printserver.getproducer())
eventloop.create_task(ledprinter.capture(printserver.addconsumer(), capturepixel))
eventloop.create_task(fileprinter.capture(printserver.addconsumer()))
eventloop.create_task(physicalprinter.capture(printserver.addconsumer()))

eventloop.create_task(serialserver.start())
if webenabled:
    eventloop.create_task(webserver.start())

gc.collect()

eventloop.run_forever()
