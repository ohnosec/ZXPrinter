from micropython import const

STATE_IDLE   = const(0)
STATE_LITERAL = const(1)
STATE_REPEAT  = const(2)
MAX_LENGTH    = const(128)

class PackBitsFile:
    def __init__(self, filename):
        self._file = open(filename, 'wb')
        self._state =  STATE_IDLE
        self._lastbyte = 0
        self._literal = bytearray(MAX_LENGTH+1)
        self._literallen = 0
        self._literalview = memoryview(self._literal)
        self._literalbytes = bytearray(1)
        self._repeat = 0
        self._repeatbytes = bytearray(2)

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.close()

    def _writeliteral(self):
        litlen = self._literallen
        if litlen>0:
            self._literalbytes[0] = litlen-1
            self._file.write(self._literalbytes)
            self._file.write(self._literalview[0:litlen])
            self._literallen = 0

    def _writerepeat(self):
        while self._repeat > 0:
            repeatsize = self._repeat if self._repeat <= MAX_LENGTH else MAX_LENGTH-1
            self._repeatbytes[0] = 256-repeatsize+1
            self._repeatbytes[1] = self._lastbyte
            self._file.write(self._repeatbytes)
            self._repeat -= repeatsize

    def write(self, byte):
        if self._state == STATE_IDLE:
            self._state = STATE_LITERAL
        elif self._state == STATE_LITERAL:
            if self._lastbyte != byte:
                if self._literallen >= MAX_LENGTH:
                    self._writeliteral()
                self._literal[self._literallen] = self._lastbyte
                self._literallen += 1
            else:
                self._writeliteral()
                self._repeat = 2
                self._state = STATE_REPEAT
        elif self._state == STATE_REPEAT:
            if self._lastbyte == byte:
                self._repeat += 1
            else:
                self._writerepeat()
                self._state = STATE_LITERAL
        self._lastbyte = byte

    def close(self):
        if self._state == STATE_IDLE:
            pass
        elif self._state == STATE_LITERAL:
            self._literal[self._literallen] = self._lastbyte
            self._literallen += 1
            self.write(self._lastbyte)
        elif self._state == STATE_REPEAT:
            self.write(None)
        return self._file.close()

class UnpackBitsFile:
    def __init__(self, filename):
        self._file = open(filename, 'rb')
        self._state = STATE_IDLE
        self._literallen = 0
        self._repeatlen = 0
        self._repeatbyte = 0

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.close()

    def read(self):
        while True:
            if self._state == STATE_IDLE:
                data = self._file.read(1)
                if not data:
                    return None
                flagcounter = data[0]
                if flagcounter == 128:  # ignore
                    continue
                if flagcounter > 128:   # repeat
                    data = self._file.read(1)
                    if not data:
                        return None
                    self._state = STATE_REPEAT
                    self._repeatlen = 256 - flagcounter - 1
                    self._repeatbyte = data[0]
                    return self._repeatbyte
                # literal
                data = self._file.read(1)
                if not data:
                    return None
                self._state = STATE_LITERAL
                self._literallen = flagcounter - 1
                return data[0]
            elif self._state == STATE_LITERAL:
                if self._literallen < 0:
                    self._state = STATE_IDLE
                    continue
                data = self._file.read(1)
                if not data:
                    return None
                self._literallen -= 1
                return data[0]
            elif self._state == STATE_REPEAT:
                if self._repeatlen < 0:
                    self._state = STATE_IDLE
                    continue
                self._repeatlen -= 1
                return self._repeatbyte

    def close(self):
        self._file.close()
