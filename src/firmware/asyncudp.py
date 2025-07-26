import asyncio
import socket
from socket import AF_INET, SOCK_DGRAM

class Client:
    def __init__(self):
        self.socket = socket.socket(AF_INET, SOCK_DGRAM)
        self.socket.setblocking(False)

    # from Stream.readinto in micropython/extmod/asyncio/stream.py
    # despite the lack of async this is indeed async
    def _read(self, bufsize):
        yield asyncio.core._io_queue.queue_read(self.socket) # type: ignore
        return self.socket.recvfrom(bufsize)

    async def _readtimeout(self, bufsize, timeoutms):
        try:
            return await asyncio.wait_for_ms(self._read(bufsize), timeoutms) # type: ignore
        except asyncio.TimeoutError:
            return None, None

    async def recvfrom(self, bufsize, timeoutms = -1):
        if timeoutms <= 0:
            return await self._read(bufsize) # type: ignore
        else:
            return await self._readtimeout(bufsize, timeoutms)

    def sendto(self, bytes, address):
        return self.socket.sendto(bytes, address)

    def close(self):
        self.socket.close()
