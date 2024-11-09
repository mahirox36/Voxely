import datetime
import os
import threading
import time
import psutil
from rich import print
import json
import subprocess
import socket
from .jar import MinecraftServerDownloader
import asyncio

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

        if os.path.exists(self.path):
            self._load_existing_server()
        else:
            self._create_new_server(type, version, min_ram, max_ram, port, players_limit)

    def _load_existing_server(self):
        with open(f"{self.path}/server.json", "r", encoding="utf-8") as f:
            self.data = json.load(f)
        
        for key, value in self.data.items():
            setattr(self, key, value)
        
        self.status = ServerStatus.OFFLINE
        self.created_at = datetime.datetime.strptime(self.created_at, "%Y-%m-%d %H:%M:%S")

    def _create_new_server(self, type, version, min_ram, max_ram, port, players_limit):
        self.created_at = datetime.datetime.now()
        self.status = ServerStatus.OFFLINE
        self.type = type
        self.version = version
        self.players = []
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
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "status": self.status,
            "type": self.type,
            "version": self.version,
            "players": self.players,
            "players_limit": self.players_limit,
            "logs": self.logs,
            "path": self.path,
            "jar_path": self.jar_path,
            "min_ram": self.min_ram,
            "max_ram": self.max_ram,
            "full_path": self.full_path,
            "jar_full_path": self.jar_full_path,
            "port": self.port
        }

        self._save_server_data()

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

    def _save_server_data(self):
        with open(f"{self.path}/server.json", "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)
    async def get_metrics(self):
        usage = await self.measure_process_usage()
        return {
            "cpu_usage": usage['cpu'],
            "memory_usage": usage['memory'],
            "player_count": len(self.players),
            "uptime": (datetime.datetime.now() - self.created_at).total_seconds()
        }

    def accept_eula(self):
        with open(f"{self.path}/eula.txt", "w", encoding="utf-8") as f:
            f.write("eula=true")
    def _save_state(self):
        self.data["status"] = self.status
        self.data["players"] = self.players
        self.data["logs"] = self.logs
        self._save_server_data()

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
    
            if "Done" in line:
                self.status = ServerStatus.ONLINE
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
            print(f"Error measuring process usage: {e}")
            return {"cpu": 0, "memory": 0}

    async def get_usage(self):
        usage = await self.measure_process_usage()
        print(usage)
        return f"CPU: {usage['cpu']:.1f}%, Memory: {usage['memory']:.1f} MB"
    
    def stop(self):
        if self.status not in [ServerStatus.OFFLINE, ServerStatus.STOPPING]:
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