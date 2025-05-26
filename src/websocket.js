import { Handler } from "./utils.js"

let targeturl = null;
let websocket = null;
let isconnected = false;
let retryms = 1000;

let connecthandler = new Handler();
let messagehandler = new Handler();
let errorhandler = new Handler();
let disconnecthandler = new Handler();

function connect(url) {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        if (targeturl === url) return;
        disconnect();
    }

    targeturl = url;
    try {
        isconnected = false;
        websocket = new WebSocket(targeturl);

        websocket.onopen = async (event) => {
            isconnected = true;
            await connecthandler.call(event);
        };

        websocket.onmessage = async (event) => {
            await messagehandler.call(event);
        };

        websocket.onerror = async (event) => {
            await errorhandler.call(event);
        };

        websocket.onclose = async (event) => {
            isconnected = false;
            await disconnecthandler.call(event);
            retry();
        }
    } catch (error) {
        console.error("Failed to create WebSocket:", error);
        retry();
    }
}

function retry() {
    if (targeturl) {
        setTimeout(() => connect(targeturl), retryms);
    }
}

function send(data) {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(data);
    } else {
        console.log("WebSocket send failed, WebSocket is not connected");
    }
}

function disconnect(code=1000, reason=1000) {
    targeturl = "";
    if (websocket) {
        websocket.close(code, reason);
        websocket = null;
        isconnected = false;
    }
}

function getstate() {
    return websocket ? websocket.readyState : WebSocket.CLOSED;
}

export {
    connect,
    send,
    disconnect,
    getstate,
    isconnected,
    connecthandler,
    messagehandler,
    errorhandler,
    disconnecthandler
}