import { execrequest, requests } from "./client.js"
import { logger as seriallogger } from "./serial.js"
import { Logger } from "./utils.js"

const LogTarget = Object.freeze({
    ZXPRINTER: 0,
    SERIAL: 1,
    CONSOLE: 2
});

let logtarget = LogTarget.ZXPRINTER;
let logintervalid = undefined;

const consolelogger = new Logger();
const consolelog = (type, ...args) => {
    consolelogger.log(`${type}: ${args.join(" ")}\n`);
}
const newconsolelog = (type, object, method) => {
    return (...args) => {
        consolelog(type, ...args);
        method.apply(object, args);
    }
}
window.console.log = newconsolelog('Log', window.console, window.console.log);
window.console.info = newconsolelog('Info', window.console, window.console.info);
window.console.warn = newconsolelog('Warn', window.console, window.console.warn);
window.console.error = newconsolelog('Error', window.console, window.console.error);

function showlog(checkbox) {
    const logs = document.getElementById('logmenu');
    if (checkbox.checked) {
        logs.classList.remove("d-none");
    } else {
        const logpage = document.getElementById("log");
        logpage.hidden = true;
        logs.classList.add("d-none");
    }
}

function startrefresh() {
    if (!logintervalid) {
        logintervalid = setInterval(() => refreshlog(false), 500);
    }
}

function stoprefresh() {
    if (logintervalid) {
        clearInterval(logintervalid);
        logintervalid = undefined;
    }
}

async function logzxprinter() {
    document.getElementById('logzxprinter').classList.add("active");
    document.getElementById('logserial').classList.remove("active");
    document.getElementById('logconsole').classList.remove("active");
    logtarget = LogTarget.ZXPRINTER;
    stoprefresh();
    refreshlog();
}

async function logserial() {
    document.getElementById('logzxprinter').classList.remove("active");
    document.getElementById('logserial').classList.add("active");
    document.getElementById('logconsole').classList.remove("active");
    logtarget = LogTarget.SERIAL;
    startrefresh();
    refreshlog();
}

async function logconsole() {
    document.getElementById('logzxprinter').classList.remove("active");
    document.getElementById('logserial').classList.remove("active");
    document.getElementById('logconsole').classList.add("active");
    logtarget = LogTarget.CONSOLE;
    stoprefresh();
    refreshlog();
}

function showlogmenu() {
    const galleryelement = document.getElementById('gallery');
    const logelement = document.getElementById('log');
    galleryelement.hidden = true;
    logelement.hidden = false;
}

async function refreshlog(showmenu=true) {
    if (showmenu) showlogmenu();
    const logtextelement = document.getElementById('logtext');
    let linetext;
    if (logtarget == LogTarget.ZXPRINTER) {
        const lines = await execrequest(requests.getlog);
        linetext = lines.join('\n');
    } else if (logtarget == LogTarget.SERIAL) {
        linetext = seriallogger.contents;
    } else {
        linetext = consolelogger.contents;
    }
    logtextelement.value = linetext;
    logtextelement.scrollTop = logtextelement.scrollHeight;
}

export {
    logzxprinter, logserial, logconsole,
    showlog, refreshlog
}