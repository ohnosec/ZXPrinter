import * as serial from "./serial.js"
import { sleep } from "./utils.js"

const CTRLA = "\x01" // raw REPL
const CTRLB = "\x02" // normal REPL
const CTRLC = "\x03" // interrupt code
// in normal REPL soft reboot
// in raw REPL
// - by itself resets
// - with command enters
const CTRLD = "\x04"
const ENTER = "\r"

const INTERRUPT = CTRLC;
const REPL = CTRLB;
const REBOOT = CTRLD;
const STOP = `${REPL}${ENTER}${INTERRUPT}${INTERRUPT}`;

const RAWSTART = CTRLA;
const RAWSTARTED = "raw REPL; CTRL-B to exit\r\n>";
const RAWPROMPT = ">";
const RAWOK = "OK";
const RAWSUBMIT = CTRLD;
const RAWRESET = CTRLD;
const RAWNULL = `${ENTER}${RAWSUBMIT}`;

async function expect(data, expect, message=undefined) {
    serial.flush();
    await serial.write(data);
    //const response = await serial.read(expect, 100);
    const response = await serial.read(expect, 1000);
    if (!response.endsWith(expect)) {
        throw Error(message ?? `Failed read: Expected "${expect}"`);
    }
}

async function exec(command) {
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
    await exec(RAWNULL);
    await exec(RAWRESET);
    await sleep(10);
    serial.flush();
}

async function execute(command) {
    await exec(RAWNULL);
    await serial.write(command);
    await expect(RAWSUBMIT, RAWOK, "REPL not OK");
}

async function execute_trim(command) {
    let indent = 0;
    const lines = command.split(/\r?\n|\r|\n/g);
    const firstline = lines.findIndex((l) => l.search(/\w/) >= 0);
    if (firstline >= 0) {
        indent = lines[firstline].search(/\w/);
    }
    const text = lines
        .map(x => x.substring(indent).trimEnd())
        .join("\r");
    await execute(text);
}

async function put(filename, data) {
    const chunk_size = 128;
    const tempfilename = `${filename}.inprogress.tmp`;
    const filefolder = filename.split("/").slice(0,-1).join("/");

    if (typeof data === 'string' || data instanceof String) {
        const encoder = new TextEncoder('utf-8')
        data = new Uint8Array(Array.from(encoder.encode(data)))
    }

    const charcode = (x) => x.charCodeAt(0);
    const textchar = (x) => String.fromCharCode(x);
    const hexchar = (x) => x.toString(16).padStart(2, '0');
    const quote = charcode("'");
    const backslash = charcode("\\");
    const hexlify = (data) => Array.from(data)
        .map(x => hexchar(x))
        .join('');
    const bytelify = (data) => Array.from(data)
        .flatMap(x => x === quote || x === backslash ? [backslash,x] : x)
        .map(x => x >= 32 && x <= 126 ? textchar(x) : `\\x${hexchar(x)}`)
        .join('');

    await execute_trim(`
        import os
        import binascii
        h=binascii.unhexlify
        try: os.mkdir('${filefolder}')
        except: pass
        f=open('${tempfilename}','wb')
        wb=f.write
        wh=lambda d: f.write(h(d))
        c=lambda: f.close()
    `);

    for(let i = 0; i < data.length; i += chunk_size) {
        const chunk = data.slice(i, i + chunk_size);
        const hexchunk = hexlify(chunk);
        const bytechunk = bytelify(chunk);
        if (bytechunk.length < hexchunk.length) {
            await execute(`wb(b'${bytechunk}')\r`);
        } else {
            await execute(`wh('${hexchunk}')\r`);
        }
    }

    await execute_trim(`
        c()
        try: os.remove('${filename}')
        except: pass
        os.rename('${tempfilename}','${filename}')
    `);
}

async function removedir(directory, keep=[]) {
    const keeplist = keep.length === 0 ? "" : `'${keep.join("','")}'`
    await execute_trim(`
        import os
        def rd(dn, kfn):
            for fi in os.ilistdir(dn):
                fn, ft = fi[0:2]
                if fn in kfn:
                    continue
                fp = f'{dn}/{fn}'
                if ft == 0x8000:
                    os.remove(fp)
                else:
                    rd(fp, kfn)
                    os.rmdir(fp)
        rd('${directory}', (${keeplist}))
    `);
}

export {
    enter,
    exit,
    reboot,
    reset,
    execute,
    put,
    removedir
}
