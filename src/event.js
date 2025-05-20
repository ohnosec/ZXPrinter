import * as serial from "./serial.js"
import { Handler } from "./utils.js"
import { ishttpallowed, hasaddress, gettargeturl } from "./client.js"

const EVENTDEDUPMS = 1000;
const EVENTPROCESSMS = 500;

const eventhandler = new Handler();
const eventtimes = new Map();
const eventqueue = [];

const connecthandler = new Handler();
const disconnecthandler = new Handler();

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

if (ishttpallowed() && hasaddress()) {
    const retrytime = 1000;
    const connect = () => {
        console.log("Websocket connecting");
        const targeturl = gettargeturl();
        const targetprotocol = targeturl.protocol === "http:" ? "ws:" : "wss:";
        const eventsocket = new WebSocket(`${targetprotocol}//${targeturl.hostname}/events`);
        eventsocket.onmessage = async event => {
            const data =  event.data;
            console.log(`Websocket event ${data}`);
            await queueevent(data);
        };
        eventsocket.onopen = () => {
            console.log("Websocket connected");
            connecthandler.call();
        };
        eventsocket.onclose = () => {
            console.log("Websocket disconnected");
            disconnecthandler.call();
            setTimeout(connect, retrytime);
        };
        eventsocket.onerror = () => {
            console.log("Websocket error");
        };
    };
    connect();
}

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
    connecthandler,
    disconnecthandler,
    eventhandler
}