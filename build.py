import sys, os
import json
import re
import fnmatch

basepath = os.path.abspath(os.path.dirname(sys.argv[0]))
basepath += "/src"

definitions = [
    {
        "config": "config.json",
        "include": ["main.py", "config.json", "*.html", "*.css", "*.js", "*.svg", "*.ico", "*.woff"],
        "exclude": ["font.js"]
    },
    {
        "config": "firmware/config.json",
        "include": ["*.py"],
        "exclude": ["firmware/test*.py"]
    }
]

def minifyfont(fontfilename):
    linelength = 128

    filepath = os.path.normpath(os.path.join(basepath, fontfilename))
    (filefolder, filename) = os.path.split(filepath)
    (filenoext, fileext) = os.path.splitext(filename)
    fileminpath = os.path.normpath(os.path.join(filefolder, f"{filenoext}.min{fileext}"))

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

def matches(name, names):
    return len([n for n in names if fnmatch.fnmatch(name, n)]) > 0

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

    for definition in definitions:
        configfile = definition["config"]
        configpath = os.path.dirname(configfile)
        with open(f"{basepath}/{configfile}", "w") as configstream:
            filenames = []
            for file in allfiles:
                if matches(file, definition["include"]) and not matches(file, definition["exclude"]):
                    if len(configpath)>0:
                        file = file[len(configpath)+1:]
                    if len(file)>0:
                        filenames.append(file)
            config = { 'filenames': filenames }
            json.dump(config, configstream, indent=2) # type: ignore

minifyfont("font.js")
buildconfig()
