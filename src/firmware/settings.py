import json

SETTINGSFILE = const('/settings.json')

settings = {
    'hostname': 'zxprinter',
    'ssid': '',
    'password': ''
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

    with open(SETTINGSFILE, 'w') as fp:
        fp.write(json.dumps(settings))

def gethostname():
    global settings

    return settings['hostname']

def getssid():
    global settings

    return settings['ssid']

def getpassword():
    global settings

    return settings['password']

def sethostname(hostname):
    global settings

    settings['hostname'] = hostname

def setssid(ssid):
    global settings

    settings['ssid'] = ssid

def setpassword(password):
    global settings

    settings['password'] = password