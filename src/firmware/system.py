import sys
import io
from os import uname # type: ignore
from phew import logging

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

def logexception(ex):
    exfile = io.StringIO()
    sys.print_exception(ex, exfile) # type: ignore
    exmessage = exfile.getvalue().strip() # type: ignore
    logging.error(f"Exception: {ex}\n{exmessage}")
