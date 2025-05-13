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
    WRITE: 2
});

let lastlogtype = LogType.UNKNOWN;

const logger = new Logger();
function log(type, message) {
    if (type != lastlogtype) {
        lastlogtype = type;
        if (type == LogType.READ) {
            logger.log("🡄 ");
        } else if (type == LogType.WRITE) {
            logger.log("🡆 ");
        }
    }
    logger.log(message.replace(/[\x00-\x1F]/g, m => {
        if (m == '\r' || m == '\n') return m;
        const asciicode = m.charCodeAt(0);
        const atcode = "@".charCodeAt(0);
        return "^"+String.fromCharCode(atcode+asciicode)
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
    readbuffer = "";

    isconnected = true;
    connecthandler.call(); // dont wait so the handler can do serial IO

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
    await port.forget();
    await port.close();
    isconnected = false;
    await disconnecthandler.call();
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
        if(char == undefined) return string;
        string += char;
        if(until!="" && string.endsWith(until)) return string;
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
