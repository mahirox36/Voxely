import re
import time
from rich.console import Console
from Libs.servers import Server, status, Type, ExistingServer
import asyncio

console = Console()
ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')

def printNewLine(line):
    clean_line = ansi_escape.sub('', line)
    if "logged in with entity id" in line: return
    console.print(clean_line)

server= ExistingServer("Test")
server.set_output_callback(printNewLine)
server.acceptEula()
server.start()


async def main():
    while server.status != status.STOPPED:
        server.send_command(input("Command: "))
        print(await server.get_usage())

asyncio.run(main())
# ... wait for some time or until the server is fully started ...