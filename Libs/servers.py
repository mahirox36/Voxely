from datetime import datetime
import os
import re
import threading
from typing import List
from mcrcon import MCRcon
import time
import psutil
from rich import print
import json
import subprocess
import socket
from .jar import MinecraftServerDownloader
import asyncio
from .serverProperties import ServerProperties

loop = asyncio.get_event_loop()


class ServerStatus:
    ONLINE = "online"
    OFFLINE = "offline"
    STARTING = "starting"
    STOPPING = "stopping"

class ServerType:
    VANILLA = "vanilla"
    FABRIC = "fabric"
    PAPER = "paper"
    CUSTOM = "custom"

def get_servers(space: bool = False):
    servers = []
    for server in os.listdir("servers"):
        with open(f"servers/{server}/server.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        if space:
            servers.append(data["name"].replace("_.", " "))
        else:
            servers.append(data["name"])
    return servers



class Server:
    def __init__(self,
                 name: str,
                 type: ServerType = ServerType.PAPER,
                 version: str = "1.21.1",
                 min_ram: int = 1024,
                 max_ram: int = 1024,
                 port: int = 25565,
                 players_limit: int = 20):
        self.name = name
        self.path = f"servers/{name}"
        self.full_path = os.path.join(os.getcwd(), self.path)
        self.Properties = ServerProperties(os.path.join(self.full_path, "server.properties"))
        self.started_at = None

        if os.path.exists(self.path):
            self._load_existing_server()
        else:
            self._create_new_server(type, version, min_ram, max_ram, port, players_limit)

    def _load_existing_server(self):
        with open(f"{self.path}/server.json", "r", encoding="utf-8") as f:
            self.data = json.load(f)
        
        for key, value in self.data.items():
            if key in ["players"]: continue
            setattr(self, key, value)
        if "started_at" in self.data:
            self.started_at = datetime.fromisoformat(self.data["started_at"]) if self.data["started_at"] != None else None
        
        if self.is_server_online == False:
            self.data["status"] = ServerStatus.OFFLINE
            self.logs = []
            self.started_at = None
            self._save_state()
        self.status = ServerStatus.OFFLINE
    @property
    def players(self) -> List[str]:
        return self.get_players()

    def _create_new_server(self, type, version, min_ram, max_ram, port, players_limit):
        self.created_at = datetime.now()
        self.status = ServerStatus.OFFLINE
        self.type = type
        self.version = version
        self.players_limit = players_limit
        self.logs = []
        self.min_ram = min_ram
        self.max_ram = max_ram
        self.port = port

        os.makedirs(self.path, exist_ok=True)
        
        self.jar_path = self._download_jar(type, version)
        self.jar_full_path = os.path.join(self.full_path, os.path.basename(self.jar_path))

        self.data = {
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at,
            "status": self.status,
            "type": self.type,
            "version": self.version,
            "players_limit": self.players_limit,
            "path": self.path,
            "jar_path": self.jar_path,
            "min_ram": self.min_ram,
            "max_ram": self.max_ram,
            "full_path": self.full_path,
            "jar_full_path": self.jar_full_path,
            "port": self.port,
            "players": self.players,
            "logs": self.logs,
        }

        self._save_server_data()
        with open(os.path.join(self.full_path, "server.properties"),"w") as f:
            f.write(f"""motd={self.name}
max-players={players_limit}
server-port={port}
enable-rcon=true
rcon.password=sdu923rf873bdf4iu53aw2
                    """)
    @property
    def lengthPlayers(self):
        return len(self.players)
    def _download_jar(self, type: ServerType, version: str):
        downloader = MinecraftServerDownloader()
        if type == ServerType.VANILLA:
            path = downloader.downloadVanilla(version)
        elif type == ServerType.PAPER:
            path = downloader.downloadPaper(version)
        elif type == ServerType.FABRIC:
            path = downloader.downloadFabric(version)
        else:
            return False
        
        new_path = os.path.join(self.path, os.path.basename(path))
        os.rename(path, new_path)
        return new_path
    @property
    def is_server_online(self):
        """Check if the server is currently online by attempting to connect to the specified port."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)  # Set timeout to avoid long waits
            try:
                result = sock.connect_ex(('localhost', self.port))
                if result == 0:
                    self.status = ServerStatus.ONLINE
                    return True
                else:
                    self.status = ServerStatus.OFFLINE
                    return False
            except socket.error as e:
                self.status = ServerStatus.OFFLINE
                self.started_at = None
                return False

    def _save_server_data(self):
        with open(f"{self.path}/server.json", "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)
    @property
    def uptime(self):
        if self.started_at:
            uptime_seconds = (datetime.now() - self.started_at).total_seconds()
            
            # Calculate days, hours, minutes, and seconds
            days, remainder = divmod(uptime_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            return f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
        else:
            return "Offline"
    async def get_metrics(self,edited: bool = False):
        usage = await self.measure_process_usage()
        print(self.lengthPlayers)
        return {
            "cpu_usage": usage['cpu'],
            "memory_usage": usage['memory'],
            "player_count": self.lengthPlayers,
            "uptime": self.uptime
        } if edited == False else {
            "cpu_usage": f"%{usage['cpu']:.2f}",
            "memory_usage": f"%{usage['memory']:.2f}",
            "player_count": f"{self.lengthPlayers}/{self.players_limit}",
            "uptime": self.uptime
        }
    def _save_state(self):
        self.data["status"] = self.status
        self.data["players"] = self.players
        self.data["logs"] = self.logs
        self.data["started_at"] = self.started_at.isoformat() if self.started_at != None else None
        self._save_server_data()

    def get_players(self):
        if self.is_server_online:
            try:
                with MCRcon(self.ip["private"].split(":")[0], "sdu923rf873bdf4iu53aw2", port=25575) as mcr:
                    response = mcr.command("list")
                    # Parse the response to extract player count and names
                    if response:
                        match = re.search(r"There are (\d+) of a max of \d+ players online: (.+)", response)
                        if match:
                            player_count = int(match.group(1))
                            player_names = match.group(2).split(", ")
                        else:
                            player_count = 0
                            player_names = []
                return player_names
            except Exception as e:
                print(f"Error using RCON: {e}")
        else:
            return []
    
    def accept_eula(self):
        with open(f"{self.path}/eula.txt", "w", encoding="utf-8") as f:
            f.write("eula=true")

    def start(self):
        self.status = ServerStatus.STARTING
        self._save_state()
        start_command = f"java -Xmx{self.max_ram}M -Xms{self.min_ram}M -jar {self.jar_full_path} nogui"

        self.process = subprocess.Popen(
            start_command,
            cwd=self.path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        self.logs.append(f"Started server with command: {start_command}")
        
        self.output_thread = threading.Thread(target=self._capture_output)
        self.output_thread.start()

    def _capture_output(self):
        for line in iter(self.process.stdout.readline, ''):
            line = line.strip()
            self.logs.append(line)
            
            # Broadcast the line to the WebSocket manager
            asyncio.run_coroutine_threadsafe(
                self.output_callback(line),
                loop
            )
            
            if "Done" in line:  # Detect when server is fully online
                self.status = ServerStatus.ONLINE
                self.started_at = datetime.now()  # Set start time for uptime
                self._save_state()
    
        self.process.stdout.close()
        self.status = ServerStatus.OFFLINE
        self._save_state()

    def _handle_new_line(self, line):
        if hasattr(self, "output_callback") and self.output_callback:
            # Use asyncio to send the output asynchronously
            asyncio.run_coroutine_threadsafe(
                self.output_callback(line), loop
            )

    def set_output_callback(self, callback):
        self.output_callback = callback

    async def measure_process_usage(self):
        if not hasattr(self, "process") or self.process is None:
            return {"cpu": 0, "memory": 0}
        
        try:
            p = psutil.Process(self.process.pid)
            
            cpu_start = p.cpu_percent()
            time.sleep(0.1)
            cpu_usage = p.cpu_percent()
            
            memory_info = p.memory_info()
            memory_usage = memory_info.rss / (1024 * 1024)
            
            return {"cpu": cpu_usage, "memory": memory_usage}
        except psutil.NoSuchProcess:
            return {"cpu": 0, "memory": 0}
        except Exception as e:
            return {"cpu": 0, "memory": 0}

    async def get_usage(self):
        usage = await self.measure_process_usage()
        return f"CPU: {usage['cpu']:.1f}%, Memory: {usage['memory']:.1f} MB"
    
    def stop(self):
        if self.status not in [ServerStatus.OFFLINE, ServerStatus.STOPPING]:
            self.started_at = None
            self.status = ServerStatus.STOPPING
            self._save_state()
            self.send_command("stop")
            self.output_thread.join()
            self.status = ServerStatus.OFFLINE
            self._save_state()

    def kill(self):
        if self.status in [ServerStatus.ONLINE, ServerStatus.STARTING]:
            self.status = ServerStatus.STOPPING
            self._save_state()
            self.process.terminate()
            self.output_thread.join()
            self.status = ServerStatus.OFFLINE
            self._save_state()

    def restart(self):
        self.stop()
        self.start()

    def delete(self):
        self.stop()
        os.rmdir(self.path)

    def send_command(self, command):
        if self.process and self.process.poll() is None:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()

    @property
    def ip(self):
        hostname = socket.gethostname()
        private_ip = f"{socket.gethostbyname(hostname)}:{self.port}"
        public_ip = f"{subprocess.check_output(['curl', 'ifconfig.me']).decode('utf-8').strip()}:{self.port}"
        return {"private": private_ip, "public": public_ip}

    def __str__(self):
        return f"Server {self.name} is {self.status}"