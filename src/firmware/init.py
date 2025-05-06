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

from phew import server, logging
from zxprinterdriver import RowServerAsync
from producerconsumer import ProducerConsumer
import ledprinter
import fileprinter
import physicalprinter
import services
import webserver
import serialserver
import secretsmanager
import gc

# logging.enable_logging_types(logging.LOG_ALL)
logging.logger = logging.file_logger
# logging.logger = print

services.initialise(connectedpixel)
secretsmanager.initialize()
webserver.initialize(connectedpixel)
serialserver.initialize()

print("Starting...")

printserver = ProducerConsumer(RowServerAsync(PRTTIMEOUT))
server.loop.create_task(printserver.getproducer())
server.loop.create_task(ledprinter.capture(printserver.addconsumer(), capturepixel))
server.loop.create_task(fileprinter.capture(printserver.addconsumer()))
server.loop.create_task(physicalprinter.capture(printserver.addconsumer()))

server.loop.create_task(serialserver.start())
server.loop.create_task(webserver.start())

gc.collect()

server.run()
