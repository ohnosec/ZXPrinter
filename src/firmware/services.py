import os
import json
from micropython import const
import parallelprinter
import serialprinter
from phew import server, logging
import fileprinter
import physicalprinter
from sdmanager import SDManager
import secretsmanager
from system import hasnetwork

SDBUS       = const(0)
SDCLK       = const(18)
SDMOSI      = const(19)
SDMISO      = const(16)
SDCS        = const(17)
SDCD        = const(27)

def initialise(p):
    global sd
    global connectedpixel

    connectedpixel = p

    sd = SDManager(bus=SDBUS, sck=SDCLK, mosi=SDMOSI, miso=SDMISO, cs=SDCS, cd=SDCD)
    os.chdir("/")

    physicalprinter.setenabled(False)

@micropython.native # type: ignore
async def render_printout(filename):
    filename = fileprinter.getfilepath(filename)
    # starttime = time.ticks_ms()
    chunk = bytearray(1024)
    chunkview = memoryview(chunk)
    yield '['
    try:
        with open(filename, "rb") as filehandle:
            firstchunk = True
            while True:
                bytecount = filehandle.readinto(chunk)
                if not bytecount:
                    # logging.info(f"Render printout took {time.ticks_diff(time.ticks_ms(), starttime)} ms")
                    return
                if not firstchunk:
                    yield ','
                firstchunk = False
                firstblock = True
                for blockpos in range(0, bytecount, 128):
                    if not firstblock:
                        yield ','
                    firstblock = False
                    yield '"'
                    yield chunkview[blockpos:min(blockpos+128, bytecount)].hex()
                    yield '"'
    finally:
        yield ']'

def get_printouts():
    return fileprinter.getfiles()

def delete_printout(filename):
    os.remove(fileprinter.getfilepath(filename))

def print_printout(filename):
    server.loop.create_task(physicalprinter.printfile(fileprinter.getfilepath(filename)))

def copy_printout(filename):
    filename = fileprinter.getfilepath(filename)
    if os.getcwd() == "/":
        fromfilename = f"{sd.mount_point}/{filename}"
        topath = "/"
    else:
        fromfilename = f"/{filename}"
        topath = f"{sd.mount_point}/"
    nextfilename = fileprinter.nextfilename()
    logging.info(f"Copying from {fromfilename} to {topath}{nextfilename}")
    copyfile(fromfilename, nextfilename)
    fileprinter.savesettings()

def setstorename(name):
    logging.info(f"Changing store to {name}")
    if name.lower() == "sdcard":
        os.chdir(sd.mount_point)
    else:
        os.chdir("/")
    fileprinter.captureinit()

def setprintercapture(state):
    logging.info(f"Changing printer capture to {state}")
    state = state.lower()
    fileprinter.setcapture(state == "on")

def setprinterendofline(char):
    logging.info(f"Changing printer end of line to {char}")
    char = char.lower()
    physicalprinter.setlinefeed(char == "crlf")

def setprinterendofprint(char):
    logging.info(f"Changing printer end of print to {char}")
    char = char.lower()
    physicalprinter.setformfeed(char == "ff")

def setprinterleftmargin(value):
    logging.info(f"Changing printer left margin to {value}")
    physicalprinter.setleftmargin(value)

def setprinterdensity(value):
    logging.info(f"Changing printer density to {value}")
    physicalprinter.setdensity(value)

def setprintertarget(target):
    logging.info(f"Changing printer to {target}")
    target = target.lower()
    if target == "off":
        physicalprinter.setenabled(False)
    elif target == "serial":
        serialprinter.setactive()
    elif target == "parallel":
        parallelprinter.setactive()

def setserialsettings(settings):
    logging.info(f"Setting serial to {settings}")
    serialprinter.setsettings(settings['baudrate'], settings['bits'], settings['parity'], settings['stop'])

def setserialflow(hardware, software, delayms):
    logging.info(f"Setting serial flow control to hardware={hardware} software={software} delayms={delayms}")
    serialprinter.setflowcontrol(hardware, software, delayms)

def getnetwork():
    return {
        'ssid': secretsmanager.getssid()
    }

async def sethostname(newhostname):
    import network

    if newhostname != network.hostname():
        logging.info(f"Setting hostname {newhostname}")
        secretsmanager.sethostname(newhostname)
        secretsmanager.savesecrets()
        network.hostname(newhostname)
    return {}

async def setnetwork(newssid, newpassword):
    secretsmanager.setssid(newssid)
    if newpassword is not None:
        secretsmanager.setpassword(newpassword)
    secretsmanager.savesecrets()
    return {}

def connect(newssid, newpassword):
    import network

    wlan = network.WLAN()
    ssid = secretsmanager.getssid()
    password = secretsmanager.getpassword()
    if newssid is not None:
        ssid = newssid
    if newpassword is not None:
        password = newpassword

    connectedpixel.flash(500, 500, retrigger=True)

    wlan.disconnect()
    wlan.connect(ssid, password)

    connectedpixel.on()

    return {}

def status():
    import network

    wlan = network.WLAN()
    connected = wlan.isconnected()
    rssi = wlan.status('rssi')
    state = wlan.status()
    if state == network.STAT_IDLE:             # 0
        status = "No connection"
    elif state == network.STAT_CONNECTING:     # 1
        status = "Connecting"
    elif state == network.STAT_GOT_IP:         # 3
        status = "Connected"
    elif state == network.STAT_WRONG_PASSWORD: # -3
        status = "Wrong password"
    elif state == network.STAT_NO_AP_FOUND:    # -2
        status = "Network not found"
    elif state == network.STAT_CONNECT_FAIL:   # -1
        status = "Connection failed"
    else:
        status = "Unknown"
    if state==network.STAT_GOT_IP:
        ipaddress = wlan.ifconfig()[0]
    else:
        ipaddress = ""
    macaddress = ':'.join([f"{b:02X}" for b in wlan.config('mac')])
    return {
        'state': state,
        'status': status,
        'rssi': rssi,
        'connected': connected,
        'connecting': state == network.STAT_CONNECTING,
        'hostname': network.hostname(),
        'ip': ipaddress,
        'mac': macaddress
    }

def scan():
    import network

    wlan = network.WLAN()
    networks = [{'ssid': net[0], 'rssi': net[3]} for net in wlan.scan()]
    return networks

async def getlogfile():
    yield '['
    try:
        with open(logging.log_file) as filehandle:
            firstline = True
            while True:
                line = filehandle.readline()
                if not line:
                    return
                if not firstline:
                    yield ','
                firstline = False
                yield json.dumps(line.rstrip())
    finally:
        yield ']'

def copyfile(src_filename, dst_filename):
    BUFFER_SIZE = const(128)
    try:
        with open(src_filename, 'rb') as src_file:
            with open(dst_filename, 'wb') as dst_file:
                while True:
                    buf = src_file.read(BUFFER_SIZE)
                    if len(buf) > 0:
                        dst_file.write(buf)
                    if len(buf) < BUFFER_SIZE:
                        break
        return True
    except:
        return False

def about():
    return {
        'version': 1.0,
        'network': hasnetwork()
    }