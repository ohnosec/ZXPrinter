# pyright: reportUndefinedVariable=false

@micropython.viper
def setbytes(buf: ptr8, frombuf: ptr8, len: int) -> int:
    for i in range(len):
        buf[i] = frombuf[i]
    return len

@micropython.viper
def setbyte(buf: ptr8, val: int) -> int:
    buf[0] = val
    return 1

@micropython.viper
def setword(buf: ptr8, val: int) -> int:
    buf[0] = (val >> 8) & 0xff
    buf[1] = val & 0xff
    return 2

@micropython.viper
def setdword(buf: ptr8, val: int) -> int:
    buf[0] = (val >> 24) & 0xff
    buf[1] = (val >> 16) & 0xff
    buf[2] = (val >> 8) & 0xff
    buf[3] = val & 0xff
    return 4

@micropython.viper
def getword(buf: ptr8) -> int:
    return ((buf[0] << 8) & 0xff) | (buf[1] & 0xff)

@micropython.viper
def getdword(buf: ptr8) -> int:
    return ((buf[0] << 24) & 0xff) | ((buf[1] << 16) & 0xff) | ((buf[2] << 8) & 0xff) | (buf[3] & 0xff)
