import json
from phew import server, logging
from command import serialnotify

eventclients = set()

pingmessage = "__ping__"
pongmessage = "__pong__"

connecthandlers = []

def addconnecthandler(handler, data):
    connecthandlers.append((handler, data))

async def sendall(message):
    global eventclients

    for client in eventclients:
        try:
            await client.send(message)
        except:
            pass

async def notifyevent(type, data):
    global eventclients

    logging.info(f"Notifying event {type} with {data}")
    event = json.dumps({
        "event": {
            "type": type,
            "data": data
        }
    })
    await serialnotify(event)
    await sendall(event)

@server.websocket("/events")
async def events(websocket):
    global eventclients

    eventclients.add(websocket)
    for handler in connecthandlers:
        await handler[0](handler[1])
    while True:
        evt = await websocket.recv()
        if evt is None or evt["type"] == "close":
            break
        if evt["type"] == "text":
            message = str(evt["data"])
            if message == pingmessage:
                await websocket.send(pongmessage)
    eventclients.discard(websocket)
