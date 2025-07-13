import asyncio, os, time
from . import logging
from hashlib import sha1
from binascii import b2a_base64
import struct
import gc

_routes = []
catchall_handler = None
exception_handler = None
loop = asyncio.get_event_loop()


def file_exists(filename):
  try:
    return (os.stat(filename)[0] & 0x4000) == 0
  except OSError:
    return False


def urldecode(text):
  text = text.replace("+", " ")
  result = ""
  token_caret = 0
  # decode any % encoded characters
  while True:
    start = text.find("%", token_caret)
    if start == -1:
      result += text[token_caret:]
      break
    result += text[token_caret:start]
    code = int(text[start + 1:start + 3], 16)
    result += chr(code)
    token_caret = start + 3
  return result

def _parse_query_string(query_string):
  result = {}
  for parameter in query_string.split("&"):
    key, value = parameter.split("=", 1)
    key = urldecode(key)
    value = urldecode(value)
    result[key] = value
  return result


class Request:
  def __init__(self, method, uri, protocol):
    self.method = method
    self.uri = uri
    self.protocol = protocol
    self.headers = {}
    self.form = {}
    self.data = {}
    self.query = {}
    query_string_start = uri.find("?") if uri.find("?") != -1 else len(uri)
    self.path = uri[:query_string_start]
    self.query_string = uri[query_string_start + 1:]
    if self.query_string:
      self.query = _parse_query_string(self.query_string)

  def __str__(self):
    return f"""\
request: {self.method} {self.path} {self.protocol}
headers: {self.headers}
form: {self.form}
data: {self.data}"""


class Response:
  def __init__(self, body, status=200, headers={}):
    self.status = status
    self.headers = headers
    self.body = body

  def add_header(self, name, value):
    self.headers[name] = value

  def __str__(self):
    return f"""\
status: {self.status}
headers: {self.headers}
body: {self.body}"""


content_type_map = {
  "html": "text/html",
  "jpg": "image/jpeg",
  "jpeg": "image/jpeg",
  "svg": "image/svg+xml",
  "json": "application/json",
  "png": "image/png",
  "css": "text/css",
  "js": "text/javascript",
  "csv": "text/csv",
}


class FileResponse(Response):
  def __init__(self, file, status=200, headers={}):
    self.status = 404
    self.headers = headers
    self.file = file

    try:
      if (os.stat(self.file)[0] & 0x4000) == 0:
        self.status = 200

        # auto set content type
        extension = self.file.split(".")[-1].lower()
        if extension in content_type_map:
          headers["Content-Type"] = content_type_map[extension]

        headers["Content-Length"] = os.stat(self.file)[6]
    except OSError:
      pass

class Route:
  def __init__(self, path, handler, methods=["GET"], iswebsocket=False):
    self.path = path
    self.methods = methods
    self.iswebsocket = iswebsocket
    self.handler = handler
    self.path_parts = path.split("/")

  # returns True if the supplied request matches this route
  def matches(self, request):
    if request.method not in self.methods:
      return False
    compare_parts = request.path.split("/")
    if len(compare_parts) != len(self.path_parts):
      return False
    for part, compare in zip(self.path_parts, compare_parts):
      if not part.startswith("<") and part != compare:
        return False
    return True

  # call the route handler passing any named parameters in the path
  def call_handler(self, request):
    parameters = {}
    for part, compare in zip(self.path_parts, request.path.split("/")):
      if part.startswith("<"):
        name = part[1:-1]
        parameters[name] = compare

    return self.handler(request, **parameters)

  def __str__(self):
    return f"""\
path: {self.path}
methods: {self.methods}
"""

  def __repr__(self):
    return f"<Route object {self.path} ({', '.join(self.methods)})>"


class WebSocket:
    HANDSHAKE_KEY = b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

    OP_TYPES = {
        0x0: 'cont',
        0x1: 'text',
        0x2: 'bytes',
        0x8: 'close',
        0x9: 'ping',
        0xa: 'pong',
    }

    @classmethod
    async def upgrade(cls, headers, reader, writer):
        key = headers['sec-websocket-key'].encode()
        key += WebSocket.HANDSHAKE_KEY
        x = b2a_base64(sha1(key).digest()).strip()
        writer.write(b'HTTP/1.1 101 Switching Protocols\r\n')
        writer.write(b'Upgrade: websocket\r\n')
        writer.write(b'Connection: Upgrade\r\n')
        writer.write(b'Sec-WebSocket-Accept: ' + x + b'\r\n')
        writer.write(b'\r\n')
        await writer.drain()
        return cls(reader, writer)

    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

    async def recv(self):
        reader = self.reader
        x = await reader.read(2)
        if not x or len(x) < 2:
            return None
        out = {}
        op, n = struct.unpack('!BB', x)
        out['fin'] = bool(op & (1 << 7))
        op = op & 0x0f
        if op not in WebSocket.OP_TYPES:
            raise None
        out['type'] = WebSocket.OP_TYPES[op]
        masked = bool(n & (1 << 7))
        n = n & 0x7f
        if n == 126:
            n, = struct.unpack('!H', await reader.read(2))
        elif n == 127:
            n, = struct.unpack('!Q', await reader.read(8))
        if masked:
            mask = await reader.read(4)
        data = await reader.read(n)
        if masked:
            data = bytearray(data)
            for i in range(len(data)):
                data[i] ^= mask[i % 4]
            data = bytes(data)
        if out['type'] == 'text':
            data = data.decode()
        out['data'] = data
        return out

    async def send(self, msg):
        if isinstance(msg, str):
            await self._send_op(0x1, msg.encode())
        elif isinstance(msg, bytes):
            await self._send_op(0x2, msg)

    async def _send_op(self, opcode, payload):
        writer = self.writer
        writer.write(bytes([0x80 | opcode]))
        n = len(payload)
        if n < 126:
            writer.write(bytes([n]))
        elif n < 65536:
            writer.write(struct.pack('!BH', 126, n))
        else:
            writer.write(struct.pack('!BQ', 127, n))
        writer.write(payload)
        await writer.drain()


# parses the headers for a http request (or the headers attached to
# each field in a multipart/form-data)
async def _parse_headers(reader):
  headers = {}
  while True:
    header_line = await reader.readline()
    if header_line == b"\r\n": # crlf denotes body start
      break
    header_split = header_line.decode().strip().split(": ", 1)
    name = header_split[0]
    value = "" if len(header_split) == 1 else header_split[1]
    headers[name.lower()] = value
  return headers


# returns the route matching the supplied path or None
def _match_route(request):
  for route in _routes:
    if route.matches(request):
      return route
  return None


# if the content type is multipart/form-data then parse the fields
async def _parse_form_data(reader, headers):
  boundary = headers["content-type"].split("boundary=")[1]
  # discard first boundary line
  dummy = await reader.readline()

  form = {}
  while True:
    # get the field name
    field_headers = await _parse_headers(reader)
    if len(field_headers) == 0:
      break
    name = field_headers["content-disposition"].split("name=\"")[1][:-1]
    # get the field value
    value = ""
    while True:
      line = await reader.readline()
      line = line.decode().strip()
      # if we hit a boundary then save the value and move to next field
      if line == "--" + boundary:
        form[name] = value
        break
      # if we hit end of form data boundary then save value and return
      if line == "--" + boundary + "--":
        form[name] = value
        return form
      value += line
  return None


# if the content type is application/json then parse the body
async def _parse_json_body(reader, headers):
  import json
  content_length_bytes = int(headers["content-length"])
  body = await reader.readexactly(content_length_bytes)
  return json.loads(body.decode())


status_message_map = {
  200: "OK", 201: "Created", 202: "Accepted",
  203: "Non-Authoritative Information", 204: "No Content",
  205: "Reset Content", 206: "Partial Content", 300: "Multiple Choices",
  301: "Moved Permanently", 302: "Found", 303: "See Other",
  304: "Not Modified", 305: "Use Proxy", 306: "Switch Proxy",
  307: "Temporary Redirect", 308: "Permanent Redirect",
  400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
  404: "Not Found", 405: "Method Not Allowed", 406: "Not Acceptable",
  408: "Request Timeout", 409: "Conflict", 410: "Gone",
  414: "URI Too Long", 415: "Unsupported Media Type",
  416: "Range Not Satisfiable", 418: "I'm a teapot",
  500: "Internal Server Error", 501: "Not Implemented"
}


# handle an incoming request to the web server
async def _handle_request(reader, writer):
  response = None

  request_start_time = time.ticks_ms()

  request_line = await reader.readline()
  try:
    method, uri, protocol = request_line.decode().split()
  except Exception as e:
    logging.error(e)
    return

  request = Request(method, uri, protocol)
  request.headers = await _parse_headers(reader)
  if "content-length" in request.headers and "content-type" in request.headers:
    if request.headers["content-type"].startswith("multipart/form-data"):
      request.form = await _parse_form_data(reader, request.headers)
    if request.headers["content-type"].startswith("application/json"):
      request.data = await _parse_json_body(reader, request.headers)
    if request.headers["content-type"].startswith("application/x-www-form-urlencoded"):
      form_data = await reader.read(int(request.headers["content-length"]))
      request.form = _parse_query_string(form_data.decode())

  route = _match_route(request)
  if route:
    if route.iswebsocket:
      websocket = await WebSocket.upgrade(request.headers, reader, writer)
      await route.handler(websocket)
      await writer.wait_closed()
      return
    try:
      response = await route.call_handler(request)
    except Exception as e:
      if exception_handler:
        response = exception_handler(request, e)
      else:
        raise
  elif catchall_handler:
    response = catchall_handler(request)

  # if shorthand body generator only notation used then convert to tuple
  if type(response).__name__ == "generator":
    response = (response,)

  # if shorthand body text only notation used then convert to tuple
  if isinstance(response, str):
    response = (response,)

  # if shorthand tuple notation used then build full response object
  if isinstance(response, tuple):
    body = response[0]
    status = response[1] if len(response) >= 2 else 200
    content_type = response[2] if len(response) >= 3 else "text/html"
    response = Response(body, status=status)
    response.add_header("Content-Type", content_type)
    if hasattr(body, '__len__'):
      response.add_header("Content-Length", len(body))

  # write status line
  status_message = status_message_map.get(response.status, "Unknown")
  writer.write(f"HTTP/1.1 {response.status} {status_message}\r\n".encode("ascii"))

  # write headers
  for key, value in response.headers.items():
    writer.write(f"{key}: {value}\r\n".encode("ascii"))

  # blank line to denote end of headers
  writer.write("\r\n".encode("ascii"))

  if isinstance(response, FileResponse):
    # file
    chunk = bytearray(1024)
    chunkview = memoryview(chunk)
    with open(response.file, "rb") as f:
      while True:
        bytecount = f.readinto(chunk)
        if not bytecount:
          break
        writer.write(chunkview[0:bytecount])
        await writer.drain()
  elif type(response.body).__name__ == "generator":
    # generator
    for chunk in response.body:
      writer.write(chunk)
      await writer.drain()
  else:
    # string/bytes
    writer.write(response.body)
    await writer.drain()

  writer.close()
  await writer.wait_closed()

  processing_time = time.ticks_ms() - request_start_time
  logging.info(f"> {request.method} {request.path} ({response.status} {status_message}) [{processing_time}ms]")
  gc.collect()

# adds a new route to the routing table
def _add_route(route):
  global _routes
  _routes.append(route)
  # descending complexity order so most complex routes matched first
  _routes = sorted(_routes, key=lambda route: len(route.path_parts), reverse=True)


# adds a new web route
def add_route(path, handler, methods=["GET"]):
  _add_route(Route(path, handler, methods))


# adds a new websocket route
def add_websocket(path, handler):
  _add_route(Route(path, handler, methods=["GET"], iswebsocket=True))


def set_catchall(handler):
  global catchall_handler
  catchall_handler = handler


def set_exception(handler):
  global exception_handler
  exception_handler = handler


# decorator shorthand for adding a route
def route(path, methods=["GET"]):
  def _route(f):
    add_route(path, f, methods=methods)
    return f
  return _route


# decorator shorthand for adding a websocket
def websocket(path):
  def _websocket(f):
    add_websocket(path, f)
    return f
  return _websocket


# decorator for adding catchall route
def catchall():
  def _catchall(f):
    set_catchall(f)
    return f
  return _catchall


# decorator for adding exception route
def exception():
  def _exception(f):
    set_exception(f)
    return f
  return _exception


def redirect(url, status = 301):
  return Response("", status, {"Location": url})


def serve_file(file):
  return FileResponse(file)

def create_task(host = "0.0.0.0", port = 80, usessl = False):
  if usessl:
    import ssl
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("ec_cert.der", "ec_key.der")
    loop.create_task(asyncio.start_server(_handle_request, host, 443, ssl=context))

  loop.create_task(asyncio.start_server(_handle_request, host, port))

def run(host = "0.0.0.0", port = 80, usessl = False):
  logging.info("> starting web server on port {}".format(port))

  create_task(host, port, usessl)

  loop.run_forever()

def stop():
  loop.stop()

def close():
  loop.close()