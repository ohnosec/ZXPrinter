from os import uname # type: ignore

machine = uname().machine

isrp2350 = "RP2350" in uname().machine

_hasnetwork = None

def hasnetwork():
    global _hasnetwork

    if _hasnetwork is None:
        try:
            import network
            _hasnetwork = hasattr(network, "WLAN")
        except:
            _hasnetwork = False
    return _hasnetwork