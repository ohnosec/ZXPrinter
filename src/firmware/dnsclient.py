from micropython import const
from uctypes import addressof
import os, errno
import asyncio
import time
import socket
from utils import setbytes, setbyte, setword
from asyncudp import AsyncUdp

MDNSPORT    = const(5353)
ADDRESS     = const("224.0.0.251")

INCLASS     = const(1)      # the internet class

ATYPE       = const(1)      # IPv4
AAAATYPE    = const(28)     # IPv6
PTRTYPE     = const(12)
TXTTYPE     = const(16)
SRVTYPE     = const(33)

IDLEN       = const(2)      # ID
BITSLEN     = const(2)      # QR, OPCODE, AA, TC, RD, RA, Z, RCODE
COUNTLEN    = const(8)      # QDCOUNT, ANCOUNT, NSCOUNT, ARCOUNT
NAMELEN     = const(2)      # QNAME length + null terminator
TYPELEN     = const(2)      # QTYPE
CLASSLEN    = const(2)      # QCLASS

QRYMINLEN   = const(IDLEN+BITSLEN+COUNTLEN+NAMELEN+TYPELEN+CLASSLEN)
RSPMINLEN   = const(IDLEN+BITSLEN+COUNTLEN)

def buildquery(host, qtype):
    host = host.encode()
    id, _ = parseword(os.urandom(2), 0)
    query = bytearray(QRYMINLEN + len(host))
    ptr = addressof(query)
    ptr += setword(ptr, id)
    ptr += setword(ptr, 0x0100)             # query with recursion
    ptr += setword(ptr, 1)                  # one question RR
    ptr += 6                                # no answer, authority, or additional RRs
    for part in host.split(b"."):           # QNAME
        size = len(part)
        ptr += setbyte(ptr, size)
        ptr += setbytes(ptr, part, size)
    ptr += setbyte(ptr, 0)                  # end of QNAME
    ptr += setword(ptr, qtype)              # QTYPE
    ptr += setword(ptr, INCLASS)            # QCLASS (IN)
    return query, id

def parseword(b, pos):
    endpos = pos+2
    return int.from_bytes(b[pos: endpos], "big"), endpos

def parsedword(b, pos):
    endpos = pos+4
    return int.from_bytes(b[pos: endpos], "big"), endpos

def parsestring(b, pos):
    stringlen = int(b[pos])
    pos += 1
    endpos = pos+stringlen
    return bytes(b[pos: endpos]).decode("ascii"), endpos

def parsename(response, pos):
    parts = []
    while True:
        namelen = response[pos]
        pos += 1
        if (namelen & 0xC0) == 0xC0:        # a compression pointer
            pointerpos = ((namelen & 0x3F) << 8) | response[pos]
            pos += 1
            decompressed_name, _ = parsename(response, pointerpos)
            parts.append(decompressed_name)
            break
        elif namelen == 0:                  # end of name
            break
        else:                               # regular name
            labelbytes = bytes(response[pos:pos + namelen])
            label = labelbytes.decode("ascii")
            parts.append(label)
            pos += namelen
    return ".".join(parts), pos

def addrecord(records, type, value):
    record = records.get(type)
    if not record:
        record = []
        records[type] = record
    record.append(value)

def parseresponse(response, queryid, querytype):
    if len(response) < RSPMINLEN:
        raise ValueError("Bad DNS response: response length")
    response = memoryview(response)
    pos = 0

    id, pos = parseword(response, pos)
    if id != queryid:
        raise ValueError("Bad DNS response: ID")
    bits, pos = parseword(response, pos)
    if (bits & 0x000F) != 0:
        raise ValueError("Bad DNS response: bad response code")
    qdcount, pos = parseword(response, pos)
    ancount, pos = parseword(response, pos)
    if not ancount:
        raise ValueError("Bad DNS response: answer count")
    nscount, pos = parseword(response, pos)
    arcount, pos = parseword(response, pos)

    for _ in range(qdcount):
        qname, pos = parsename(response, pos)
        qtype, pos = parseword(response, pos)
        qclass, pos = parseword(response, pos)
        if qclass != INCLASS:
            raise ValueError("Bad DNS response: QCLASS")
        if qtype != querytype:
            raise ValueError("Bad DNS response: QTYPE")
        # print(f"QNAME: {qname} QTYPE: {qtype} QCLASS: {qclass}")

    records = {}

    for _ in range(ancount+nscount+arcount):
        rname, pos = parsename(response, pos)
        rtype, pos = parseword(response, pos)
        rclass, pos = parseword(response, pos)
        if rclass != INCLASS:
            raise ValueError("Bad DNS response: RCLASS")
        ttl, pos = parsedword(response, pos)
        rdlength, pos = parseword(response, pos)
        if rtype == ATYPE and rdlength == 4:
            ip = response[pos : pos + 4]
            address = ".".join(str(b) for b in ip)
            # print(f"A: {rname}: {address}")
            addrecord(records, "a", { "name": rname, "address": address })
        elif rtype == AAAATYPE and rdlength == 16:
            ip = response[pos : pos + 16]
            address = ":".join(f"{parseword(ip, i)[0]:x}" for i in range(0, 16, 2))
            # print(f"AAAA: {rname}: {address}")
            addrecord(records, "aaaa", { "name": rname, "address": address })
        elif rtype == PTRTYPE:
            name, _ = parsename(response, pos)
            # print(f"PTR: {name}")
            addrecord(records, "ptr", { "name": name })
        elif rtype == TXTTYPE:
            txtpos = pos
            txtindex = 0
            while txtpos < pos+rdlength:
                txt, txtpos = parsestring(response, txtpos)
                valuepos = txt.find("=")
                if valuepos <= 0:
                    name = f"txt[{txtindex}]"
                    value = txt
                    txtindex += 1
                else:
                    name = txt[:valuepos]
                    value = txt[valuepos+1:]
                if name == "pdl":
                    value = value.split(",")
                # print(f"TXT: {name}: {value}")
                addrecord(records, "txt", { "name": name, "value": value })
        elif rtype == SRVTYPE:
            srvpos = pos
            priority, srvpos = parseword(response, srvpos)
            weight, srvpos = parseword(response, srvpos)
            port, srvpos = parseword(response, srvpos)
            target, srvpos = parsename(response, srvpos)
            # print(f"SRV: target: {target} port: {port} priority: {priority} weight: {weight}")
            addrecord(records, "srv", {
                "target": target,
                "port": port,
                "priority": priority,
                "weight": weight
            })
        else:
            print(f"answer_type: {rtype} response: {response[pos : pos + rdlength]}")
        pos += rdlength

    return records

async def query(querytype, name, timeout=1000):
    if not name.endswith(".local"):
        raise ValueError("Only local names are currently supported")
    responses = []
    try:
        udp = AsyncUdp()
        address = socket.getaddrinfo(ADDRESS, MDNSPORT)[0][-1]
        query, queryid = buildquery(name, querytype)
        _ = udp.sendto(query, address)
        while True:
            response, _ = await udp.recvfrom(1024, timeout)
            if response is None:
                break
            responses.append(parseresponse(response, queryid, querytype))
    finally:
        udp.close()
    return responses

if __name__ == "__main__":
    async def main():
        global responses
        # responses = await query(PTRTYPE, "_ipp._tcp.local")                   # IPP
        # responses = await query(PTRTYPE, "_ipps._tcp.local")                  # IPPS
        # responses = await query(PTRTYPE, "_print._sub._ipp._tcp.local")       # IPP everywhere - doesn't work with my EPSON
        # responses = await query(PTRTYPE, "_printer._tcp.local")               # LPD - from Bonjour and IPP everywhere (LPD port 515)
        responses = await query(PTRTYPE, "_pdl-datastream._tcp.local")        # RAW - from Bonjour (RAW port 9100)...AppSocket/PhaserPort/JetDirect/Port9100
        # responses = await query(ATYPE, "EPSON2B357D.local")
        # responses = await query(AAAATYPE, "EPSON2B357D.local")
        # responses = await query(TXTTYPE, "EPSON XP-4200 Series._ipp._tcp.local")
        # responses = await query(SRVTYPE, "EPSON XP-4200 Series._ipp._tcp.local")
        print(responses)

    asyncio.run(main())
