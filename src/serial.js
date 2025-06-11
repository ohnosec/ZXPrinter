import { sleep, Logger, Handler } from "./utils.js"
let port, reader, writer;
let isconnected = false;
const encoder = new TextEncoder();
const decoder = new TextDecoder();
const blocksize = 128;
let readbuffer = "";

const LogType = Object.freeze({
    UNKNOWN: 0,
    READ: 1,
    WRITE: 2,
    CONNECT: 3,
    DISCONNECT: 4
});

let lastlogtype = LogType.UNKNOWN;

const logger = new Logger();
let lastcr = false;
function log(type, message = "") {
    if (type != lastlogtype) {
        lastlogtype = type;
        if (type == LogType.READ || type === LogType.WRITE) {
            let logtext = type === LogType.READ ? "🡄" : "🡆";
            if (lastcr) logtext = `\n${logtext}`;
            logger.log(logtext);
            lastcr = false;
        } else if (type === LogType.CONNECT || type === LogType.DISCONNECT) {
            let logtext = type === LogType.CONNECT ? "🡇" : "🡅";
            if (!logger.isblankline()) logtext = `\n${logtext}`;
            logger.log(`${logtext}\n`);
            lastcr = false;
        }
    }
    if (message === "") return;
    logger.log(message.replace(/[\S\s]/g, char => {
        let logtext = char;
        const iscr = char === "\r";
        const islf = char === "\n";
        const extraline = lastcr ? "\n" : "";
        const charcode = char.charCodeAt(0);
        if (charcode > 0x1F) {
            logtext = extraline + logtext;
        } else {
            const ctrlcode = "@".charCodeAt(0);
            logtext = "^" + String.fromCharCode(ctrlcode+charcode);
            if (iscr || islf) {
                if ((iscr && lastcr) || islf) logtext += char;
            } else {
                logtext = extraline + logtext;
            }
        }
        lastcr = iscr;
        return logtext;
    }));
}

const connecthandler = new Handler();
const disconnecthandler = new Handler();
const readhandler = new Handler();

async function connect() {
    try {
        port = await navigator.serial.requestPort();
    } catch (error) {
        if (error.name != "NotFoundError") {
            throw new Error("Serial port selection failed", { cause: error });
        }
        return;
    }

    try {
        await port.open({ baudRate: 115200 });
    } catch (error) {
        throw new Error("Serial port open failed", { cause: error });
    }

    reader = port.readable.getReader();
    writer = port.writable.getWriter();
    flush();

    isconnected = true;
    connecthandler.call(); // dont wait so the handler can do serial IO
    log(LogType.CONNECT);

    try {
        while (true) {
            const { value, done } = await reader.read();
            if (done) {
                reader.releaseLock();
                break;
            }
            if (value) {
                const readstring = decoder.decode(value);
                await readhandler.call(readstring);
                readbuffer += readstring;
                log(LogType.READ, readstring);
            }
        }
    } catch (err) {
        console.error(`Unexpected serial disconnect: ${err}`)
    }
    reader.releaseLock();
    writer.releaseLock();
    await port.close();
    await port.forget();
    flush();
    isconnected = false;
    await disconnecthandler.call();
    log(LogType.DISCONNECT);
}

async function write(data) {
    log(LogType.WRITE, data);
    const bytes = encoder.encode(data);
    let offset = 0;
    while(offset < bytes.byteLength) {
        const block = bytes.slice(offset, offset + blocksize);
        await writer.write(block);
        offset += blocksize;
    }
}

async function disconnect() {
    await reader.cancel()
}

function flush() {
    readbuffer = "";
}

function available() {
    return readbuffer.length;
}

async function readstring(until="\n", timeoutms=0) {
    let string = "";
    while(true) {
        const char = await readchar(timeoutms);
        if (char == undefined) return string;
        string += char;
        if (until!="" && string.endsWith(until)) return string;
    }
}

async function readchar(timeoutms=0) {
    const timeout = Date.now() + timeoutms;
    while(available() == 0) {
        if (timeoutms>0 && Date.now() >= timeout) {
            return undefined;
        }
        await sleep(10);
    }
    const ch = readbuffer.substring(0, 1);
    readbuffer = readbuffer.substring(1);
    return ch;
}

export {
    connect,
    write,
    disconnect,
    readstring as read,
    flush,
    available,
    isconnected,
    connecthandler,
    disconnecthandler,
    readhandler,
    logger
}
