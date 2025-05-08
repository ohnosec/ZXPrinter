import json
import time
import asyncio
import network, ntptime
from phew import server, logging
from phew.server import redirect, Response, FileResponse
from phew.template import render_template
import services
import secretsmanager

class JsonResponse(Response):
    def __init__(self, body, content='application/json'):
        if type(body).__name__ != "generator":
            body = json.dumps(body)
        super().__init__(body, headers={
            'Content-Type': content,
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*',
            'Access-Control-Allow-Headers': 'Content-Type, Accept',
            'Cache-Control': 'no-store'
        })

def addstaticroute(filename):
    # handler = lambda _: FileResponse(f"/{filename}", headers={'Cache-Control': 'max-age=120'}) # 2 minutes
    handler = lambda _: FileResponse(f"/{filename}", headers={'Cache-Control': 'max-age=10800'}) # 3 hours
    server.add_route(f"/{filename}", handler)

def initialize(p):
    global connectedpixel
    global wlan

    connectedpixel = p

    with open("/config.json") as fp:
        config = json.load(fp)
        for filename in config['filenames']:
            if filename != "local.js":
                addstaticroute(filename)

    network.hostname(secretsmanager.gethostname())
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

@server.route("/local.js")
def local(_):
    return JsonResponse(render_template("/local.js", local="true"), content="text/javascript")

@server.route("/printouts")
def printouts(_):
    return JsonResponse(services.get_printouts())

@server.route("/printouts/<file>")
def printout(_, file):
    return JsonResponse(services.render_printout(file))

@server.route("/printouts/<file>", methods=['DELETE'])
def printoutdel(_, file):
    services.delete_printout(file)
    return JsonResponse({})

@server.route("/printouts/<file>/print", methods=['POST'])
def printoutprint(_, file):
    services.print_printout(file)
    return JsonResponse({})

@server.route("/printouts/<file>/copy", methods=['POST'])
def printoutcopy(_, file):
    services.copy_printout(file)
    return JsonResponse({})

@server.route("/store/<name>", methods=['POST'])
def setstore(_, name):
    services.setstorename(name)
    return JsonResponse({})

@server.route("/printer/capture/<state>", methods=['POST'])
def setcapture(_, state):
    services.setprintercapture(state)
    return JsonResponse({})

@server.route("/printer/endofline/<char>", methods=['POST'])
def setendofline(_, char):
    services.setprinterendofline(char)
    return JsonResponse({})

@server.route("/printer/endofprint/<char>", methods=['POST'])
def setendofprint(_, char):
    services.setprinterendofprint(char)
    return JsonResponse({})

@server.route("/printer/leftmargin/<value>", methods=['POST'])
def setleftmargin(_, value):
    services.setprinterleftmargin(int(value))
    return JsonResponse({})

@server.route("/printer/density/<value>", methods=['POST'])
def setdensity(_, value):
    services.setprinterdensity(int(value))
    return JsonResponse({})

@server.route("/printer/<target>", methods=['POST'])
def setprinter(_, target):
    services.setprintertarget(target)
    return JsonResponse({})

@server.route("/printer/serial/settings", methods=['POST'])
def setserial(request):
    services.setserialsettings(request.data)
    return JsonResponse({})

@server.route("/printer/serial/flow", methods=['POST'])
def setserialflow(request):
    services.setserialflow(request.data['hardware'], request.data['software'], request.data['delayms'])
    return JsonResponse({})

@server.route("/log")
def getlog(_):
    return JsonResponse(services.getlogfile())

@server.route("/about")
def about(_):
    return JsonResponse(services.about())

@server.catchall()
def catchall(request):
    if (request.method == 'OPTIONS'):
        return JsonResponse({})
    return redirect(f"http://{request.headers['host']}/index.html")

# async version of phew's connect_to_wifi
async def connect_to_wifi(ssid, password, timeout_seconds=15):
    if wlan.isconnected():
        logging.info("Disconnecting from wifi")
        wlan.disconnect()
        while wlan.isconnected():
            await asyncio.sleep_ms(250) # type: ignore

    logging.info("Connecting to wifi")
    wlan.connect(ssid, password)

    timeout_ms = timeout_seconds * 1000
    start = time.ticks_ms()
    while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
        await asyncio.sleep_ms(250) # type: ignore

    return wlan.ifconfig()[0] if wlan.status()==network.STAT_GOT_IP else ""

async def start():
    server.create_task()
    try:
        ipaddress = await connect_to_wifi(secretsmanager.getssid(), secretsmanager.getpassword())
        if ipaddress:
            try:
                ntptime.settime()
            except:
                logging.error(f"Failed to get time from time server")
            logging.info(f"Connected to wifi on {ipaddress}")
            connectedpixel.on()
            return
    except:
        pass
    logging.info(f"Connection to wifi failed")
    connectedpixel.off()
    await asyncio.sleep_ms(1000) # type: ignore
    connectedpixel.flash(200, 200, retrigger=True)