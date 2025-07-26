import json
import time
import asyncio
import network, ntptime
from phew import server, logging
from phew.server import redirect, Response, FileResponse
from phew.template import render_template
from system import logexception
import services
import settings
import fileprinter

class JsonResponse(Response):
    def __init__(self, body, content="application/json", status=200):
        if type(body).__name__ != "generator":
            body = json.dumps(body)
        super().__init__(body, status=status, headers={
            "Content-Type": content,
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "Content-Type, Accept",
            "Cache-Control": "no-cache"
        })

class BadRequest(Exception):
    pass

def addstaticroute(filename):
    # maxage = 120    # 2 minutes
    maxage = 10800  # 3 hours
    async def handler(_):
        return FileResponse(f"/{filename}", headers={"Cache-Control": f"max-age={maxage}"})
    server.add_route(f"/{filename}", handler)

def initialize(p):
    global connectedpixel
    global wlan

    connectedpixel = p

    with open("/files.json") as fp:
        files = json.load(fp)
        for file in files:
            filetype = file["type"]
            if filetype == "web" or filetype == "config":
                filename = file["target"]
                if filename != "local.js":
                    addstaticroute(filename)

    network.hostname(settings.gethostname())
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

@server.route("/local.js")
async def local(_):
    return JsonResponse(render_template("/local.js", local="true"), content="text/javascript")

def storename(store):
    return store if store == fileprinter.SDSTORENAME else None

@server.route("/printouts/<store>")
async def printouts(_, store):
    return JsonResponse(services.get_printouts(storename(store)))

@server.route("/printouts/<store>/<name>")
async def printout(_, store, name):
    return JsonResponse(services.get_printout(storename(store), name))

@server.route("/printouts/<store>/<name>", methods=["DELETE"])
async def printoutdel(_, store, name):
    return JsonResponse(services.delete_printout(storename(store), name))

@server.route("/printouts/<store>/<name>/printer", methods=["PUT", "POST"])
async def printoutprint(_, store, name):
    return JsonResponse(services.print_printout(storename(store), name))

@server.route("/printouts/<target_store>", methods=["POST"])
async def printoutcopy(request, target_store):
    target_parts = request.path.split("/")
    sources = request.data.get("source")
    if isinstance(sources, str):
        sources = [sources]
    if sources is None or len(sources) == 0:
        raise BadRequest("Missing source")
    source_names = []
    for source in sources:
        source_parts = source.split("/")
        if len(target_parts)<3 or len(source_parts)<4 or \
        target_parts[0]!="" or source_parts[0]!="" or \
        target_parts[1]!= source_parts[1]:
            raise BadRequest(f"Source '{source}' or target '{target_store}' is invalid")
        source_store = source_parts[2]
        source_names.append(source_parts[3])
    return JsonResponse(services.copy_printout(storename(source_store), storename(target_store), source_names))

@server.route("/printer/capture/<state>", methods=["PUT"])
async def setcapture(_, state):
    return JsonResponse(services.setprintercapture(state))

@server.route("/printer/endofline/<char>", methods=["PUT"])
async def setendofline(_, char):
    return JsonResponse(services.setprinterendofline(char))

@server.route("/printer/endofprint/<char>", methods=["PUT"])
async def setendofprint(_, char):
    return JsonResponse(services.setprinterendofprint(char))

@server.route("/printer/leftmargin/<value>", methods=["PUT"])
async def setleftmargin(_, value):
    return JsonResponse(services.setprinterleftmargin(int(value)))

@server.route("/printer/density/<value>", methods=["PUT"])
async def setdensity(_, value):
    return JsonResponse(services.setprinterdensity(int(value)))

@server.route("/printer/test", methods=["POST"])
async def testprinter(_):
    return JsonResponse(services.testprinter())

@server.route("/printer", methods=["GET"])
async def findprinters(request):
    protocol = request.query.get("protocol")
    print(f"protocol={protocol}")
    printers = await services.findprinters(protocol)
    return JsonResponse(printers)

@server.route("/printer/<target>", methods=["PUT"])
async def setprinter(_, target):
    return JsonResponse(services.setprintertarget(target))

@server.route("/printer/target", methods=["GET"])
async def getprinter(_):
    return JsonResponse(services.getprinter())

@server.route("/printer/serial/settings", methods=["PUT"])
async def setserial(request):
    return JsonResponse(services.setserialsettings(request.data))

@server.route("/printer/serial/flow", methods=["PUT"])
async def setserialflow(request):
    response = services.setserialflow(request.data["hardware"], request.data["software"], request.data["delayms"])
    return JsonResponse(response)

@server.route("/printer/network/address", methods=["GET"])
async def getprinteraddress(_):
    return JsonResponse(services.getprinteraddress())

@server.route("/printer/network/address/<value>", methods=["PUT"])
async def setprinteraddress(_, value):
    return JsonResponse(services.setprinteraddress(value))

@server.route("/printer/protocol", methods=["GET"])
async def getprinterprotocol(_):
    return JsonResponse(services.getprinterprotocol())

@server.route("/printer/protocol/<value>", methods=["PUT"])
async def setprinterprotocol(_, value):
    return JsonResponse(services.setprinterprotocol(value))

@server.route("/log")
async def getlog(_):
    return JsonResponse(services.getlogfile())

@server.route("/sd")
async def sdcard(_):
    return JsonResponse(services.getcardinfo())

@server.route("/about")
async def getcardinfo(_):
    return JsonResponse(services.about())

@server.catchall()
def catchall(request):
    if (request.method == "OPTIONS"):
        return JsonResponse({})
    contenttype = request.headers.get("content-type")
    if contenttype == "application/json":
        return JsonResponse({
            "error": "Endpoint not found"
        }, status=404)
    return redirect(f"http://{request.headers['host']}/index.html")

@server.exception()
def exception(request, ex):
    if type(ex) is BadRequest:
        status = 400
    else:
        status = 500
        logexception(ex)
    accepttype = request.headers.get("accept")
    if accepttype == "application/json":
        return JsonResponse({
            "error": str(ex)
        }, status=status)
    return Response(f"<html><body>Error: {str(ex)}</body></html>", status, headers={
        "Content-Type": "text/html"
        })

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