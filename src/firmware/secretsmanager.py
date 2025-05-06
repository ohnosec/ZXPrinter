import json

SECRETSFILE = const('/secrets.json')

secrets = {
    'hostname': 'zxprinter',
    'ssid': '',
    'password': ''
}

def loadsecrets():
    global secrets

    try:
        with open(SECRETSFILE) as fp:
            secrets = json.load(fp)
    except:
        pass

def savesecrets():
    global secrets

    with open(SECRETSFILE, 'w') as fp:
        fp.write(json.dumps(secrets))

def initialize():
    loadsecrets()

def gethostname():
    global secrets

    return secrets['hostname']

def getssid():
    global secrets

    return secrets['ssid']

def getpassword():
    global secrets

    return secrets['password']

def sethostname(hostname):
    global secrets

    secrets['hostname'] = hostname

def setssid(ssid):
    global secrets

    secrets['ssid'] = ssid

def setpassword(password):
    global secrets

    secrets['password'] = password