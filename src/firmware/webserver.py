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
    def __init__(self, body, content='application/json', status=200):
        if type(body).__name__ != "generator":
            body = json.dumps(body)
        super().__init__(body, status=status, headers={
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
    return JsonResponse(services.delete_printout(file))

@server.route("/printouts/<file>/print", methods=['POST'])
def printoutprint(_, file):
    return JsonResponse(services.print_printout(file))

@server.route("/printouts/<file>/copy", methods=['POST'])
def printoutcopy(_, file):
    return JsonResponse(services.copy_printout(file))

@server.route("/store/<name>", methods=['POST'])
def setstore(_, name):
    return JsonResponse(services.setstorename(name))

@server.route("/printer/capture/<state>", methods=['POST'])
def setcapture(_, state):
    return JsonResponse(services.setprintercapture(state))

@server.route("/printer/endofline/<char>", methods=['POST'])
def setendofline(_, char):
    return JsonResponse(services.setprinterendofline(char))

@server.route("/printer/endofprint/<char>", methods=['POST'])
def setendofprint(_, char):
    return JsonResponse(services.setprinterendofprint(char))

@server.route("/printer/leftmargin/<value>", methods=['POST'])
def setleftmargin(_, value):
    return JsonResponse(services.setprinterleftmargin(int(value)))

@server.route("/printer/density/<value>", methods=['POST'])
def setdensity(_, value):
    return JsonResponse(services.setprinterdensity(int(value)))

@server.route("/printer/<target>", methods=['POST'])
def setprinter(_, target):
    return JsonResponse(services.setprintertarget(target))

@server.route("/printer/serial/settings", methods=['POST'])
def setserial(request):
    return JsonResponse(services.setserialsettings(request.data))

@server.route("/printer/serial/flow", methods=['POST'])
def setserialflow(request):
    response = services.setserialflow(request.data['hardware'], request.data['software'], request.data['delayms'])
    return JsonResponse(response)

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

@server.exception()
def exception(_, ex):
    return JsonResponse({
        "error": "Request failed",
        "cause": str(ex)
    }, status=500)

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