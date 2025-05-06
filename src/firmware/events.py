import json
from phew import server, logging

eventclients = set()

async def notifyevent(type, data):
    global eventclients

    logging.info(f"Notifying event {type} with {data}")
    payload = json.dumps({
        'type': type,
        'data': data
    })
    for client in eventclients:
        try:
            await client.send(payload)
        except:
            pass

@server.websocket("/events")
async def events(websocket):
    global eventclients

    eventclients.add(websocket)
    while True:
        evt = await websocket.recv()
        if evt is None or evt['type'] == 'close':
            break
    eventclients.discard(websocket)
