import sys, os
import json
import re
import fnmatch

basepath = os.path.abspath(os.path.dirname(sys.argv[0])) # type: ignore
basepath += "/src"

configfile = "files.json"
definition = {
    "include": [configfile, "main.py", "*.html", "*.css", "*.js", "*.svg", "*.ico", "*.woff", "<firmware/>*.py"],
    "exclude": ["font.js", "firmware/test*.py"]
}

def minifyfont(fontfilename):
    linelength = 128

    filepath = os.path.normpath(os.path.join(basepath, fontfilename)) # type: ignore
    (filefolder, filename) = os.path.split(filepath) # type: ignore
    (filenoext, fileext) = os.path.splitext(filename) # type: ignore
    fileminpath = os.path.normpath(os.path.join(filefolder, f"{filenoext}.min{fileext}")) # type: ignore

    with open(filepath, "r") as fontfile:
        fontjs = fontfile.read()
        names = re.split(r"\W+", fontjs)
        shortname = names[1]
        fontpy = re.sub(r"^.*\[", r"[", fontjs).replace("//","#").replace("\n", "\\\n")
        fonts = eval(fontpy)
        flatfonts = [row for font in fonts for row in font]
        hexfonts = "".join(f"{i:02x}" for i in flatfonts)
        hexlines = [hexfonts[i:i+linelength] for i in range(0, len(hexfonts), linelength)]
        hexstrings = '[\n    "' + '",\n    "'.join(hexlines) + '"\n]'
        with open(fileminpath, "w") as minfile:
            minfile.write(f"const {shortname}=")
            minfile.write(hexstrings)

# crc converted from here, reused in firmware sd card
# https://electronics.stackexchange.com/questions/321304/how-to-use-the-data-crc-of-sd-cards-in-spi-mode
crc16table = [0]*256
for byt in range(256):
    crc = byt << 8
    for bit in range(8):
        crc = crc << 1
        if (crc & 0x10000) != 0:
            crc ^= 0x1021
    crc16table[byt] = crc & 0xFFFF

def sd_crc16_byte(crcval, byte):
    return (crc16table[(byte ^ (crcval >> 8)) & 0xFF] ^ (crcval << 8)) & 0xFFFF;

def getcrc16(filename):
    crcval = 0x0000
    with open(f"{basepath}/{filename}", "rb") as filestream:
        while True:
            bytes = filestream.read(1)
            if not bytes:
                break
            crcval = sd_crc16_byte(crcval, bytes[0])
    return crcval

def findmatch(name, names):
    return next((n for n in names if fnmatch.fnmatch(name, n.replace("<", "").replace(">", ""))), None)

def buildconfig():
    allfiles = []
    for (root, _, files) in os.walk(basepath):
        for file in files:
            path = root[len(basepath):]
            path = path.replace("\\", "/")
            if len(path) > 0:
                path += "/"
            if path.startswith("/"):
                path = path[1:]
            allfiles.append(f"{path}{file}")

    configpath = os.path.dirname(configfile) # type: ignore
    filenames = []
    for file in allfiles:
        include = findmatch(file, definition["include"])
        exclude = findmatch(file, definition["exclude"])
        if include and not exclude:
            source = file
            target = file
            type = "web"
            targetmatch = re.match(r"<.*>", include)
            if targetmatch:
                target = target[:targetmatch.start()]+target[targetmatch.end()-2:]
                type = "backend"
            if len(configpath)>0:
                file = file[len(configpath)+1:]
            if len(file)>0:
                filenames.append({
                    "source": source,
                    "target": target,
                    "type": type,
                    "checksum": f"0x{getcrc16(file):04x}"
                    })
    with open(f"{basepath}/{configfile}", "w") as configstream:
        json.dump(filenames, configstream, indent=2) # type: ignore

minifyfont("font.js")
buildconfig()
