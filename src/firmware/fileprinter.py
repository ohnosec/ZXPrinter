import os
import time
import json
import re
from micropython import const
from phew import logging
from phew.server import file_exists
from packbits import PackBitsFile
from event import notifyevent
from sdmanager import SDManager

PRINTOUTFOLDER  = const("printout")
PRINTCONFIGFILE = const("prtconfig.json")

SDSTORENAME = const("sd")

filenumbers = {}
captureenabled = True
printpattern = re.compile(r"^prt(\d\d\d\d\d\d).cap$") # type: ignore

def initialise(s: SDManager):
    global sd
    sd = s
    sd.addhandler(storehandler)

async def storehandler(hascard):
    if hascard:
        storeinit(SDSTORENAME)
    else:
        del filenumbers[SDSTORENAME]

def getrootpath(store):
    return sd.mount_point if store == SDSTORENAME else ""

def getfilename(number):
    return f"prt{number:06d}.cap"

def getstorepath(store):
    return f"{getrootpath(store)}/{PRINTOUTFOLDER}"

def getfilepath(store, name):
    storepath = getstorepath(store)
    return f"{storepath}/{name}"

def getfullfilename(store, number):
    return getfilepath(store, getfilename(number))

def getfilenumber(store):
    global filenumbers
    filenumber = filenumbers.get(store)
    if filenumber is None:
        raise Exception("File store not ready")
    return filenumber

def nextfilename(store):
    filenumber = getfilenumber(store)
    filenumbers[store] = filenumber+1
    return getfullfilename(store, filenumber)

def getfiles(store):
    files = []
    storepath = getstorepath(store)
    for file in os.listdir(storepath):
        if printpattern.match(file) and file_exists(f"{storepath}/{file}"):
            files.append(file)
    return files

def savesettings(store):
    logging.info("Saving print capture settings")
    storepath = getstorepath(store)
    with open(f"{storepath}/{PRINTCONFIGFILE}", "wt") as fp:
        json.dump({ "next": getfilenumber(store)+1 }, fp)

def setcapture(state):
    global captureenabled

    captureenabled = state

def storeinit(store):
    global filenumbers

    storepath = getstorepath(store)
    try:
        os.stat(storepath)
    except:
        logging.info("Creating print folder")
        os.mkdir(storepath)

    logging.info("Finding next print file")
    try:
        with open(f"{storepath}/{PRINTCONFIGFILE}") as fp:
            settings = json.load(fp)
    except:
        settings = {}

    settinglast = int(settings.get("next") or "1")-1
    filelast = max([0]+[int(m.group(1)) for f in os.listdir(storepath) for m in [printpattern.match(f)] if m is not None])
    maxlast = max(settinglast, filelast)

    filenumber = maxlast

    if maxlast != settinglast:
        savesettings(store)

    filenumbers[store] = filenumber

    logging.info(f"Next print file is #{filenumber+1} '{getfullfilename(store, filenumber+1)}'")

async def capture(rows):
    storeinit(None)

    starttime = None
    filehandle = None
    logging.info("Waiting for printout to capture")
    while True:
        async for row in rows:
            if starttime is None:
                if not captureenabled:
                    continue
                starttime = time.ticks_ms()
            if filehandle is None:
                logging.info("Capture started")
                filehandle = PackBitsFile(nextfilename(None))
            for byte in row:
                filehandle.write(byte)
        if filehandle is not None:
            filehandle.close()
            filehandle = None
            await notifyevent("capture", getfilename(getfilenumber(None)))
        if starttime is not None:
            printtime = time.ticks_diff(time.ticks_ms(), starttime)
            logging.info(f"Capture time: {printtime} ms")
            logging.info("Capture finished")
            savesettings(None)
            starttime = None