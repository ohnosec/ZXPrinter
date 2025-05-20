import json
from phew import server, logging
from command import serialnotify

eventclients = set()

connecthandlers = []

def addconnecthandler(handler, data):
    connecthandlers.append((handler, data))

async def notifyevent(type, data):
    global eventclients

    logging.info(f"Notifying event {type} with {data}")
    payload = json.dumps({
        "event": {
            "type": type,
            "data": data
        }
    })
    await serialnotify(payload)
    for client in eventclients:
        try:
            await client.send(payload)
        except:
            pass

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
        # if evt["type"] == "text":
        #     print(f"websocket text: {evt['data']}")
    eventclients.discard(websocket)
