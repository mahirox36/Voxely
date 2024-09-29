# from pydantic import BaseModel
import datetime
import os
import threading
import time
import psutil
from rich import print
from .jar import MinecraftServerDownloader
import json
import subprocess

class status:
    RUNNING= "running"
    STOPPED= "stopped"
    STARTING= "starting"
    STOPPING= "stopping"

class Type:
    VANILLA= "vanilla"
    FABRIC= "fabric"
    PAPER= "paper"
    CUSTOM= "custom"

def get_servers():
    servers = []
    for server in os.listdir("servers"):
        with open(f"servers/{server}/server.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        servers.append(data["name"])
    return servers

class Server:
    def __init__(self, name: str, type: Type = Type.PAPER, version: str = "1.21.1", minRam: int = 1024, maxRam: int = 1024):
        if os.path.exists(f"servers/{name}"):
            raise FileExistsError(f"Server with name {name} already exists")
        self.name = name
        self.created_at = datetime.datetime.now()
        self.status = status.STOPPED
        self.type = type
        self.version = version
        self.players = []
        self.logs = []
        self.id = hash(name)
        self.path = f"servers/{name}"
        self.minRam = minRam
        self.maxRam = maxRam
        self.full_path = os.path.join(os.getcwd(), self.path)
        os.makedirs(self.path, exist_ok=True)
        
        self.jar_path= self.downloadJar(type, version)
        self.jar_full_path= os.path.join(self.full_path, os.path.basename(self.jar_path))
        data = {
            "name"      : self.name,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "status"    : self.status,
            "type"      : self.type,
            "version"   : self.version,
            "players"   : self.players,
            "logs"      : self.logs,
            "id"        : self.id,
            "path"      : self.path,
            "jar_path"  : self.jar_path,
            "minRam"    : self.minRam,
            "maxRam"    : self.maxRam,
            "full_path" : self.full_path,
            "jar_full_path": self.jar_full_path}
        with open(f"{self.path}/server.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(data))
        
    def downloadJar(self, type: Type = Type.PAPER, version: str = "1.21.1"):
        Downloader = MinecraftServerDownloader()
        if type == Type.VANILLA:  path= Downloader.downloadVanilla(version)
        elif type == Type.PAPER:  path= Downloader.downloadPaper(version)
        elif type == Type.FABRIC: path= Downloader.downloadFabric(version)
        else:return False
        
        os.rename(path, os.path.join(self.path, os.path.basename(path)))
        return os.path.join(self.path, os.path.basename(path))
    def acceptEula(self):
        with open(f"{self.path}/eula.txt", "w", encoding="utf-8") as f:
            f.write("eula=true")
        
    def start(self):
        self.status = status.STARTING
        start_command = f"java -Xmx{self.maxRam}M -Xms{self.minRam}M -jar {self.jar_full_path} nogui"

        self.process = subprocess.Popen(
            start_command,
            cwd=self.path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Redirect stderr to stdout
            shell=True,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )

        self.logs.append(f"Started server with command: {start_command}")
        
        # Start thread for capturing output
        self.output_thread = threading.Thread(target=self._capture_output)
        self.output_thread.start()

    def _capture_output(self):
        for line in iter(self.process.stdout.readline, ''):
            line = line.strip()
            self.logs.append(line)
            self._handle_new_line(line)

            # Check for server ready message
            if "Done" in line:
                self.status = status.RUNNING

        self.process.stdout.close()
        self.status = status.STOPPED

    def _handle_new_line(self, line):
        # If there's a callback function set, call it with the new line
        if hasattr(self, "output_callback"):
            if self.output_callback:
                self.output_callback(line)

    def set_output_callback(self, callback):
        """Set a callback function to be called for each new line of output."""
        self.output_callback = callback

    async def measure_process_usage(self):
        if not hasattr(self, "process") or self.process is None:
            return {"cpu": 0, "memory": 0}
        
        try:
            p = psutil.Process(self.process.pid)
            
            # Measure CPU usage over a short interval
            cpu_start = p.cpu_percent()
            time.sleep(0.1)  # Wait for a short time to get a more accurate measurement
            cpu_usage = p.cpu_percent()
            
            # Measure memory usage
            memory_info = p.memory_info()
            memory_usage = memory_info.rss / (1024 * 1024)  # Convert bytes to MB
            
            return {"cpu": cpu_usage, "memory": memory_usage}
        except psutil.NoSuchProcess:
            # Process has terminated
            return {"cpu": 0, "memory": 0}
        except Exception as e:
            print(f"Error measuring process usage: {e}")
            return {"cpu": 0, "memory": 0}

    async def get_usage(self):
        usage = await self.measure_process_usage()
        print(usage)
        return f"CPU: {usage['cpu']:.1f}%, Memory: {usage['memory']:.1f} MB"
    
    def stop(self):
        if self.status != status.STOPPED or self.status != status.STOPPING:
            self.status = status.STOPPING
            self.send_command("stop")
            self.output_thread.join()
            self.status = status.STOPPED

    def kill(self):
        if self.status in [status.RUNNING, status.STARTING]:
            self.status = status.STOPPING
            self.process.terminate()
            self.output_thread.join()
            self.status = status.STOPPED

    def restart(self):
        self.stop()
        self.start()

    def delete(self):
        self.stop()
        os.rmdir(self.path)
        del self

    def send_command(self, command):
        if self.process and self.process.poll() is None:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()

    def __str__(self):
        return f"Server {self.name} is {self.status}"

class ExistingServer(Server):
    def __init__(self, name: str):
        self.name = name
        self.path = f"servers/{name}"
        self.full_path = os.path.join(os.getcwd(), self.path)
        
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"Server with name {name} does not exist")
        
        with open(f"{self.path}/server.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.created_at = datetime.datetime.strptime(data["created_at"], "%Y-%m-%d %H:%M:%S")
        self.status = data["status"]
        self.type = data["type"]
        self.version = data["version"]
        self.players = data["players"]
        self.logs = data["logs"]
        self.id = data["id"]
        self.jar_path = data["jar_path"]
        self.minRam = data["minRam"]
        self.maxRam = data["maxRam"]
        self.jar_full_path = os.path.join(self.full_path, os.path.basename(self.jar_path))