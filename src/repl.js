import * as serial from "./serial.js"
import { sleep } from "./utils.js"

const decoder = new TextDecoder("utf-8", { fatal: true });
const encoder = new TextEncoder("utf-8");

const CTRLA = "\x01" // raw REPL
const CTRLB = "\x02" // normal REPL
const CTRLC = "\x03" // interrupt code
// in normal REPL soft reboot
// in raw REPL
// - by itself resets
// - with command enters
const CTRLD = "\x04"
const ENTER = "\r"

// commands
const INTERRUPT = CTRLC;
const REPL = CTRLB;
const REBOOT = CTRLD;
const STOP = `${REPL}${ENTER}${INTERRUPT}${INTERRUPT}`;

const RAWSTART = CTRLA;
const RAWRESET = CTRLD;
const RAWSUBMIT = CTRLD;
const RAWNULL = `${ENTER}${RAWSUBMIT}`;

// responses
const RAWSTARTED = "raw REPL; CTRL-B to exit\r\n>";
const RAWPROMPT = ">";
const RAWACCEPTED = "OK";
const RAWENDOUTPUT = CTRLD;
const RAWENDCOMMAND = `${CTRLD}${RAWPROMPT}`;

class CommandError extends Error {
    constructor(message, exception, ...params) {
        super(...params);

        this.name = "REPLException";
        this.message = message;
        this.exception = exception;
    }
}

async function waitfor(expect, message=undefined, timeout=1000) {
    const response = await serial.read(expect, timeout);
    if (!response.endsWith(expect)) {
        throw Error(message ?? `REPL read failed, expected '${expect}'`);
    }
    return response.slice(0, response.length-expect.length);
}

async function expect(command, expect, message=undefined) {
    serial.flush();
    await serial.write(command);
    return waitfor(expect, message);
}

async function send(command) {
    await expect(command, RAWPROMPT, "REPL not responding");
}

async function enter() {
    await serial.write(STOP);
    await sleep(10);
    await expect(RAWSTART, RAWSTARTED, "Could not enter REPL");
}

async function exit() {
    await serial.write(REPL);
    await sleep(10);
    serial.flush();
}

async function reboot() {
    await exit();
    await serial.write(REBOOT);
}

async function reset() {
    await send(RAWNULL);
    await send(RAWRESET);
    await sleep(10);
    serial.flush();
}

async function execute(command) {
    await send(RAWNULL);
    await serial.write(command);
    await expect(RAWSUBMIT, RAWACCEPTED, "REPL not OK", 100);
    const output = await waitfor(RAWENDOUTPUT, "REPL missing output", 800);
    const exception = await waitfor(RAWENDCOMMAND, "REPL missing exception", 100);
    if (exception) {
        throw new CommandError("REPL command failed", exception);
    }
    return output;
}

async function executelines(command) {
    const indexofword = (s) => s.search(/\w/);
    const lines = command.split(/\r?\n|\r|\n/g);
    const firstline = lines.findIndex((l) => indexofword(l) >= 0);
    let indent;
    if (firstline >= 0) {
        indent = indexofword(lines[firstline]);
    } else {
        firstline = 0;
        indent = 0;
    }
    const text = lines
        .slice(firstline)
        .map((x) => x.substring(indent).trimEnd())
        .join("\r");
    return await execute(text);
}

async function put(filename, data) {
    const chunk_size = 128;
    const tempfilename = `${filename}.inprogress.tmp`;
    const filefolder = filename.split("/").slice(0,-1).join("/");

    if (typeof data === "string" || data instanceof String) {
        data = new Uint8Array(Array.from(encoder.encode(data)));
    }

    const charcode = (x) => x.charCodeAt(0);
    const textchar = (x) => String.fromCharCode(x);
    const hexchar = (x) => x.toString(16).padStart(2, "0");
    const quote = charcode("\"");
    const backslash = charcode("\\");
    const hexlify = (data) => Array.from(data)
        .map((x) => hexchar(x))
        .join("");
    const bytelify = (data) => Array.from(data)
        .flatMap((x) => x === quote || x === backslash ? [backslash,x] : x)
        .map((x) => x >= 32 && x <= 126 ? textchar(x) : `\\x${hexchar(x)}`)
        .join("");

    await executelines(`
        import os
        import binascii
        h=binascii.unhexlify
        try: os.mkdir("${filefolder}")
        except: pass
        f=open("${tempfilename}","wb")
        wb=f.write
        wh=lambda d: f.write(h(d))
        c=lambda: f.close()
    `);

    for(let i = 0; i < data.length; i += chunk_size) {
        const chunk = data.slice(i, i + chunk_size);
        const hexchunk = hexlify(chunk);
        const bytechunk = bytelify(chunk);
        if (bytechunk.length < hexchunk.length) {
            await execute(`wb(b"${bytechunk}")\r`);
        } else {
            await execute(`wh("${hexchunk}")\r`);
        }
    }

    await executelines(`
        c()
        try: os.remove("${filename}")
        except: pass
        os.rename("${tempfilename}","${filename}")
    `);
}

async function getbinary(filename) {
    try {
        const response = await executelines(`
            import binascii
            h=lambda b: binascii.hexlify(b).decode()
            with open("${filename}", "rb") as f:
                while 1:
                    b = f.read(64)
                    if not b: break
                    print(h(b),end="")
        `);
        return response.length
            ? new Uint8Array(response.match(/../g).map(h=>parseInt(h,16)))
            : new Uint8Array();
    } catch (error) {
        if (error instanceof CommandError) {
            if (error.exception.includes("OSError:") && error.exception.includes("ENOENT")) {
                return null;
            }
        }
        throw error;
    }
}

async function gettext(filename) {
    const data = await getbinary(filename);
    return data !== null ? decoder.decode(data) : null;
}

async function removedir(directory, keep=[]) {
    const keeplist = keep.length === 0 ? "" : `"${keep.join('","')}"`
    await executelines(`
        import os
        def rd(dn, kfn):
            for fi in os.ilistdir(dn):
                fn, ft = fi[0:2]
                if fn in kfn:
                    continue
                fp = f"{dn}/{fn}"
                if ft == 0x8000:
                    os.remove(fp)
                else:
                    rd(fp, kfn)
                    os.rmdir(fp)
        rd("${directory}", (${keeplist}))
    `);
}

async function hasnetwork() {
    const response = await executelines(`
        try:
            import network
            print(hasattr(network, "WLAN"))
        except:
            print(False)
    `);
    return response.trim() === "True";
}

export {
    enter,
    exit,
    reboot,
    reset,
    execute,
    put,
    getbinary,
    gettext,
    removedir,
    hasnetwork
}
