import os
import time
import json
import re
from micropython import const
from phew import logging
from phew.server import file_exists
from packbits import PackBitsFile
from events import notifyevent

PRINTOUTFOLDER  = const('printout')
PRINTCONFIGFILE = const('prtconfig.json')

filenumber = 1
captureenabled = True
printpattern = re.compile(r"^prt(\d\d\d\d).packed.bin$")

def getfilename(number):
    return f'prt{number:04d}.packed.bin'

def getfullfilename(number):
    return f'{PRINTOUTFOLDER}/{getfilename(number)}'

def getfilepath(file):
    return f"{PRINTOUTFOLDER}/{file}"

def nextfilename():
    global filenumber
    filenumber += 1
    return getfullfilename(filenumber)

def getfiles():
    files = []
    for file in os.listdir(PRINTOUTFOLDER):
        if printpattern.match(file) and file_exists(f"{PRINTOUTFOLDER}/{file}"):
            files.append(file)
    return files

def savesettings():
    global filenumber

    logging.info('Saving print capture settings')
    with open(f"{PRINTOUTFOLDER}/{PRINTCONFIGFILE}", "wt") as fp:
        json.dump({ 'next': filenumber+1 }, fp)

def setcapture(state):
    global captureenabled

    captureenabled = state

def captureinit():
    global filenumber

    try:
        os.stat(PRINTOUTFOLDER)
    except:
        logging.info('Creating print folder')
        os.mkdir(PRINTOUTFOLDER)

    logging.info('Finding next print file')
    try:
        with open(f"{PRINTOUTFOLDER}/{PRINTCONFIGFILE}") as fp:
            settings = json.load(fp)
    except:
        settings = {}

    settinglast = int(settings.get('next') or '1')-1
    filelast = max([0]+[int(m.group(1)) for f in os.listdir(PRINTOUTFOLDER) for m in [printpattern.match(f)] if m is not None])
    maxlast = max(settinglast, filelast)

    filenumber = maxlast

    if maxlast != settinglast:
        savesettings()

    logging.info(f'Next print file is #{filenumber+1} "{getfullfilename(filenumber+1)}"')

async def capture(rows):
    captureinit()

    starttime = None
    filehandle = None
    logging.info('Waiting for printout to capture')
    while True:
        async for row in rows:
            if starttime is None:
                if not captureenabled:
                    continue
                starttime = time.ticks_ms()
            if filehandle is None:
                logging.info('Capture started')
                filehandle = PackBitsFile(nextfilename())
            for byte in row:
                filehandle.write(byte)
        if filehandle is not None:
            filehandle.close()
            filehandle = None
            await notifyevent('capture', getfilename(filenumber))
        if starttime is not None:
            printtime = time.ticks_diff(time.ticks_ms(), starttime)
            logging.info(f"Capture time: {printtime} ms")
            logging.info('Capture finished')
            savesettings()
            starttime = None