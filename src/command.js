import { Mutex, sleep, setbusystate } from "./utils.js"
import * as serial from "./serial.js"
import * as repl from "./repl.js"

const CTRLD = "\x04";
const ENTER = "\r";

const STATECOMMAND = ` ${CTRLD}${ENTER}`;

const State = Object.freeze({
    UNKNOWN: 0,
    RUNNING: 1,
    REPL: 2,
    RAWREPL: 3
});

const RESETSECONDS = 10;

const mutex = new Mutex();

async function getstate() {
    serial.flush();
    await serial.write(STATECOMMAND);
    let responsetext = await serial.read("", 100);
    if (responsetext.includes('"error"')) {
        return State.RUNNING;
    } else if (responsetext.includes(`OK${CTRLD}${CTRLD}`)) {
        return State.RAWREPL;
    } else if (responsetext.includes('>>>')) {
        return State.REPL;
    } else {
        return State.UNKNOWN;
    }
}

async function executerepl(replaction) {
    const release = await mutex.acquire();
    setbusystate(true);
    try {
        await repl.enter();
        await repl.reset();
        await replaction(repl);
    } catch (error) {
        throw new Error("Serial REPL failed", { cause: error });
    } finally {
        setbusystate(false);
        release();
    }
}

async function execute(command, params = [], timeout = 15000) {
    const release = await mutex.acquire();
    if (timeout>500) setbusystate(true);
    let responsetext;
    try {
        serial.flush();
        params = params.map(p => encodeURIComponent(p)).join(' ');
        const startTime = (new Date()).getTime();
        await serial.write(`${command} ${params}\r`);
        responsetext = await serial.read("\n", timeout);
        const responseMs = (new Date()).getTime() - startTime;
        console.log(`Command '${command}' took ${responseMs} ms`)
    } finally {
        if (timeout>500) setbusystate(false);
        release();
    }
    try {
        const objectindex = responsetext.indexOf("{");
        const arrayindex = responsetext.indexOf("[");
        if (objectindex == -1 && arrayindex == -1) {
            throw new Error("Serial command response missing");
        }
        responsetext = responsetext.substring(Math.min(objectindex, arrayindex));
        const response = JSON.parse(responsetext);
        if (response && response.error) {
            throw new Error("Serial command error");
        }
        return response;
    } catch(error) {
        throw new Error("Serial command failed", { cause: error });
    }
}

async function reboot() {
    const RETRYWAIT = 500;
    const RETRIES = (RESETSECONDS*1000)/RETRYWAIT;

    await repl.reboot();
    let state;
    for(let retry=0; retry<RETRIES; retry++) {
        state = await getstate();
        if (state == State.RUNNING) break;
        await sleep(RETRYWAIT);
    }
    if (state != State.RUNNING) {
        throw new Error("Command not ready");
    }
}

async function reset() {
    try {
        await executerepl(async (repl) => {
            const startTime = (new Date()).getTime();
            await reboot();
            const responseMs = (new Date()).getTime() - startTime;
            console.log(`Reset took ${responseMs} ms`)
        });
    } catch (error) {
        throw new Error("Serial reset failed", { cause: error });
    }
}

export {
    execute,
    executerepl,
    reset,
    reboot
}
