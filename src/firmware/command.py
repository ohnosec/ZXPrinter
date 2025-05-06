import time
import json
import asyncio
import usys
import gc
from phew.server import urldecode
from phew import logging

WHITESPACE = ''.join(chr(code) for code in range(33)) # control chars and space

class CommandDefinition:
    def __init__(self, name, handler, params):
        self.name = name
        self.handler = handler
        self.params = []
        self.secrets = set()
        self.optional = 0
        for param in params:
            if param.startswith('[') and param.endswith(']'):
                param = param[1:-1]
                self.optional += 1
            else:
                if self.optional > 0:
                    raise ValueError('Mandatory parameters must come before optional parameters')
            if param.startswith('*'):
                param = param[1:]
                self.secrets.add(param)
            self.params.append(param)

    class Command:
        def __init__(self, commanddef, params):
            self.commanddef = commanddef
            self.params = params
            self.callparams = {}
            self.maskedparams = []
            position = 0
            for param in params:
                paramname = commanddef.params[position] if position < len(commanddef.params) else None
                self.maskedparams.append('****' if paramname in commanddef.secrets else param)
                if not paramname:
                    continue
                self.callparams[paramname] = urldecode(param)
                position += 1

        async def invoke(self):
            if len(self.params) < len(self.commanddef.params)-self.commanddef.optional:
                raise ValueError(f"Missing parameters, expecting: {' '.join(self.commanddef.paramhelp())}")
            if len(self.params) > len(self.commanddef.params):
                raise ValueError(f"Too many parameters, expecting: {' '.join(self.commanddef.paramhelp())}")
            return await self.commanddef.call_handler(self.callparams)

        def __str__(self):
            return f"{self.commanddef.name.upper()} {' '.join(self.maskedparams)}"

    def match(self, tokens):
        if tokens[0].lower() == self.name.lower():
            return self.Command(self, tokens[1:])
        return None

    async def call_handler(self, params):
        return await self.handler(params)

    def paramhelp(self):
        mandatory = len(self.params)-self.optional
        position = 0
        for param in self.params:
            yield param if position<mandatory else f"[{param}]"
            position += 1

_commands = []

def _match_command(line):
    tokens = line.strip(WHITESPACE).split(" ")
    for commanddef in _commands:
        if command := commanddef.match(tokens):
            return command
    return None

def command_error(message, cause=None):
    response = { 'error': message }
    if cause:
        response['cause'] = cause
    return response

def add_command(name, handler, params):
    global _commands
    _commands.append(CommandDefinition(name, handler, params))

def command(name, *args):
    def _command(f):
        add_command(name, f, args)
        return f
    return _command

async def serialread(stdin):
    line = ''
    while True:
        byte = await stdin.read(1)
        if byte == '\n' or byte == '\r':
            return line
        line += byte

async def serialwrite(stdout, response):
    if type(response).__name__ == "generator":
        for chunk in response:
            await stdout.awrite(chunk)
    else:
        await stdout.awrite(json.dumps(response))
    await stdout.awrite("\n")

async def start_server():
    stdin = asyncio.StreamReader(usys.stdin)
    stdout = asyncio.StreamWriter(usys.stdout, {}) # type: ignore

    while True:
        try:
            line = await serialread(stdin)
            command_start_time = time.ticks_ms()
            command = _match_command(line)
            if command:
                try:
                    response = await command.invoke()
                    await serialwrite(stdout, response)
                    processing_time = time.ticks_ms() - command_start_time
                    logging.info(f"$ {command} [{processing_time}ms]")
                except Exception as e:
                    logging.error(f"$ {command} failed: {e}")
                    await serialwrite(stdout, command_error("Command failed", f"{e}"))
            else:
                await serialwrite(stdout, command_error("Unknown command"))
            gc.collect()
        except Exception as e:
            logging.error(f"$ Command read failed: {e}")
