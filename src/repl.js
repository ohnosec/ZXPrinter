import { serial } from "./serial.js"
import { sleep } from "./utils.js"

const CTRLA = "\x01" // raw REPL
const CTRLB = "\x02" // normal REPL
const CTRLC = "\x03" // interrupt code
const CTRLD = "\x04" // soft reset

const ENTER = "\r"

const INTERRUPT = `${CTRLB}${ENTER}${CTRLC}${CTRLC}`;
const REPLENTER = "raw REPL; CTRL-B to exit\r\n>";
const REPLPROMPT = ">";
const REPLOK = "OK";
const REPLSUBMIT = CTRLD;
const REPLREBOOT = CTRLD;
const REPLNULLCMD = `${ENTER}${REPLSUBMIT}`;

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
    await expect(command, REPLPROMPT, "REPL not responding");
}

async function enter() {
    await serial.write(INTERRUPT);
    await sleep(10);
    await expect(CTRLA, REPLENTER, "Could not enter REPL");
}

async function exit() {
    await serial.write(CTRLB);
    await sleep(10);
    serial.flush();
}

async function reboot() {
    await exit();
    await serial.write(CTRLD);
}

async function reset() {
    await exec(REPLNULLCMD);
    await exec(REPLREBOOT);
    await sleep(10);
    serial.flush();
}

async function execute(command) {
    await exec(REPLNULLCMD);
    await serial.write(command);
    await expect(REPLSUBMIT, REPLOK, "REPL not OK");
}

async function execute_trim(command) {
    const lines = command.split(/\r?\n|\r|\n/g)
        .map(x => x.trim())
        .join("\r");
    await execute(lines);
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

export {
    enter,
    exit,
    reboot,
    reset,
    execute,
    put
}
