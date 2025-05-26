import * as serial from "./serial.js"
import * as websocket from "./websocket.js"
import { Handler } from "./utils.js"
import { ishttpallowed, hasaddress, gettargeturl } from "./client.js"

const EVENTDEDUPMS = 1000;
const EVENTPROCESSMS = 500;

const eventhandler = new Handler();
const eventtimes = new Map();
const eventqueue = [];

setInterval(async () => {
    if (eventqueue.length > 0) {
        const event = eventqueue.shift();
        console.log(`Handling event: ${JSON.stringify(event)}`);
        await eventhandler.call(event);
    }
}, EVENTPROCESSMS);

async function queueevent(data) {
    try {
        const response = JSON.parse(data);
        if (response.event) {
            const event = response.event;
            const lasttime = eventtimes.get(data);
            const nowtime = Date.now();
            if (lasttime) {
                if (nowtime-lasttime < EVENTDEDUPMS) return;
            }
            eventtimes.set(data, nowtime);
            eventqueue.push(event);
        }
    } catch {
        // ignore
    }
}


websocket.connecthandler.add(() => console.log("Websocket connected"));
websocket.disconnecthandler.add(() => console.log("Websocket disconnected"));
websocket.errorhandler.add(() => console.log("Websocket error"));
websocket.messagehandler.add(async (event) => {
    const data =  event.data;
    console.log(`Websocket event ${data}`);
    await queueevent(data);
});

function connect() {
    if (!ishttpallowed() || !hasaddress()) {
        websocket.disconnect();
        return;
    }
    console.log("Websocket connecting");
    const targeturl = gettargeturl();
    const targetprotocol = targeturl.protocol === "http:" ? "ws:" : "wss:";
    websocket.connect(`${targetprotocol}//${targeturl.hostname}/events`);
}

connect();

const SERIALFLUSHMS = 500;

let readline = "";
let readflush = true;

serial.connecthandler.add(async () => {
    readline = "";
    readflush = true;
    setTimeout(() => {
        readflush = false;
    }, SERIALFLUSHMS);
});

serial.readhandler.add(async (readstring) => {
    if (readflush) return;
    for(const readchar of readstring) {
        if (readchar == '\n') {
            try {
                const response = JSON.parse(readline);
                if (response.event) {
                    console.log(`Serial event ${readline}`);
                    await queueevent(readline);
                }
            } catch(error) {
                // ignore
            }
            readline = "";
        } else {
            readline += readchar;
        }
    }
});

export {
    eventhandler,
    connect
}