import os
import json
from micropython import const
from phew import server, logging
import parallelprinter
import serialprinter
import networkprinter
import fileprinter
import physicalprinter
import settings
import dnsclient
from system import hasnetwork

testprinterfilename = const("/testprintout.cap")

PRINTERTARGET       = const("printer:target")
PRINTERADDRESS      = const("printer:raw:address")
PRINTERPROTOCOL     = const("printer:raw:protocol")

OLDPRINTERTARGET    = const("printertarget")
OLDPRINTERADDRESS   = const("printeraddress")
OLDPRINTERPROTOCOL  = const("printerprotocol")

def initialise(p, sd):
    global connectedpixel
    global sdmanager

    connectedpixel = p
    sdmanager = sd

    migratesettings()

    setprinteraddress(getprinteraddress()["address"], False)
    setprintertarget(getprinter()["target"], False)

# move old flat settings into new hierarchical one
def migratesettings():
    if settings.getvalue(OLDPRINTERADDRESS) is not None:
        settings.setvalue(PRINTERTARGET, settings.getvalue(OLDPRINTERTARGET))
        settings.setvalue(PRINTERADDRESS, settings.getvalue(OLDPRINTERADDRESS))
        settings.setvalue(PRINTERPROTOCOL, settings.getvalue(OLDPRINTERPROTOCOL))
        settings.removevalue(OLDPRINTERTARGET)
        settings.removevalue(OLDPRINTERADDRESS)
        settings.removevalue(OLDPRINTERPROTOCOL)
        settings.save()

@micropython.native # type: ignore
async def get_printout(store, name):
    filename = fileprinter.getfilepath(store, name)
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

def get_printouts(store):
    return fileprinter.getfiles(store)

def delete_printout(store, name):
    filename = fileprinter.getfilepath(store, name)
    os.remove(filename)
    return {}

def print_printout(store, name):
    filename = fileprinter.getfilepath(store, name)
    server.loop.create_task(physicalprinter.printfile(filename))
    return {}

def copy_printout(sourcestore, targetstore, filenames):
    fromfilenames = [fileprinter.getfilepath(sourcestore, fn) for fn in filenames]
    tofilename = fileprinter.nextfilename(targetstore)
    fileprinter.savesettings(targetstore)
    logging.info(f"Copying from {fromfilenames} to {tofilename}")
    copyfile(fromfilenames, tofilename)
    return {}

def testprinter():
    logging.info(f"Printing a test page")
    server.loop.create_task(physicalprinter.printfile(testprinterfilename))
    return {}

async def findprinters(protocol):
    if protocol.lower() != "raw":
        raise ValueError(f"Protocol '{protocol}' not supported")
    logging.info(f"Finding {protocol} printers")
    responses = await dnsclient.query(dnsclient.PTRTYPE, "_pdl-datastream._tcp.local")
    addresses = []
    for response in responses:
        target = next((s["target"] for s in response["srv"]), None)
        txtty = next((t["value"] for t in response["txt"] if t["name"] == "ty"), None)
        txtpdl = next((t["value"] for t in response["txt"] if t["name"] == "pdl"), None)
        if target is None or txtty is None or txtpdl is None:
            logging.info(f"Found {protocol} printer but missing some details: {response}")
        else:
            logging.info(f"Found {protocol} printer '{txtty}' at '{target}' handling {txtpdl}")
            addresses.append({
                "address": target,
                "type": txtty,
                "pdl": txtpdl
            })
    return addresses

def setprintercapture(state):
    logging.info(f"Changing printer capture to {state}")
    state = state.lower()
    fileprinter.setcapture(state == "on")
    return {}

def setprinterendofline(char):
    logging.info(f"Changing printer end of line to {char}")
    char = char.lower()
    physicalprinter.setlinefeed(char == "crlf")
    return {}

def setprinterendofprint(char):
    logging.info(f"Changing printer end of print to {char}")
    char = char.lower()
    physicalprinter.setformfeed(char == "ff")
    return {}

def setprinterleftmargin(value):
    logging.info(f"Changing printer left margin to {value}")
    physicalprinter.setleftmargin(value)
    return {}

def setprinterdensity(value):
    logging.info(f"Changing printer density to {value}")
    physicalprinter.setdensity(value)
    return {}

def setprintertarget(target, save=True):
    logging.info(f"Changing printer to {target}")
    target = target.lower()
    if target == "off":
        physicalprinter.setenabled(False)
        target = None
    elif target == "serial":
        serialprinter.setactive()
    elif target == "parallel":
        parallelprinter.setactive()
    elif target == "network":
        networkprinter.setactive()
    if save:
        settings.setvalue(PRINTERTARGET, target)
        settings.save()
    protocol = settings.getvalue(PRINTERPROTOCOL)
    if protocol is not None:
        setprinterprotocol(protocol, save)
    return {}

def getprinter():
    target = settings.getvalue(PRINTERTARGET)
    return {
        "target": "off" if target is None else target
    }

def setprinteraddress(address, save=True):
    logging.info(f"Setting printer address to {address}")
    networkprinter.setaddress(address)
    if save:
        settings.setvalue(PRINTERADDRESS, address)
        settings.save()
    return {}

def getprinteraddress():
    return {
        "address": settings.getvalue(PRINTERADDRESS)
    }

def setprinterprotocol(protocol, save=True):
    logging.info(f"Setting printer protocol to {protocol}")
    protocol = protocol.lower()
    if protocol == "auto":
        target = settings.getvalue(PRINTERTARGET)
        if target == "serial":
            serialprinter.setdefaultprotocol()
        elif target == "parallel":
            parallelprinter.setdefaultprotocol()
        elif target == "network":
            networkprinter.setdefaultprotocol()
        protocol = None
    elif protocol == "escp":
        physicalprinter.setprotocolescp()
    elif protocol == "escpr":
        networkprinter.setprotocolescpr()
    if save:
        settings.setvalue(PRINTERPROTOCOL, protocol)
        settings.save()
    return {}

def getprinterprotocol():
    protocol = settings.getvalue(PRINTERPROTOCOL)
    return {
        "protocol": "auto" if protocol is None else protocol
    }

def setserialsettings(settings):
    logging.info(f"Setting serial to {settings}")
    serialprinter.setsettings(settings["baudrate"], settings["bits"], settings["parity"], settings["stop"])
    return {}

def setserialflow(hardware, software, delayms):
    logging.info(f"Setting serial flow control to hardware={hardware} software={software} delayms={delayms}")
    serialprinter.setflowcontrol(hardware, software, delayms)
    return {}

def getnetwork():
    return {
        "ssid": settings.getssid()
    }

async def sethostname(newhostname):
    import network

    if newhostname != network.hostname():
        logging.info(f"Setting hostname {newhostname}")
        settings.sethostname(newhostname)
        settings.save()
        network.hostname(newhostname)
    return {}

async def setnetwork(newssid, newpassword):
    settings.setssid(newssid)
    if newpassword is not None:
        settings.setpassword(newpassword)
    settings.save()
    return {}

def connect(newssid, newpassword):
    import network

    wlan = network.WLAN() # type: ignore
    ssid = settings.getssid()
    password = settings.getpassword()
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

    wlan = network.WLAN() # type: ignore
    connected = wlan.isconnected()
    rssi = wlan.status("rssi")
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
    macaddress = ':'.join([f"{b:02X}" for b in wlan.config("mac")])
    return {
        "state": state,
        "status": status,
        "rssi": rssi,
        "connected": connected,
        "connecting": state == network.STAT_CONNECTING,
        "hostname": network.hostname(),
        "ip": ipaddress,
        "mac": macaddress
    }

def scan():
    import network

    wlan = network.WLAN() # type: ignore
    networks = [{"ssid": net[0], "rssi": net[3]} for net in wlan.scan()]
    return networks

def readlogfile(filename):
    if not logging.file_exists(filename):
        return
    with open(filename) as filehandle:
        while True:
            line = filehandle.readline()
            if not line:
                return
            yield json.dumps(line.rstrip())

async def getlogfile():
    yield '['
    try:
        isfirstline = True
        for line in readlogfile(logging.log1_file):
            if not isfirstline:
                yield ','
            isfirstline = False
            yield line
        for line in readlogfile(logging.log_file):
            if not isfirstline:
                yield ','
            isfirstline = False
            yield line
    finally:
        yield ']'

def copyfile(fromfilenames, tofilename):
    BUFFER_SIZE = const(128)
    try:
        with open(tofilename, "wb") as dst_file:
            for fromfilename in fromfilenames:
                with open(fromfilename, "rb") as src_file:
                    while True:
                        buf = src_file.read(BUFFER_SIZE)
                        if len(buf) > 0:
                            dst_file.write(buf)
                        if len(buf) < BUFFER_SIZE:
                            break
        return True
    except:
        try:
            os.remove(tofilename)
        except:
            pass
        return False

def getcardinfo():
    ismounted = sdmanager.ismounted()
    return {
        "identifier": hex(sdmanager.card.CID)[2:] if ismounted else None,
        "details": sdmanager.card.decode_cid() if ismounted else None
    }

def about():
    return {
        "version": 1.0,
        "network": hasnetwork(),
        "sdcard": sdmanager.ismounted()
    }