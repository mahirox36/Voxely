import asyncio
from asyncio.subprocess import Process
import json
import logging
import os
import re
import shutil
import uuid
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

import aiofiles
import aiohttp
import psutil
from mcrcon import MCRcon
from pydantic import SecretStr

from modules.Backup import BackupManager
from modules.jar import JarDownloader
from modules.playitgg import download_playit
from modules.router import WebSocketManager
from modules.javaManager import JavaManager
from .models import (
    PlayerDBResponse,
    PlayerDetails,
    ServerResponse,
    ServerType,
    ServerStatus,
    ServerConfigModel,
    ServerCreationRequest,
    ServerMetricsModel,
    AddonModel,
    get_addon_type_for_server,
    get_addon_directory_name,
)

# from process_handler import ProcessHandler, ProcessStartResult
# from event_router import WebSocketEventRouter, EventType

logger = logging.getLogger("server_service")
SECRET_KEY = os.getenv("SECRET_KEY", "idkwhatimdoingbu")
if SECRET_KEY == "idkwhatimdoingbu":
    logger.warning(
        "SECRET_KEY environment variable not set. Using default insecure key. This should be changed!"
    )


class ServerService:
    servers: Dict[str, "ServerInstance"] = {}

    def __init__(
        self,
        servers_base_path: str = "servers",
    ):
        self.java_manager = JavaManager()
        self.jar_downloader = JarDownloader()
        self.servers_base_path = Path(servers_base_path)
        self.servers_base_path.mkdir(exist_ok=True)
        self.logger = logger
        # name ->
        self.global_data_file = self.servers_base_path / "servers_data.json"
        self._load_servers_data()

    def _load_servers_data(self):
        """Crawl the servers directory and load each server's individual config."""
        for server_folder in self.servers_base_path.iterdir():
            # Only look at directories that look like a UUID
            if server_folder.is_dir() and self._is_uuid(server_folder.name):
                config_path = server_folder / "config.json"

                if config_path.exists():
                    try:
                        with open(config_path, "r") as f:
                            data = json.load(f)
                            config = ServerConfigModel(**data)

                        self.servers[config.id] = ServerInstance(
                            id=config.id,  # The UUID
                            path=self.servers_base_path,
                            java_manager=self.java_manager,
                            jar_downloader=self.jar_downloader,
                            config=config,
                        )
                    except Exception as e:
                        self.logger.error(
                            f"Failed to load server at {server_folder}: {e}"
                        )

    def _is_uuid(self, name: str) -> bool:
        # Quick regex check to ensure we aren't loading random folders
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        return bool(re.match(uuid_pattern, name.lower()))

    async def create_server(
        self,
        request: ServerCreationRequest,
        socket: WebSocketManager,
        initialize: bool = True,
    ) -> "ServerInstance":
        """Create a new server instance based on the provided configuration."""
        server_id = str(uuid.uuid4())
        server_path = self.servers_base_path / server_id
        server_path.mkdir(parents=True, exist_ok=False)

        config = ServerConfigModel(
            id=server_id,
            name=request.name,
            type=request.type,
            version=request.version,
        )

        server_instance = ServerInstance(
            id=server_id,
            path=self.servers_base_path,
            java_manager=self.java_manager,
            jar_downloader=self.jar_downloader,
            config=config,
        )

        self.servers[server_id] = server_instance
        server_instance.socket = socket
        await server_instance.save_config()  # Save initial config to disk
        self.logger.info(
            f"Created server instance '{server_id}' with config: {config.json()}"
        )

        if initialize:
            await server_instance.initialize()
        return server_instance

    async def get_server_instance(self, server_id: str) -> Optional["ServerInstance"]:
        """Helper to retrieve a server instance by ID."""
        return self.servers.get(server_id)

    async def delete_server(self, server_id: str):
        """Delete a server instance and its files without blocking the event loop."""
        server = self.servers.get(server_id)
        if not server:
            self.logger.warning(f"Tried to delete non-existent server '{server_id}'")
            return

        if server.status == ServerStatus.ONLINE:
            await server.stop()

        del self.servers[server_id]

        def remove_files():
            if server.path.exists():
                shutil.rmtree(server.path)

        try:
            await asyncio.to_thread(remove_files)
            self.logger.info(
                f"Deleted server '{server_id}' and its files successfully."
            )
        except Exception as e:
            self.logger.error(f"Failed to delete files for server '{server_id}': {e}")


class ServerInstance:
    def __init__(
        self,
        id: str,
        path: Path,
        java_manager: JavaManager,
        jar_downloader: JarDownloader,
        config: ServerConfigModel,
        socket: Optional[WebSocketManager] = None,
    ):
        self.id = id
        self.path = path / id
        self.java_manager = java_manager
        self.socket = socket
        self.logger = logging.getLogger(f"server.{self.id}")
        self.jar_downloader = jar_downloader

        self.config: ServerConfigModel = config
        self.process: Optional[Process] = None
        self.playit_process: Optional[Process] = None
        self.status: ServerStatus = ServerStatus.OFFLINE
        self.metrics: Optional[ServerMetricsModel] = None

        self.started_at: Optional[float] = None
        self._output_task: Optional[asyncio.Task] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._output_task_playit: Optional[asyncio.Task] = None
        self._rcon: Optional[MCRcon] = None
        self._rcon_lock = asyncio.Lock()
        self.java_path: Optional[Path] = None

        self.console_buffer: List[str] = []  # Buffer to store console output lines
        self._session: Optional[aiohttp.ClientSession] = None
        self._headers = {
            "User-Agent": "VoxelyServerManager/1.0 (contact: mahiroc36@gmail.com)"
        }
        self._cached_user_data: Dict[str, PlayerDetails] = {}

        self.playit_path: Optional[Path] = None
        self.addon_path = self.path / get_addon_directory_name(
            get_addon_type_for_server(self.config.type)
        )

        self.backup = BackupManager(self)

        self._setup_logger()

    async def emit(self, event: str, data: Any):
        """Helper to emit WebSocket events to the frontend."""
        if self.socket:
            await self.socket.emit(event, {"server_id": self.id, "data": data})

    def _setup_logger(self) -> None:
        """Set up logging for this server instance."""
        log_path = self.path / "server.log"
        self.path.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(log_path)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        self.logger.addHandler(handler)

    async def save_config(self):
        """Save the current configuration to the server's local folder."""
        config_path = self.path / "config.json"
        async with aiofiles.open(config_path, "w") as f:
            await f.write(self.config.model_dump_json(indent=4))

    async def _install_playit(self) -> Path | None:
        if self.config.use_playit:
            self.logger.info("Setting up playit.gg tunnel...")
            await self.emit("server.playit.downloading", {"server_id": self.id})
            bin_dir = Path("./bin")
            bin_dir.mkdir(exist_ok=True)

            try:
                self.playit_path = await download_playit(bin_dir)
                self.logger.info(f"Playit ready at {self.playit_path}")
                await self.emit("server.playit.ready", {"server_id": self.id})
                return self.playit_path
            except Exception as e:
                self.logger.error(f"Failed to setup playit: {e}")

    async def initialize(self):
        """Initialize the server by downloading the necessary JAR and setting up folders."""

        self._session = aiohttp.ClientSession(headers=self._headers)

        try:
            self.logger.info(
                f"Initializing server '{self.id}' with version {self.config.version}"
            )
            await self.emit(
                "server.jar.downloading",
                {"server_id": self.id, "config": self.config.model_dump(mode="json")},
            )
            jar_path = await self.jar_downloader.download_jar(
                self.config.version, self.config.type, self.path
            )
            self.config.jar_path = str(jar_path)
            self.logger.info(
                f"Server '{self.id}' initialized successfully with JAR at {jar_path}"
            )

            await self.emit(
                "server.java.downloading",
                {"server_id": self.id, "config": self.config.model_dump(mode="json")},
            )

            self.java_path = await self.java_manager.get_java_path(self.config.version)

            await self._create_server_properties()

            await self._install_playit()

            await self.save_config()
            await self.emit(
                "server.initialized",
                {"server_id": self.id, "config": self.config.model_dump(mode="json")},
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize server '{self.id}': {e}")
            await self._close_session()
            await self.emit(
                "server.initialization.failed", {"server_id": self.id, "error": str(e)}
            )

    async def _close_session(self):
        """Important: Close the session when the instance is destroyed or stopped."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _create_server_properties(self) -> None:
        """Create server.properties file."""
        props_file = self.path / "server.properties"
        content = f"""motd={self.config.name}\nmax-players={self.config.players_limit}\nserver-port={self.config.port}\nenable-rcon=true\nrcon.password={self.config.name}{SECRET_KEY}\nrcon.port=25575"""
        async with aiofiles.open(props_file, "w") as f:
            await f.write(content)
        self.logger.debug(f"Created server.properties")

    async def start(self):
        """Start the Minecraft server process."""
        if self.status == ServerStatus.ONLINE:
            self.logger.warning(f"Server '{self.id}' is already running.")
            return

        if not self.config.jar_path or not self.java_path:
            self.logger.error(f"Server '{self.id}' is missing JAR path or Java path.")
            return

        if not self.config.eula_accepted:
            self.logger.error(
                f"Server '{self.id}' cannot start without accepting EULA."
            )
            await self.emit(
                "server.start.failed",
                {"server_id": self.id, "error": "EULA not accepted"},
            )
            return

        await self._install_playit()

        try:
            self.logger.info(f"Starting server '{self.id}'...")

            java_opts = [
                f"-Xms{self.config.min_ram}M",
                f"-Xmx{self.config.max_ram}M",
                "-XX:+UseG1GC",
                "-XX:+ParallelRefProcEnabled",
                "-XX:MaxGCPauseMillis=200",
                "-XX:+UnlockExperimentalVMOptions",
                "-XX:+DisableExplicitGC",
                "-XX:+AlwaysPreTouch",
                "-XX:G1NewSizePercent=30",
                "-XX:G1MaxNewSizePercent=40",
                "-XX:G1HeapRegionSize=8M",
                "-XX:G1ReservePercent=20",
                "-XX:G1HeapWastePercent=5",
                "-XX:G1MixedGCCountTarget=4",
                "-XX:InitiatingHeapOccupancyPercent=15",
                "-XX:G1MixedGCLiveThresholdPercent=90",
                "-XX:G1RSetUpdatingPauseTimePercent=5",
                "-XX:SurvivorRatio=32",
                "-XX:+PerfDisableSharedMem",
                "-XX:MaxTenuringThreshold=1",
                "-Dusing.aikars.flags=https://mcflags.emc.gs",
                "-Daikars.new.flags=true",
            ]

            self.process = await asyncio.create_subprocess_exec(
                str(self.java_path),
                *java_opts,
                "-jar",
                self.config.jar_path,
                "nogui",
                cwd=self.path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            self.status = ServerStatus.STARTING
            loop = asyncio.get_running_loop()
            self.started_at = loop.time()
            await self.emit("server.starting", {"server_id": self.id})

            self._output_task = asyncio.create_task(self._read_output())
            self._monitor_task = asyncio.create_task(self._monitor_process())
            if self.config.use_playit:
                await self._start_playit()
                self._output_task_playit = asyncio.create_task(
                    self._read_playit_output()
                )

        except Exception as e:
            self.logger.error(f"Failed to start server '{self.id}': {e}")
            self.status = ServerStatus.OFFLINE
            await self.emit(
                "server.start.failed", {"server_id": self.id, "error": str(e)}
            )

    async def _read_output(self):
        # .stdout is now an asyncio.StreamReader, which is non-blocking
        if not self.process or not self.process.stdout:
            self.logger.error(f"Process or stdout not available for server '{self.id}'")
            return
        while True:
            line = await self.process.stdout.readline()
            if not line:
                break

            decoded_line = line.decode().strip()
            if not decoded_line:
                continue

            await self.emit(
                "server.output", {"server_id": self.id, "line": decoded_line}
            )
            self.console_buffer.append(decoded_line)
            if len(self.console_buffer) > 1000:
                self.console_buffer.pop(0)

            if "Done (" in decoded_line:
                self.status = ServerStatus.ONLINE
                await self.emit("server.online", {"server_id": self.id})

    async def _monitor_process(self):
        """Monitor the server resources and players and tps using function get_metrics every 10 seconds."""
        while self.status in (ServerStatus.STARTING, ServerStatus.ONLINE):
            await self.get_metrics()
            await self.emit(
                "server.metrics",
                {
                    "server_id": self.id,
                    "metrics": (
                        self.metrics.model_dump(mode="json") if self.metrics else None
                    ),
                },
            )
            await asyncio.sleep(2 if self.socket else 30)

    async def _stop_playit(self):
        if self.playit_process:
            self.logger.info(f"Stopping playit.gg tunnel for {self.id}...")
            if self._output_task_playit:
                self._output_task_playit.cancel()
            self.playit_process.kill()
            await self.playit_process.wait()
            self.playit_process = None

    async def stop(self, force: bool = False):
        """Stop the Minecraft server process gracefully."""
        if self.status != ServerStatus.ONLINE or not self.process:
            self.logger.warning(f"Server '{self.id}' is not running.")
            return

        try:
            asyncio.create_task(self._stop_playit())

            if self._output_task:
                self._output_task.cancel()
            if self._monitor_task:
                self._monitor_task.cancel()

            self.logger.info(f"Stopping server '{self.id}'...")
            self.status = ServerStatus.STOPPING
            await self.emit("server.stopping", {"server_id": self.id})
            await self.send_command("save-all")
            await asyncio.sleep(1)
            await self.send_command("stop")
            await self.process.wait()
            self.status = ServerStatus.OFFLINE
            await self.emit("server.stopped", {"server_id": self.id})
        except Exception as e:
            self.logger.error(f"Failed to stop server '{self.id}': {e}")
            if force:
                await self.kill()

    async def restart(self):
        """Restart the Minecraft server process."""
        await self.stop(True)
        await asyncio.sleep(2)
        await self.start()

    async def kill(self):
        """Forcefully kill the Minecraft server process."""
        if self.process and self.status == ServerStatus.ONLINE:
            self.status = ServerStatus.STOPPING
            await self.emit("server.stopping", {"server_id": self.id})
            self.logger.warning(f"Forcefully killing server '{self.id}'...")
            self.process.kill()
            await self.process.wait()
            self.status = ServerStatus.OFFLINE
            await self.emit("server.stopped", {"server_id": self.id})

    async def _start_playit(self):
        """Starts the playit.gg tunnel with an auto-restart watchdog."""
        while self.status in (ServerStatus.STARTING, ServerStatus.ONLINE):
            if not self.config.use_playit:
                break

            self.logger.info("Launching playit.gg tunnel...")
            await self.emit("server.playit.launching", {"server_id": self.id})

            args = [str(self.playit_path)]
            if self.config.playit_secret:
                args.extend(["--secret", self.config.playit_secret.get_secret_value()])

            try:
                self.playit_process = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=self.path,
                )

                self._output_task_playit = asyncio.create_task(
                    self._read_playit_output()
                )

                exit_code = await self.playit_process.wait()

            except Exception as e:
                self.logger.error(f"Playit watchdog error: {e}")

            if self.status in (ServerStatus.STARTING, ServerStatus.ONLINE):
                self.logger.warning(f"Playit process exited. Restarting in 5s...")
                await asyncio.sleep(5)
            else:
                break

    async def _read_playit_output(self):
        """Parses playit logs for claim URLs and secrets."""
        if not self.playit_process or not self.playit_process.stdout:
            return

        while True:
            line = await self.playit_process.stdout.readline()
            if not line:
                break

            decoded_line = line.decode().strip()
            if not decoded_line:
                continue

            await self.emit("server.playit.output", {"line": decoded_line})

            # 1. Capture Claim URL (e.g., https://playit.gg/claim/XXXX-XXXX)
            if "https://playit.gg/claim/" in decoded_line:
                # Extract the actual URL from the line to be precise
                match = re.search(r"(https://playit\.gg/claim/[^\s]+)", decoded_line)
                url = match.group(1) if match else decoded_line
                await self.emit("server.playit.claim_url", {"url": url})
                self.logger.info(f"Playit Claim URL generated: {url}")

            # 2. Capture Secret from log
            if "secret =" in decoded_line or "secret:" in decoded_line:
                match = re.search(
                    r'secret\s*[=:]\s*["\']?(.*?)["\']?(\s|$)', decoded_line
                )
                if match:
                    new_secret = match.group(1).strip()
                    self.config.playit_secret = SecretStr(new_secret)
                    await self.save_config()
                    self.logger.info("Playit secret captured and saved to config.")

    async def send_command(self, command: str):
        """Send a command to the server via RCON without blocking the loop."""
        if not self._rcon:
            # Note: _connect_rcon also needs to be thread-safe or async-wrapped
            await self._connect_rcon()

        if self._rcon:
            async with self._rcon_lock:
                try:
                    response = await asyncio.to_thread(self._rcon.command, command)

                    self.logger.debug(f"RCON Response: {response}")
                    return response
                except Exception as e:
                    self.logger.error(f"RCON Error: {e}")
                    # If it's a network error, clear the connection so it reconnects
                    self._rcon = None
                    return None
        return None

    async def _connect_rcon(self):
        """Establish an RCON connection to the server."""
        try:
            self._rcon = MCRcon(
                "localhost",
                f"{self.config.name}{SECRET_KEY}",
                port=25575,
                timeout=5,
            )
            self._rcon.connect()
            self.logger.info(f"Established RCON connection for server '{self.id}'")
        except Exception as e:
            self.logger.error(
                f"Failed to establish RCON connection for server '{self.id}': {e}"
            )
            self._rcon = None

    async def get_metrics(self) -> Optional[ServerMetricsModel]:
        """Get current server metrics like TPS, player count, and resource usage."""
        if self.status != ServerStatus.ONLINE:
            self.logger.warning(
                f"Cannot get metrics for server '{self.id}' because it is not online."
            )
            return None

        try:
            # Get player count from RCON
            player_task = asyncio.create_task(self.send_command("list"))

            tps_task = asyncio.create_task(self.send_command("spark tps"))

            # Get CPU and RAM usage using psutil
            loop = asyncio.get_running_loop()
            if self.process and self.process.pid:
                proc = psutil.Process(self.process.pid)
                # Use run_in_executor so the 1-second interval happens in a background thread
                cpu_usage = await loop.run_in_executor(None, proc.cpu_percent, 1)
                ram_usage = proc.memory_info().rss // (1024 * 1024)
            else:
                cpu_usage = 0.0
                ram_usage = 0.0

            player_list_response = await player_task
            tps_response = await tps_task

            player_count = 0
            if player_list_response and "There are" in player_list_response:
                match = re.search(
                    r"There are (\d+) of a max \d+ players", player_list_response
                )
                if match:
                    player_count = int(match.group(1))
            tps = None
            if tps_response and "TPS" in tps_response:
                match = re.search(r"TPS: ([\d\.]+)", tps_response)
                if match:
                    tps = float(match.group(1))

            if self.status == ServerStatus.ONLINE and self.started_at is not None:
                # self.started_at should have been set using loop.time()
                uptime_seconds = loop.time() - self.started_at
                uptime = str(timedelta(seconds=int(uptime_seconds)))
            else:
                uptime = "Offline"

            self.logger.debug(
                f"Metrics for server '{self.id}': CPU {cpu_usage}%, RAM {ram_usage}MB, Players {player_count}, TPS {tps}, Uptime {uptime}"
            )

            metrics = ServerMetricsModel(
                player_count=player_count,
                tps=tps,
                cpu_usage=cpu_usage,
                memory_usage=ram_usage,
                uptime=uptime,
            )
            self.metrics = metrics
            return metrics

        except Exception as e:
            self.logger.error(f"Failed to get metrics for server '{self.id}': {e}")
            return None

    async def accept_eula(self):
        """Create eula.txt with eula=true to accept the Minecraft EULA."""
        eula_path = self.path / "eula.txt"
        content = "eula=true"
        async with aiofiles.open(eula_path, "w") as f:
            await f.write(content)
        self.logger.debug(f"Accepted EULA for server '{self.id}' by creating eula.txt")
        self.config.eula_accepted = True
        await self.save_config()

    async def _get_user_data(self, username: str) -> Optional[PlayerDetails]:
        username = username.strip().lower()
        if username in self._cached_user_data:
            return self._cached_user_data[username]

        if not self._session or self._session.closed:
            # Safety fallback: re-open if session was never created
            self._session = aiohttp.ClientSession(headers=self._headers)

        try:
            async with self._session.get(
                f"https://playerdb.co/api/player/minecraft/{username}"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    playerData = PlayerDBResponse(**data)
                    self._cached_user_data[username] = playerData.data.player
                    return playerData.data.player
                logger.warning(
                    f"Failed to fetch UUID for username '{username}': HTTP {resp.status}"
                )
                return None
        except Exception as e:
            self.logger.error(f"Error fetching UUID: {e}")
            return None

    async def _modify_list_file(
        self, filename: str, player_info: PlayerDetails, add: bool = True
    ) -> bool:
        """Helper to add/remove players from server JSON files when offline."""
        file_path = self.path / filename
        data = []

        if file_path.exists():
            async with aiofiles.open(file_path, "r") as f:
                content = await f.read()
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    data = []

        # Check for existing entry by UUID
        existing = next((item for item in data if item["uuid"] == player_info.id), None)

        if add:
            if not existing:
                # Explicitly type the dict as Dict[str, Any]
                new_entry: dict[str, Any] = {
                    "uuid": player_info.id,
                    "name": player_info.username,
                }

                if filename == "ops.json":
                    new_entry["level"] = 4
                    new_entry["bypassesPlayerLimit"] = False

                elif filename == "banned-players.json":
                    new_entry.update(
                        {
                            "created": "2026-04-30 00:00:00 +0000",
                            "source": "Console",
                            "expires": "forever",
                            "reason": "Banned by Admin",
                        }
                    )

                data.append(new_entry)
        else:
            if existing:
                data.remove(existing)

        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(data, indent=4))
        return True

    async def manage_player(self, username: str, action: str) -> bool:
        """
        Universal handler for player management.
        Actions: 'whitelist_add', 'whitelist_remove', 'ban', 'pardon', 'op', 'deop'
        """
        username = username.strip()
        player_data = await self._get_user_data(username)
        if not player_data:
            self.logger.warning(
                f"Could not find player '{username}' for action '{action}'."
            )
            return False

        # Mapping logic
        config = {
            "whitelist_add": ("whitelist add", "whitelist.json", True),
            "whitelist_remove": ("whitelist remove", "whitelist.json", False),
            "ban": ("ban", "banned-players.json", True),
            "pardon": ("pardon", "banned-players.json", False),
            "op": ("op", "ops.json", True),
            "deop": ("deop", "ops.json", False),
        }

        cmd_prefix, filename, should_add = config[action]

        if self.status == ServerStatus.ONLINE:
            response = await self.send_command(f"{cmd_prefix} {username}")
            return response is not None
        else:
            return await self._modify_list_file(filename, player_data, should_add)

    # Clean Public API for your Dashboard
    async def whitelist_player(self, username: str) -> bool:
        return await self.manage_player(username, "whitelist_add")

    async def unwhitelist_player(self, username: str) -> bool:
        return await self.manage_player(username, "whitelist_remove")

    async def ban_player(self, username: str) -> bool:
        return await self.manage_player(username, "ban")

    async def pardon_player(self, username: str) -> bool:
        return await self.manage_player(username, "pardon")

    async def op_player(self, username: str) -> bool:
        return await self.manage_player(username, "op")

    async def deop_player(self, username: str) -> bool:
        return await self.manage_player(username, "deop")

    # TODO: Make Addons Functional and add Backup and Restore functions for server data and configs

    async def add_addon(self, addon: AddonModel):
        """Add an addon to the server's addon config. no need to handle file moving here, just update the config and let the frontend handle the rest."""
        try:
            if self.config.type in (ServerType.VANILLA):
                self.logger.error(
                    f"Server '{self.id}' does not support addons, cannot add addon."
                )
                return

            self.config.addons.append(addon)
            await self.save_config()
            self.logger.info(
                f"Added addon '{addon.project.title} {addon.version.name}' to server '{self.id}' config."
            )

        except Exception as e:
            self.logger.error(f"Failed to add addon: {e}")

    async def remove_addon(self, project_id: str):
        """Remove an addon from the server's addon config based on project and version ID."""
        try:
            addon_to_remove = next(
                (
                    addon
                    for addon in self.config.addons
                    if addon.project.id == project_id
                ),
                None,
            )
            if not addon_to_remove:
                self.logger.warning(
                    f"Addon with project ID '{project_id}' not found in server '{self.id}' config."
                )
                return

            self.config.addons.remove(addon_to_remove)
            await self.save_config()
            self.logger.info(
                f"Removed addon '{addon_to_remove.project.title} {addon_to_remove.version.name}' from server '{self.id}' config."
            )

        except Exception as e:
            self.logger.error(f"Failed to remove addon: {e}")

    @property
    def list_addons(self) -> List[AddonModel]:
        """Return the list of addons currently in the server's config."""
        return self.config.addons

    def export_addons(self) -> List[Dict[str, Any]]:
        """Return the list of addons in a JSON-serializable format."""
        return [addon.model_dump(mode="json") for addon in self.config.addons]

    async def list_untracked_addons(self) -> List[str]:
        """
        Returns a list of filenames on disk that are NOT registered
        in the server configuration.
        """

        def get_disk_state():
            if not self.addon_path.exists():
                return set()
            return {file.name for file in self.addon_path.glob("*.jar")}

        files_on_disk = await asyncio.to_thread(get_disk_state)

        known_filenames = {
            addon.path.name for addon in self.config.addons if addon.path
        }

        untracked_filenames = list(files_on_disk - known_filenames)

        return untracked_filenames

    async def get_online_players(self) -> list[str]:
        """Get a list of online players from the server using RCON."""
        response = await self.send_command("list")

        if not response:
            return []

        # Regex to find the part after the colon
        match = re.search(r"online: (.*)", response)
        if match:
            players_str = match.group(1).strip()
            if not players_str:
                return []
            # Split by comma and clean up whitespace
            return [p.strip() for p in players_str.split(",")]

        return []

    async def export_server(self):
        """Return a dictionary representation of the server instance for API responses."""
        return ServerResponse(
            id=self.id,
            name=self.config.name,
            type=self.config.type,
            version=self.config.version,
            status=self.status,
            min_ram=self.config.min_ram,
            max_ram=self.config.max_ram,
            port=self.config.port,
            players_limit=self.config.players_limit,
            created_at=self.config.created_at,
            started_at=(
                datetime.fromtimestamp(self.started_at) if self.started_at else None
            ),
            jar_path=self.config.jar_path,
            players=await self.get_online_players(),
            # addons=[addon.model_dump(mode="json") for addon in self.config.addons],
            logs=self.console_buffer[-100:],  # Last 100 lines
            use_playit=self.config.use_playit,
            playit_secret=(
                self.config.playit_secret if self.config.playit_secret else None
            ),
        )
