import asyncio

# from https://github.com/peterhinch/micropython-async/blob/master/v3/primitives/barrier.py
class Barrier:
    def __init__(self, participants):
        self._participants = participants
        self._count = participants
        self._evt = asyncio.Event()

    def __await__(self):
        if self.trigger():
            return  # Other tasks have already reached barrier
        # Wait until last task reaches it
        await self._evt.wait()  # type: ignore

    __iter__ = __await__

    def addparticipant(self):
        self._participants += 1
        self._count = self._participants

    def trigger(self):
        self._count -= 1
        if self._count < 0:
            raise ValueError("Too many tasks accessing Barrier")
        if self._count > 0:
            return False  # At least 1 other task has not reached barrier
        self._count = self._participants
        self._evt.set()  # Release others
        self._evt.clear()
        return True

class Producer:
    def __init__(self, items, barrier):
        self._items = items
        self._barrier = barrier

    def getdata(self):
        return self.data

    async def _setdata(self, value):
        self.data = value
        await self._barrier
        await self._barrier

    async def getproducer(self):
        while True:
            async for item in self._items:
                await self._setdata(item)
            await self._setdata(None)

class Consumer:
    def __init__(self, producer, barrier):
        barrier.addparticipant()
        self._producer = producer
        self._barrier = barrier
        self._first = True

    def __aiter__(self):
        return self

    def _getdata(self):
        data = self._producer.getdata()
        if data is None:
            raise StopAsyncIteration
        return data

    async def __anext__(self):
        await self._barrier
        if self._first:
            self._first = False
            return self._getdata()
        await self._barrier
        return self._getdata()

class ProducerConsumer:
    def __init__(self, asyncgenerator):
        self._barrier = Barrier(1)
        self._producer = Producer(asyncgenerator, self._barrier)

    def getproducer(self):
        return self._producer.getproducer()

    def addconsumer(self):
        return Consumer(self._producer, self._barrier)
