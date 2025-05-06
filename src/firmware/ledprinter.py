async def capture(rows, busyled):
    while True:
        async for _ in rows:
            busyled.flash(200, rearm=200)
