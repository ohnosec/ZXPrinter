import services
from command import command, start_server

def initialize():
    pass

@command("sethostname", "hostname")
async def sethostname(params):
    return await services.sethostname(params["hostname"])

@command("getnetwork")
async def getnetwork(_):
    return services.getnetwork()

@command("setnetwork", "ssid", "[*password]")
async def setnetwork(params):
    return await services.setnetwork(params["ssid"], params.get("password"))

@command("connect", "[ssid]", "[*password]")
async def connect(params):
    return services.connect(params.get("ssid"), params.get("password"))

@command("status")
async def status(_):
    return services.status()

@command("scan")
async def scan(_):
    return services.scan()

@command("getprintouts")
async def getprintouts(_):
    return services.get_printouts()

@command("getprintout", "name")
async def getprintout(params):
    return services.render_printout(params["name"])

@command("deleteprintout", "name")
async def delprintout(params):
    return services.delete_printout(params["name"])

@command("printprintout", "name")
async def printprintout(params):
    return services.print_printout(params["name"])

@command("copyprintout", "name")
async def copyprintout(params):
    return services.copy_printout(params["name"])

@command("setstore", "name")
async def setstore(params):
    return services.setstorename(params["name"])

@command("setprinter", "target")
async def setprinter(params):
    return services.setprintertarget(params["target"])

@command("setcapture", "state")
async def setcapture(params):
    return services.setprintercapture(params["state"])

@command("setendofline", "char")
async def setendofline(params):
    return services.setprinterendofline(params["char"])

@command("setendofprint", "char")
async def setendofprint(params):
    return services.setprinterendofprint(params["char"])

@command("setleftmargin", "value")
async def setleftmargin(params):
    return services.setprinterleftmargin(params["value"])

@command("setdensity", "value")
async def setdensity(params):
    return services.setprinterdensity(params["value"])

@command("setserial", "baudrate", "bits", "parity", "stop")
async def setserial(params):
    return services.setserialsettings({
        'baudrate': int(params["baudrate"]),
        'bits': int(params["bits"]),
        'parity': params["parity"],
        'stop': int(params["stop"])
    })

@command("setflow", "hardware", "software", "delayms")
async def setflow(params):
    return services.setserialflow(params["hardware"] == "true", params["software"] == "true", int(params["delayms"]))

@command("getlog")
async def getlog(_):
    return services.getlogfile()

@command("about")
async def about(_):
    return services.about()

async def start():
    await start_server()