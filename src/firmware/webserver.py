import json
import time
import asyncio
import network, ntptime
from phew import server, logging
from phew.server import redirect, Response, FileResponse
from phew.template import render_template
import services
import settings
import fileprinter

class JsonResponse(Response):
    def __init__(self, body, content='application/json', status=200):
        if type(body).__name__ != "generator":
            body = json.dumps(body)
        super().__init__(body, status=status, headers={
            'Content-Type': content,
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*',
            'Access-Control-Allow-Headers': 'Content-Type, Accept',
            'Cache-Control': 'no-cache'
        })

def addstaticroute(filename):
    # maxage = 120    # 2 minutes
    maxage = 10800  # 3 hours
    handler = lambda _: FileResponse(f"/{filename}", headers={'Cache-Control': f'max-age={maxage}'})
    server.add_route(f"/{filename}", handler)

def initialize(p):
    global connectedpixel
    global wlan

    connectedpixel = p

    with open("/files.json") as fp:
        files = json.load(fp)
        for file in files:
            if file["type"] == "web":
                filename = file["target"]
                if filename != "local.js":
                    addstaticroute(filename)

    network.hostname(settings.gethostname())
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

@server.route("/local.js")
def local(_):
    return JsonResponse(render_template("/local.js", local="true"), content="text/javascript")

def storename(store):
    return store if store == fileprinter.SDSTORENAME else None

@server.route("/printouts/<store>")
def printouts(_, store):
    return JsonResponse(services.get_printouts(storename(store)))

@server.route("/printouts/<store>/<name>")
def printout(_, store, name):
    return JsonResponse(services.get_printout(storename(store), name))

@server.route("/printouts/<store>/<name>", methods=['DELETE'])
def printoutdel(_, store, name):
    return JsonResponse(services.delete_printout(storename(store), name))

@server.route("/printouts/<store>/<file>/printer", methods=['PUT'])
def printoutprint(_, store, name):
    return JsonResponse(services.print_printout(storename(store), name))

@server.route("/printouts/<target_store>", methods=['POST'])
def printoutcopy(request, target_store):
    target_parts = request.path.split("/")
    source_parts = request.data["source"].split("/")
    if len(target_parts)<3 or len(source_parts)<4 or \
       target_parts[0]!="" or source_parts[0]!="" or \
       target_parts[1]!= source_parts[1]:
        raise Exception("bad request")
    source_store = source_parts[2]
    name = source_parts[3]
    return JsonResponse(services.copy_printout(storename(source_store), storename(target_store), name))

@server.route("/printer/capture/<state>", methods=['PUT'])
def setcapture(_, state):
    return JsonResponse(services.setprintercapture(state))

@server.route("/printer/endofline/<char>", methods=['PUT'])
def setendofline(_, char):
    return JsonResponse(services.setprinterendofline(char))

@server.route("/printer/endofprint/<char>", methods=['PUT'])
def setendofprint(_, char):
    return JsonResponse(services.setprinterendofprint(char))

@server.route("/printer/leftmargin/<value>", methods=['PUT'])
def setleftmargin(_, value):
    return JsonResponse(services.setprinterleftmargin(int(value)))

@server.route("/printer/density/<value>", methods=['PUT'])
def setdensity(_, value):
    return JsonResponse(services.setprinterdensity(int(value)))

@server.route("/printer/<target>", methods=['PUT'])
def setprinter(_, target):
    return JsonResponse(services.setprintertarget(target))

@server.route("/printer/serial/settings", methods=['PUT'])
def setserial(request):
    return JsonResponse(services.setserialsettings(request.data))

@server.route("/printer/serial/flow", methods=['PUT'])
def setserialflow(request):
    response = services.setserialflow(request.data['hardware'], request.data['software'], request.data['delayms'])
    return JsonResponse(response)

@server.route("/log")
def getlog(_):
    return JsonResponse(services.getlogfile())

@server.route("/sd")
def sdcard(_):
    return JsonResponse(services.getcardinfo())

@server.route("/about")
def getcardinfo(_):
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
        ipaddress = await connect_to_wifi(settings.getssid(), settings.getpassword())
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