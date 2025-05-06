from os import uname
import network

machine = uname().machine

isrp2350 = "RP2350" in uname().machine

def haswifi():
    return hasattr(network, "WLAN")
