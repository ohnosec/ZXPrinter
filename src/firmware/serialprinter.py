from micropython import const
from machine import Pin, UART
import asyncio
import physicalprinter

XON = const(0x11)
XOFF = const(0x13)

TX = const(0)
RX = const(1)
# CTS = const(26)   # pcb v0.4
CTS = const(2)      # pcb v0.4c, v1.0

BUSY_SLEEP = const(200)

port = UART(0, baudrate=19200, tx=Pin(TX), rx=Pin(RX), cts=Pin(CTS), bits=8, parity=None, stop=1, txbuf=1) # type: ignore
portwriter = asyncio.StreamWriter(port, {}) # type: ignore
portreader = asyncio.StreamReader(port) # type: ignore

stopped = False
softflow = False
interchardelayms = 0

class SerialPort(physicalprinter.Port):
    async def writeport(self, line):
        global stopped

        if softflow or interchardelayms>0:
            for byte in line:
                if softflow:
                    while stopped:
                        while port.any():
                            read = await portreader.read(1) # type: ignore
                            # any character starts transmission, doesn't have to be XON
                            stopped = True if read[0] == XOFF else False
                        await asyncio.sleep_ms(BUSY_SLEEP) # type: ignore
                await portwriter.awrite([byte]) # type: ignore
                if interchardelayms>0:
                    await asyncio.sleep_ms(interchardelayms) # type: ignore
        else:
            await portwriter.awrite(data) # type: ignore

serialport = SerialPort()

def setactive():
    physicalprinter.resetprotocol()
    physicalprinter.setport(serialport)
    physicalprinter.setenabled(True)

def setsettings(baudrate, bits, parity, stop):
    parityvalue = 0 if parity=='even' else 1 if parity=='odd' else None
    port.init(baudrate=baudrate, bits=bits, parity=parityvalue, stop=stop)

def setflowcontrol(hardware, software, delayms):
    global softflow
    global interchardelayms
    global stopped

    softflow = software

    hardflow = UART.CTS if hardware else 0
    port.init(flow = hardflow) # type: ignore

    interchardelayms = delayms
    stopped = False
