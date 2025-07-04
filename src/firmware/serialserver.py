import services
from command import command, start_server
import fileprinter

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

def storename(store):
    return store if store == fileprinter.SDSTORENAME else None

@command("getprintouts", "[store]")
async def getprintouts(params):
    return services.get_printouts(storename(params.get("store")))

@command("getprintout", "name", "[store]")
async def getprintout(params):
    return services.get_printout(storename(params.get("store")), params["name"])

@command("deleteprintout", "name", "[store]")
async def delprintout(params):
    return services.delete_printout(storename(params.get("store")), params["name"])

@command("printprintout", "name", "[store]")
async def printprintout(params):
    return services.print_printout(storename(params.get("store")), params["name"])

@command("copyprintout", "name", "fromstore", "tostore")
async def copyprintout(params):
    return services.copy_printout(storename(params["fromstore"]), storename(params["tostore"]), [params["name"]])

@command("joinprintout", "names", "fromstore", "tostore")
async def joinprintout(params):
    return services.copy_printout(storename(params["fromstore"]), storename(params["tostore"]), params["names"].split("+"))

@command("setprinter", "target")
async def setprinter(params):
    return services.setprintertarget(params["target"])

@command("setprinteraddress", "address")
async def setprinteraddress(params):
    return services.setprinteraddress(params["address"])

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
    return services.setprinterleftmargin(int(params["value"]))

@command("setdensity", "value")
async def setdensity(params):
    return services.setprinterdensity(int(params["value"]))

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

@command("cardinfo")
async def getcardinfo(_):
    return services.getcardinfo()

@command("about")
async def about(_):
    return services.about()

async def start():
    await start_server()