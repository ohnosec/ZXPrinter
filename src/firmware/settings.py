import json
from micropython import const

SETTINGSFILE    = const("/settings.json")

HOSTNAME        = const("hostname")
SSID            = const("ssid")
PASSWORD        = const("password")
PRINTERADDRESS  = const("printeraddress")
PRINTERTARGET   = const("printertarget")
PRINTERPROTOCOL = const("printerprotocol")

settings = {
    HOSTNAME: "zxprinter",
    SSID: "",
    PASSWORD: "",
    PRINTERADDRESS: None,
    PRINTERTARGET: None,
    PRINTERPROTOCOL: None
}

def initialize():
    load()

def load():
    global settings

    try:
        with open(SETTINGSFILE) as fp:
            settings = json.load(fp)
    except:
        pass

def save():
    global settings

    with open(SETTINGSFILE, "w") as fp:
        fp.write(json.dumps(settings))

def gethostname():
    global settings

    return settings.get(HOSTNAME)

def getssid():
    global settings

    return settings.get(SSID)

def getpassword():
    global settings

    return settings.get(PASSWORD)

def getprinteraddress():
    global settings

    return settings.get(PRINTERADDRESS)

def getprintertarget():
    global settings

    return settings.get(PRINTERTARGET)

def getprinterprotocol():
    global settings

    return settings.get(PRINTERPROTOCOL)

def sethostname(hostname):
    global settings

    settings[HOSTNAME] = hostname

def setssid(ssid):
    global settings

    settings[SSID] = ssid

def setpassword(password):
    global settings

    settings[PASSWORD] = password

def setprinteraddress(address):
    global settings

    settings[PRINTERADDRESS] = address

def setprintertarget(target):
    global settings

    settings[PRINTERTARGET] = target

def setprinterprotocol(protocol):
    global settings

    settings[PRINTERPROTOCOL] = protocol