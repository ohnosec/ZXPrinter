import sys, os
import json
import re
import fnmatch
import argparse
from datetime import datetime

scriptpath = os.path.abspath(os.path.dirname(sys.argv[0])) # type: ignore
basepath = f"{scriptpath}/src"

buildfile = "build.json"
envfile = "env.json"
distrofile = "files.json"
indexfile = "index.html"
definition = {
    "include": ["<>main.py", "env.json", "*.html", "*.css", "*.js", "*.svg", "*.ico", "*.woff", "<firmware/>*.py", "<firmware/>*.cap"],
    "exclude": [buildfile, distrofile, "font.js", "firmware/test*.py"]
}

buildtime = datetime.utcnow()
buildnumber = buildtime.strftime("%Y-%m-%d %H:%M:%S")
indexpath = f"{basepath}/{indexfile}"

# crc functions converted from here... (also used in firmware sd card)
# https://electronics.stackexchange.com/questions/321304/how-to-use-the-data-crc-of-sd-cards-in-spi-mode
crc16table = [0]*256
for byt in range(256):
    crc = byt << 8
    for bit in range(8):
        crc = crc << 1
        if (crc & 0x10000) != 0:
            crc ^= 0x1021
    crc16table[byt] = crc & 0xFFFF

def crc16byte(crcval, byte):
    return (crc16table[(byte ^ (crcval >> 8)) & 0xFF] ^ (crcval << 8)) & 0xFFFF

def getcrc16(filename, istext):
    crcval = 0x0000
    if istext:
        with open(f"{basepath}/{filename}", "r", encoding="utf-8") as f:
            for line in f:
                for char in line.rstrip("\r\n"):
                    crcval = crc16byte(crcval, ord(char))
    else:
        with open(f"{basepath}/{filename}", "rb") as filestream:
            while True:
                bytes = filestream.read(1)
                if not bytes:
                    break
                crcval = crc16byte(crcval, bytes[0])
    return crcval

def getattributes():
    textfiles = []
    with open(f"{scriptpath}/.gitattributes", "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            pattern = parts[0]
            attributes = set(parts[1:])

            if pattern == "*":
                continue

            if "text" in attributes or "text=auto" in attributes:
                textfiles.append(pattern)
            elif "binary" not in attributes:
                textfiles.append(pattern)
    return textfiles

gitattributes = getattributes()

def getchecksum(filename):
    justfilename = os.path.basename(filename) # type: ignore
    istext = any(a for a in gitattributes if fnmatch.fnmatch(justfilename, a))
    return getcrc16(filename, istext)

def findmatch(name, names):
    return next((n for n in names if fnmatch.fnmatch(name, n.replace("<", "").replace(">", ""))), None)

def getfiles():
    filepaths = []
    for (root, _, files) in os.walk(basepath):
        for file in files:
            path = root[len(basepath):]
            path = path.replace("\\", "/")
            if len(path) > 0:
                path += "/"
            if path.startswith("/"):
                path = path[1:]
            filepaths.append(f"{path}{file}")
    filepaths.sort()
    return filepaths

def getdistro(source, target, type, checksum):
    return {
        "source": source,
        "target": target,
        "type": type,
        "checksum": f"0x{checksum:04x}"
    }

def updatedistro():
    print(f"Update distro file '{distrofile}'")

    distros = []
    for file in getfiles():
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
            if len(file)>0:
                distros.append(getdistro(source, target, type, getchecksum(file)))
    distros.append(getdistro(distrofile, distrofile, "config", 0))
    with open(f"{basepath}/{distrofile}", "w") as distrostream:
        json.dump(distros, distrostream, indent=2) # type: ignore

def minifyfont(fontfilename):
    print(f"Minify font '{fontfilename}'")

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

def updateimportmap():
    print("Update index.html importmap")

    timestamp = buildtime.strftime("%Y%m%d%H%M%S")

    files = [file for file in os.listdir(f"{basepath}") if file.endswith(".js")]

    template = r'''
    <script type="importmap">
    {{
      "imports": {{
        {imports}
      }}
    }}
    </script>'''

    imports = ",\n        ".join([f'"./{file}": "./{file}?v={timestamp}"' for file in files])

    importmap = template.format(imports=imports.lstrip()).lstrip()

    with open(indexpath, "r", encoding="utf-8") as file:
        indexhtml = file.read()

    indexhtml = re.sub(r'<script type="importmap">[\s\S]*?</script>', importmap, indexhtml, flags=re.MULTILINE)

    with open(indexpath, "w", encoding="utf-8") as file:
        file.write(indexhtml)

def updateversion():
    print("Update index.html version and build number")

    with open(indexpath, "r", encoding="utf-8") as file:
        indexhtml = file.read()

    with open(f"{basepath}/{envfile}", "r") as envstream:
        env = json.load(envstream)

    indexhtml = indexhtml.replace("{{version}}", env["version"])
    indexhtml = indexhtml.replace("{{build}}", buildnumber)

    with open(indexpath, "w", encoding="utf-8") as file:
        file.write(indexhtml)

def updatebuildinfo():
    print(f"Update build file '{buildfile}'")

    build = {
        "number": buildnumber
    }
    with open(f"{basepath}/{buildfile}", "w") as buildstream:
        json.dump(build, buildstream, indent=2) # type: ignore

parser = argparse.ArgumentParser("build", description="Pico ZX Printer builder")
parser.add_argument("-im", action="store_true", help="add versioned importmap to index.html")
args = parser.parse_args()

updatebuildinfo()
updateversion()
if args.im:
    updateimportmap()
minifyfont("font.js")
updatedistro()
