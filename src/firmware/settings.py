import json
from micropython import const

SETTINGSFILE    = const("/settings.json")

HOSTNAME        = const("hostname")
SSID            = const("ssid")
PASSWORD        = const("password")

settings = {}

def getvalue(key, default=None):
    keys = key.split(':')
    setting = settings
    for k in keys:
        if not isinstance(setting, dict) or k not in setting:
            return default
        setting = setting[k]

    value = setting
    return value

def _findsetting(key, create=False):
    keys = key.split(":")
    setting = settings

    for k in keys[:-1]:
        if k not in setting:
            if create:
                setting[k] = {}
            else:
                raise KeyError(f"Path for key '{key}' not found")
        elif not isinstance(setting[k], dict):
            raise TypeError(f"Cannot access key '{key}'. '{k}' is not a dictionary")
        setting = setting[k]

    lastkey = keys[-1]
    return setting, lastkey

def setvalue(key, value):
    setting, settingkey = _findsetting(key, create=True)
    setting[settingkey] = value

def removevalue(key):
    try:
        setting, settingkey = _findsetting(key, create=False)
        if settingkey in setting:
            del setting[settingkey]
    except KeyError:
        pass

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
    with open(SETTINGSFILE, "w") as fp:
        fp.write(json.dumps(settings))

def gethostname():
    return getvalue(HOSTNAME, "zxprinter")

def getssid():
    return getvalue(SSID, "")

def getpassword():
    return getvalue(PASSWORD, "")

def sethostname(hostname):
    setvalue(HOSTNAME, hostname)

def setssid(ssid):
    setvalue(SSID, ssid)

def setpassword(password):
    setvalue(PASSWORD, password)
