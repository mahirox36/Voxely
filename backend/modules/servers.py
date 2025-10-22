import asyncio
from asyncio.subprocess import Process
from datetime import datetime
from enum import StrEnum
import os
import re
import threading
from typing import List, Dict, Optional, Any, Union
from fastapi import WebSocket
from mcrcon import MCRcon
import time
import psutil
import shutil
import json
import subprocess
import socket
from .jar import MinecraftServerDownloader
from .serverProperties import ServerProperties
from pathlib import Path
import logging
import glob
from dataclasses import dataclass
from contextlib import contextmanager
from .jar import ServerType

# Set up root logger configuration
logger = logging.getLogger("server")
file_handler = logging.FileHandler("logs/server_module.log")
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

loop = asyncio.get_event_loop()

# Cache for server list to improve performance
_server_cache = {
    "servers": [],
    "last_updated": 0,
    "cache_duration": 10,  # Cache duration in seconds
}


class ServerStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    STARTING = "starting"
    STOPPING = "stopping"


def get_servers(space: bool = False, use_cache: bool = True):
    """
    Get list of server names. Uses a cache to improve performance.

    Args:
        space: If True, replaces "_." with space in server names
        use_cache: If True, uses the cached server list if available and not expired

    Returns:
        List of server names
    """
    logger = logging.getLogger("server.get_servers")
    global _server_cache

    # Check if we can use the cached data
    current_time = time.time()
    if (
        use_cache
        and _server_cache["servers"]
        and (
            current_time - _server_cache["last_updated"]
            < _server_cache["cache_duration"]
        )
    ):
        servers = _server_cache["servers"]
        logger.debug(f"Using cached server list, {len(servers)} servers found")
    else:
        # Cache is invalid or not requested, get fresh data
        servers = []
        if not os.path.exists("servers"):
            logger.warning("Servers directory does not exist")
            _server_cache["servers"] = []
            _server_cache["last_updated"] = current_time
            return []

        # Get basic server list from directory names first
        server_dirs = [
            d
            for d in os.listdir("servers")
            if os.path.isdir(os.path.join("servers", d))
        ]
        logger.debug(f"Found {len(server_dirs)} server directories")

        # Process each server in a more optimized way
        for server_dir in server_dirs:
            server_path = os.path.join("servers", server_dir)
            # Check if this is a valid Minecraft server directory
            server_json = os.path.join(server_path, "server.json")
            has_jar = os.path.exists(os.path.join(server_path, "server.jar"))
            has_eula = os.path.exists(os.path.join(server_path, "eula.txt"))

            # Only include directories that have BOTH jar and eula, or a valid server.json
            if os.path.exists(server_json):
                try:
                    with open(server_json, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    # Skip server if it's explicitly marked as invalid
                    if "is_valid_server" in data and data["is_valid_server"] == False:
                        logger.debug(f"Skipping invalid server: {server_dir}")
                        continue
                    servers.append(data["name"])
                    logger.debug(f"Added server {data['name']} from server.json")
                except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
                    # Only add if BOTH jar and eula exist when server.json is invalid
                    if has_jar and has_eula:
                        servers.append(server_dir)
                        logger.warning(
                            f"Error reading server.json for {server_dir}, but found jar/eula: {str(e)}"
                        )
                    else:
                        logger.warning(
                            f"Skipping invalid server {server_dir}: {str(e)}"
                        )
            else:
                # For directories without server.json, BOTH jar and eula must exist
                if has_jar and has_eula:
                    servers.append(server_dir)
                    logger.debug(f"Added server {server_dir} based on jar/eula files")
                else:
                    logger.debug(
                        f"Skipping directory {server_dir} - not a valid Minecraft server (missing jar or eula)"
                    )

        # Update the cache
        _server_cache["servers"] = servers
        _server_cache["last_updated"] = current_time
        logger.info(f"Updated server cache with {len(servers)} servers")

    # Apply space formatting if requested
    if space:
        return [name.replace("_.", " ") for name in servers]
    return servers


def invalidate_server_cache():
    """Force the server cache to be refreshed on next call to get_servers"""
    logger = logging.getLogger("server.invalidate_cache")
    global _server_cache
    _server_cache["last_updated"] = 0
    logger.info("Server cache invalidated")


@dataclass
class ServerMetrics:
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    tps: float = 20.0
    player_count: int = 0
    uptime: str = "Offline"


class Server:
    def __init__(
        self,
        name: str,
        type: ServerType = ServerType.PAPER,
        version: str = "1.21.1",
        min_ram: int = 1024,
        max_ram: int = 1024,
        port: int = 25565,
        players_limit: int = 20,
    ):
        self.name = name
        self.path = Path("servers") / name
        self.full_path = os.path.abspath(self.path)
        self.backup_path = Path("backups") / name
        self._metrics: ServerMetrics = ServerMetrics()
        self._lock = threading.Lock()
        self._shutdown_event = threading.Event()
        self.started_at = None  # Initialize started_at attribute here
        self.websockets: List[WebSocket] = []
        match type:
            case ServerType.PAPER | ServerType.PURPUR:
                self.addon_path = self.path / "plugins"
            case ServerType.FABRIC:
                self.addon_path = self.path / "mods"
            case _:
                self.addon_path = None

        self.serverExists = self.path.exists()
        # Setup logger for this server instance
        self.logger = self._setup_logger()
        self.logger.info(f"Initializing server {name} (type={type}, version={version})")

        self.Properties = ServerProperties(self.path / "server.properties")
        self._rcon: Optional[MCRcon] = None
        self._rcon_lock = threading.Lock()
        self.process: Optional[Process] = None

    @classmethod
    async def init(
        cls,
        name: str,
        type: ServerType = ServerType.PAPER,
        version: str = "1.21.1",
        min_ram: int = 1024,
        max_ram: int = 1024,
        port: int = 25565,
        players_limit: int = 20,
        jar: Optional[str] = None
    ):
        self = cls(name, type, version, min_ram, max_ram, port, players_limit)
        if not self.serverExists:
            self.logger.info(f"Creating new server at {self.path}")
            await self._create_new_server(
                type, version, min_ram, max_ram, port, players_limit, jar
            )
        else:
            await self._load_existing_server()
        return self

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(f"server.{self.name}")
        logger.setLevel(logging.DEBUG)  # Set to DEBUG for more detailed logging

        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)

        # Check if file handler already exists
        has_file_handler = False
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                has_file_handler = True
                break

        if not has_file_handler:
            # Create server log directory if it doesn't exist
            self.path.mkdir(parents=True, exist_ok=True)

            # Add file handler for this server's log file
            file_handler = logging.FileHandler(self.path / "server.log")
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            )
            logger.addHandler(file_handler)

            # Add a separate handler for the combined logs file
            combined_handler = logging.FileHandler("logs/all_servers.log")
            combined_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            logger.addHandler(combined_handler)

        # Prevent propagation to parent loggers to avoid duplicate logging
        logger.propagate = False

        return logger

    @contextmanager
    def rcon_connection(self):
        with self._rcon_lock:  # Use lock to prevent concurrent RCON operations
            try:
                if self._rcon is None:
                    self.logger.debug("Creating new RCON connection")
                    self._rcon = MCRcon(
                        self.ip["private"].split(":")[0],
                        "sdu923rf873bdf4iu53aw2",
                        port=25575,
                    )
                    self._rcon.connect()
                self.logger.debug("Using existing RCON connection")
                yield self._rcon
            except Exception as e:
                self.logger.error(f"RCON connection error: {e}")
                # Close the connection on error to allow retry
                if self._rcon:
                    try:
                        self._rcon.disconnect()
                    except Exception as disconnect_error:
                        self.logger.error(
                            f"Error during RCON disconnect: {disconnect_error}"
                        )
                    self._rcon = None
                raise

    async def backup_server(self) -> Optional[str]:
        self.logger.info("Starting server backup")
        if self.status != ServerStatus.OFFLINE:
            self.logger.debug("Server is online, saving world before backup")
            await self.send_command("save-all")
            time.sleep(2)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_path / f"{self.name}_{timestamp}.zip"

        try:
            self.backup_path.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Creating zip archive at {backup_file}")
            shutil.make_archive(str(backup_file.with_suffix("")), "zip", self.path)
            self.logger.info(f"Created backup: {backup_file}")
            return str(backup_file)
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            return None

    async def restore_backup(self, backup_file: str) -> bool:
        self.logger.info(f"Attempting to restore backup from {backup_file}")
        if self.status != ServerStatus.OFFLINE:
            self.logger.debug("Server is online, stopping before restore")
            await self.stop()

        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                self.logger.error(f"Backup file not found: {backup_file}")
                raise FileNotFoundError(f"Backup file not found: {backup_file}")

            self.logger.debug(f"Removing existing server directory {self.path}")
            shutil.rmtree(self.path)
            self.path.mkdir(parents=True)

            self.logger.debug(f"Extracting backup archive to {self.path}")
            shutil.unpack_archive(backup_file, self.path, "zip")
            self.logger.info(f"Restored backup: {backup_file}")
            return True
        except Exception as e:
            self.logger.error(f"Restore failed: {e}")
            return False

    async def monitor_performance(self):
        self.logger.debug("Starting performance monitoring")
        while not self._shutdown_event.is_set():
            if self.status == ServerStatus.ONLINE:
                metrics = await self.measure_process_usage()
                with self._lock:
                    self._metrics.cpu_usage = metrics["cpu"]
                    self._metrics.memory_usage = metrics["memory"]
                    self._metrics.player_count = await self.lengthPlayers

                    try:
                        with self.rcon_connection() as mcr:
                            tps_data = mcr.command("tps")
                            # Parse TPS data and update metrics
                            if tps_data:
                                match = re.search(r"(\d+\.?\d*)", tps_data)
                                if match:
                                    self._metrics.tps = float(match.group(1))
                                    self.logger.debug(f"TPS: {self._metrics.tps}")
                    except Exception as e:
                        self.logger.debug(f"Failed to get TPS: {e}")
            
            await asyncio.sleep(5)

    async def get_metrics(
        self, as_string: bool = False
    ) -> Union[ServerMetrics, Dict[str, str]]:
        """
        Get current server metrics (CPU, memory, TPS, player count)

        Args:
            as_string: If True, returns values as formatted strings instead of raw numbers

        Returns:
            ServerMetrics object or dictionary with metrics
        """
        self.logger.debug("Getting server metrics")

        try:
            # Update metrics if server is online
            if self.status == ServerStatus.ONLINE:
                # Refresh process metrics
                usage = await self.measure_process_usage()
                with self._lock:
                    self._metrics.cpu_usage = usage["cpu"]
                    self._metrics.memory_usage = usage["memory"]
                    self._metrics.player_count = await self.lengthPlayers

                    # Calculate and format uptime
                    if self.started_at:
                        uptime_seconds = (
                            datetime.now() - self.started_at
                        ).total_seconds()
                        hours, remainder = divmod(int(uptime_seconds), 3600)
                        minutes, seconds = divmod(remainder, 60)
                        self._metrics.uptime = f"{hours}h {minutes}m {seconds}s"
                    else:
                        self._metrics.uptime = "Unknown"

            # Return metrics in requested format
            if as_string:
                return {
                    "cpu_usage": f"{self._metrics.cpu_usage:.1f}%",
                    "memory_usage": f"{self._metrics.memory_usage:.1f} MB",
                    "player_count": (
                        f"{self._metrics.player_count}/{self.players_limit}"
                        if hasattr(self, "players_limit")
                        else "0/0"
                    ),
                    "uptime": (
                        self._metrics.uptime
                        if self.status == ServerStatus.ONLINE
                        else "Offline"
                    ),
                    "tps": (
                        f"{self._metrics.tps:.1f}"
                        if self.status == ServerStatus.ONLINE
                        else "N/A"
                    ),
                }
            return self._metrics

        except Exception as e:
            self.logger.error(f"Error getting metrics: {e}")
            # Return default metrics on error
            if as_string:
                return {
                    "cpu_usage": "0.0%",
                    "memory_usage": "0.0 MB",
                    "player_count": (
                        f"0/{self.players_limit}"
                        if hasattr(self, "players_limit")
                        else "0/0"
                    ),
                    "uptime": "Error",
                    "tps": "N/A",
                }
            return ServerMetrics()

    async def _load_existing_server(self):
        # Check if server.json exists before trying to load it
        server_json_path = self.path / "server.json"

        # First, verify this is actually a valid server directory
        # A valid server directory should at least have either a server.jar file or eula.txt
        has_jar = (self.path / "server.jar").exists()
        has_eula = (self.path / "eula.txt").exists()

        if not server_json_path.exists() and not (has_jar or has_eula):
            self.logger.warning(
                f"Directory {self.name} exists but doesn't appear to be a valid server (no server.json, server.jar, or eula.txt)"
            )
            # Mark this as invalid to prevent it from being included in server lists
            self.status = ServerStatus.OFFLINE
            self.is_valid_server = False
            # Don't create server.json for invalid servers
            return

        # This is a valid server or at least appears to be one
        self.is_valid_server = True

        if not server_json_path.exists():
            # The server directory exists but server.json doesn't - recreate it
            self.logger.warning(
                f"server.json not found for {self.name}, creating default configuration"
            )
            # Set default values
            self.created_at = datetime.now()
            self.status = ServerStatus.OFFLINE
            self.type = ServerType.PAPER
            self.version = "1.20.4"
            self.players_limit = 20
            self.logs = []
            self.min_ram = 1024
            self.max_ram = 2048
            self.port = 25565
            self.started_at = None

            # Save default configuration
            self.data = {
                "name": self.name,
                "created_at": self.created_at.isoformat(),
                "started_at": None,
                "status": self.status,
                "type": self.type,
                "version": self.version,
                "players_limit": self.players_limit,
                "path": str(self.path),
                "jar_path": str(self.path / "server.jar"),
                "min_ram": self.min_ram,
                "max_ram": self.max_ram,
                "full_path": self.full_path,
                "jar_full_path": str(self.path / "server.jar"),
                "port": self.port,
                "players": [],
                "logs": [],
                "is_valid_server": True,
            }
            self._save_server_data()
            return

        # Load the existing server.json
        try:
            self.logger.debug(f"Reading server.json from {server_json_path}")
            json_data = self._safe_load_json(server_json_path)

            # If json_data is None, the file was corrupted but we attempted repair
            if json_data is None:
                self.logger.warning(
                    f"Could not load or repair server.json for {self.name}, using default values"
                )
                # Set default values similar to when the file doesn't exist
                self.created_at = datetime.now()
                self.status = ServerStatus.OFFLINE
                self.type = ServerType.PAPER
                self.version = "1.20.4"
                self.players_limit = 20
                self.logs = []
                self.min_ram = 1024
                self.max_ram = 2048
                self.port = 25565
                self.started_at = None

                # Save default configuration
                self.data = {
                    "name": self.name,
                    "created_at": self.created_at.isoformat(),
                    "started_at": None,
                    "status": self.status,
                    "type": self.type,
                    "version": self.version,
                    "players_limit": self.players_limit,
                    "path": str(self.path),
                    "jar_path": str(self.path / "server.jar"),
                    "min_ram": self.min_ram,
                    "max_ram": self.max_ram,
                    "full_path": self.full_path,
                    "jar_full_path": str(self.path / "server.jar"),
                    "port": self.port,
                    "players": [],
                    "logs": [],
                    "is_valid_server": True if (has_jar and has_eula) else False,
                }
                self._save_server_data()
                return

            # Successfully loaded JSON data
            self.data = json_data

            for key, value in self.data.items():
                if key in ["players"]:
                    continue
                setattr(self, key, value)

            self.logger.debug(
                f"Loaded data for {self.name}: type={self.type}, version={self.version}"
            )

            # Ensure path attributes are str type
            if isinstance(self.path, str):
                self.path = Path(self.path)

            if isinstance(self.full_path, str) and "/" in self.full_path:
                self.full_path = self.full_path.replace("/", os.sep)

            # Ensure jar_path is a string
            if not isinstance(self.jar_path, str) and hasattr(self.jar_path, "__str__"):
                self.jar_path = str(self.jar_path)

            # Fix jar_full_path if needed
            if not isinstance(self.jar_full_path, str) and hasattr(
                self.jar_full_path, "__str__"
            ):
                self.jar_full_path = str(self.jar_full_path)

            if "started_at" in self.data:
                self.started_at = (
                    datetime.fromisoformat(self.data["started_at"])
                    if self.data["started_at"] != None
                    else None
                )

            if await self.is_server_online == False:
                self.logger.debug("Server is not running, updating status to OFFLINE")
                self.data["status"] = ServerStatus.OFFLINE
                self.logs = []
                self.started_at = None
                await self._save_state()
            self.status = ServerStatus.OFFLINE

            # If we got here, it's a valid server
            self.is_valid_server = True
        except Exception as e:
            self.logger.error(f"Error loading server data: {e}", exc_info=True)
            # Fallback to default configuration
            self.status = ServerStatus.OFFLINE
            self.started_at = None
            self.logs = []

            # Mark as invalid if we couldn't load the data
            if not (has_jar or has_eula):
                self.is_valid_server = False

    def _safe_load_json(self, file_path):
        """
        Safely load JSON data from a file with error recovery mechanisms.

        Args:
            file_path: Path to the JSON file

        Returns:
            Parsed JSON data as a dictionary or None if unrecoverable
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing JSON in {file_path}: {e}")

            # Attempt to repair the JSON file
            backup_path = f"{file_path}.bak"
            self.logger.info(f"Creating backup of corrupted file at {backup_path}")
            try:
                shutil.copy2(file_path, backup_path)

                # Read the raw content
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Try to fix common JSON issues
                repaired_content = self._repair_json(content, e)
                if repaired_content:
                    # Save the repaired content
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(repaired_content)

                    # Try to parse again
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            return json.load(f)
                    except json.JSONDecodeError as e2:
                        self.logger.error(f"Failed to parse JSON after repair: {e2}")
            except Exception as e3:
                self.logger.error(f"Error during JSON repair attempt: {e3}")

            return None
        except Exception as e:
            self.logger.error(f"Unexpected error reading {file_path}: {e}")
            return None

    def _repair_json(self, content, error):
        """
        Attempt to repair corrupted JSON content

        Args:
            content: The JSON string content
            error: The JSONDecodeError that occurred

        Returns:
            Repaired JSON string or None if repair failed
        """
        self.logger.info(f"Attempting to repair JSON content at position {error.pos}")

        try:
            # Convert linebreak style to consistent format
            content = content.replace("\r\n", "\n")

            # Common repair strategies

            # 1. Fix missing closing braces/brackets
            if "Expecting ',' delimiter" in str(
                error
            ) or "Expecting property name" in str(error):
                # Count opening and closing braces/brackets
                open_braces = content.count("{")
                close_braces = content.count("}")
                open_brackets = content.count("[")
                close_brackets = content.count("]")

                # Add missing closing characters
                if open_braces > close_braces:
                    content = content.rstrip() + ("}" * (open_braces - close_braces))
                if open_brackets > close_brackets:
                    content = content.rstrip() + (
                        "]" * (open_brackets - close_brackets)
                    )

            # 2. Fix trailing commas
            if "Expecting property name" in str(error):
                content = content.replace(",}", "}")
                content = content.replace(",\n}", "\n}")
                content = content.replace(",]", "]")
                content = content.replace(",\n]", "\n]")

            # 3. Fix missing quotes around property names
            if "Expecting property name enclosed in double quotes" in str(error):
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if ":" in line:
                        # Find property names without quotes
                        parts = line.split(":", 1)
                        key = parts[0].strip()
                        if not (key.startswith('"') and key.endswith('"')):
                            # Add quotes around the property name
                            lines[i] = line.replace(key, f'"{key}"', 1)
                content = "\n".join(lines)

            # Validate the repaired content
            try:
                json.loads(content)
                self.logger.info("JSON repair successful")
                return content
            except json.JSONDecodeError as e:
                self.logger.warning(f"Initial repair attempt failed: {e}")

                # More aggressive approach - remove the problematic line
                if hasattr(e, "lineno") and e.lineno > 0:
                    lines = content.split("\n")
                    problematic_line = e.lineno - 1  # 0-based index

                    if 0 <= problematic_line < len(lines):
                        self.logger.warning(
                            f"Removing problematic line: {lines[problematic_line]}"
                        )
                        del lines[problematic_line]
                        content = "\n".join(lines)

                        # Try parsing again
                        try:
                            json.loads(content)
                            self.logger.info(
                                "JSON repair successful after removing problematic line"
                            )
                            return content
                        except:
                            pass

                # Final attempt - create minimal valid JSON with core fields
                try:
                    # Extract essential fields using regex patterns
                    import re

                    name_match = re.search(r'"name"\s*:\s*"([^"]+)"', content)
                    name = name_match.group(1) if name_match else self.name

                    # Create a minimal valid JSON
                    minimal_json = {
                        "name": name,
                        "created_at": datetime.now().isoformat(),
                        "started_at": None,
                        "status": "offline",
                        "type": "paper",
                        "version": "1.20.4",
                        "path": str(self.path),
                        "is_valid_server": True,
                    }

                    self.logger.info("Created minimal valid JSON as a last resort")
                    return json.dumps(minimal_json, indent=4)
                except Exception as e:
                    self.logger.error(f"Failed to create minimal valid JSON: {e}")
                    return None

        except Exception as e:
            self.logger.error(f"Error during JSON repair: {e}")
            return None

    @property
    async def players(self) -> List[str]:
        return await self.get_players()

    async def _create_new_server(
        self,
        type: ServerType = ServerType.PAPER,
        version: str = "1.21.1",
        min_ram: int = 1024,
        max_ram: int = 1024,
        port: int = 25565,
        players_limit: int = 20,
        jar: Optional[str] = None
    ):
        self.logger.info(
            f"Creating new server: type={type}, version={version}, ram={min_ram}-{max_ram}MB, port={port}"
        )
        self.created_at = datetime.now()
        self.status = ServerStatus.OFFLINE
        self.type = type
        self.version = version
        self.players_limit = players_limit
        self.logs = []
        self.min_ram = min_ram
        self.max_ram = max_ram
        self.port = port
        self.jar = jar

        # Create the server directory
        self.path.mkdir(parents=True, exist_ok=True)

        # Download the server JAR file
        self.logger.info(f"Downloading JAR for {type} version {version}")
        self.jar_path = self._download_jar(type, version, jar)

        self.logger.debug(f"Download returned jar_path: {self.jar_path}")

        if isinstance(self.jar_path, Path) or isinstance(self.jar_path, str):
            self.jar_full_path = os.path.join(
                self.full_path, os.path.basename(str(self.jar_path))
            )
            self.logger.info(f"JAR file path: {self.jar_full_path}")
        else:
            self.logger.error(f"Failed to download JAR file: {self.jar_path}")
            self.jar_full_path = os.path.join(self.full_path, "server.jar")
            self.logger.warning(f"Using default JAR path: {self.jar_full_path}")

        self.data = {
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at,
            "status": self.status,
            "type": self.type,
            "version": self.version,
            "players_limit": self.players_limit,
            "path": str(self.path),
            "jar_path": str(self.jar_path),
            "min_ram": self.min_ram,
            "max_ram": self.max_ram,
            "full_path": self.full_path,
            "jar_full_path": self.jar_full_path,
            "port": self.port,
            "players": await self.players,
            "logs": self.logs,
        }

        self._save_server_data()

        # Create default server.properties file
        self.logger.debug("Creating default server.properties file")
        with open(self.path / "server.properties", "w") as f:
            f.write(
                f"""motd={self.name}
max-players={players_limit}
server-port={port}
enable-rcon=true
rcon.password=sdu923rf873bdf4iu53aw2
                    """
            )

    @property
    async def lengthPlayers(self):
        return len(await self.players)

    def _download_jar(self, server_type: ServerType, version: str, jar: Optional[str] = None):
        """Download the server JAR file for the specified type and version."""
        self.logger.info(
            f"Downloading server JAR: type={server_type}, version={version}"
        )
        downloader = MinecraftServerDownloader()

        try:
            # Check if the JAR file already exists in the versions directory
            potential_jar_files = []
            if server_type == ServerType.VANILLA:
                potential_jar_files.append(f"versions/vanilla-{version}.jar")
            elif server_type == ServerType.PAPER:
                # Paper JAR files can have different build numbers, check for any that match the version
                potential_jar_files = glob.glob(f"versions/paper-{version}-*.jar")
            elif server_type == ServerType.FABRIC:
                potential_jar_files = glob.glob(
                    f"versions/fabric-server-mc{version}-*.jar"
                )

            # If we found an existing JAR file, use it
            for jar_path in potential_jar_files:
                if os.path.exists(jar_path) and os.path.getsize(jar_path) > 0:
                    self.logger.info(f"Using existing JAR file: {jar_path}")
                    # Copy the existing JAR to the server directory
                    dest_path = self.path / "server.jar"
                    shutil.copy2(jar_path, dest_path)
                    self.logger.info(f"Copied existing JAR to {dest_path}")
                    return dest_path

            # No existing JAR found, download a new one
            jar_path = None
            if server_type == ServerType.VANILLA:
                self.logger.debug(f"Downloading Vanilla server JAR version {version}")
                jar_path = downloader.downloadVanilla(version)
            elif server_type == ServerType.PAPER:
                self.logger.debug(f"Downloading Paper server JAR version {version}")
                jar_path = downloader.downloadPaper(version)
            elif server_type == ServerType.FABRIC:
                self.logger.debug(f"Downloading Fabric server JAR version {version}")
                jar_path = downloader.downloadFabric(version)
            elif server_type == ServerType.PURPUR:
                self.logger.debug(f"Downloading Fabric server JAR version {version}")
                jar_path = downloader.downloadPurpur(version)
            elif server_type == ServerType.CUSTOM and jar:
                self.logger.debug(f"Downloading Fabric server JAR version {version}")
                jar_path = jar
            else:
                self.logger.error(f"Unsupported server type: {type}")
                return False

            self.logger.debug(
                f"JAR download result: {jar_path} (type: {type(jar_path).__name__})"
            )

            if not jar_path or not isinstance(jar_path, str):
                self.logger.error(
                    f"Failed to download {type} server JAR for version {version}: {jar_path}"
                )
                return False

            # Copy JAR to server directory
            dest_path = self.path / "server.jar"
            try:
                self.logger.debug(f"Copying JAR from {jar_path} to {dest_path}")

                shutil.copy2(jar_path, dest_path)

                # Verify the file was copied correctly
                if os.path.exists(dest_path):
                    src_size = os.path.getsize(jar_path)
                    dest_size = os.path.getsize(dest_path)
                    self.logger.info(
                        f"JAR file copied: source size={src_size}, destination size={dest_size}"
                    )
                    if src_size != dest_size:
                        self.logger.warning(
                            f"Size mismatch after copy! Source: {src_size}, Destination: {dest_size}"
                        )
                else:
                    self.logger.error(
                        f"Destination file {dest_path} does not exist after copy!"
                    )

                return dest_path
            except Exception as e:
                self.logger.error(f"Failed to copy JAR file: {e}", exc_info=True)
                return False
        except Exception as e:
            self.logger.error(f"Error in _download_jar: {str(e)}", exc_info=True)
            return False

    @property
    async def is_server_online(self) -> bool:
        # Check process
        if not self.process or self.process.returncode is not None:
            self.status = ServerStatus.OFFLINE
            self.started_at = None
            return False

        # Async socket check
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
            writer.close()
            await writer.wait_closed()
            if self.status == ServerStatus.STARTING:
                self.status = ServerStatus.ONLINE
                if not self.started_at:
                    self.started_at = datetime.now()
            return True
        except (ConnectionRefusedError, OSError):
            if self.status not in [ServerStatus.STARTING, ServerStatus.STOPPING]:
                self.status = ServerStatus.OFFLINE
                self.started_at = None
            return False

    def _save_server_data(self):
        """Save server data to server.json file."""
        server_json_path = self.path / "server.json"
        self.logger.debug(f"Saving server data to {server_json_path}")
        try:
            with open(server_json_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
            self.logger.debug("Server data saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving server data: {e}")

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

    async def measure_process_usage(self):
        """Measure CPU and memory usage of the Java process (async-safe)"""
        if self.status != ServerStatus.ONLINE:
            return {"cpu": 0.0, "memory": 0.0}

        def get_usage():
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                if proc.info["name"] and "java" in proc.info["name"].lower():
                    cmdline = " ".join(proc.info["cmdline"] or [])
                    if str(self.path) in cmdline or self.name in cmdline:
                        cpu_percent = proc.cpu_percent(interval=0.5)
                        memory_info = proc.memory_full_info()
                        memory_mb = memory_info.vms / (1024 * 1024)
                        return {"cpu": cpu_percent, "memory": memory_mb}
            return {"cpu": 0.0, "memory": 0.0}

        try:
            return await asyncio.to_thread(get_usage)
        except Exception as e:
            self.logger.error(f"Error measuring process usage: {e}")
            return {"cpu": 0.0, "memory": 0.0}

    async def _save_state(self):
        self.data["status"] = self.status
        self.data["players"] = await self.players
        self.data["logs"] = self.logs
        self.data["started_at"] = (
            self.started_at.isoformat() if self.started_at != None else None
        )
        self._save_server_data()

    async def get_players(self) -> List[str]:
        if await self.is_server_online:
            try:
                with self.rcon_connection() as mcr:
                    response = mcr.command("list")
                    # Parse the response to extract player count and names
                    if response:
                        match = re.search(
                            r"There are (\d+) of a max of \d+ players online: (.+)",
                            response,
                        )
                        if match:
                            player_count = int(match.group(1))
                            player_names = match.group(2).split(", ")
                            self.logger.debug(
                                f"Current players ({player_count}): {', '.join(player_names)}"
                            )
                            return player_names
                        self.logger.debug("No players online")
                        return []
                    self.logger.debug("Empty response from list command")
                    return []
            except Exception as e:
                self.logger.error(f"Error using RCON to get player list: {e}")
                return []
        return []

    def accept_eula(self):
        self.logger.info("Accepting Minecraft EULA")
        try:
            with open(self.path / "eula.txt", "w", encoding="utf-8") as f:
                f.write("eula=true")
            self.logger.debug("EULA accepted")
        except Exception as e:
            self.logger.error(f"Failed to write eula.txt: {e}")

    def append_websocket(self, websocket: WebSocket):
        self.websockets.append(websocket)

    def remove_websocket(self, websocket: WebSocket):
        self.websockets.remove(websocket)

    async def send_websocket(self, data: Any):
        self.logger.info(self.websockets)
        for websocket in self.websockets:
            try:
                await websocket.send_json(data)
            except:
                self.remove_websocket(websocket)

    async def start(self):
        if self.status != ServerStatus.OFFLINE:
            self.logger.warning(f"Cannot start server, current status is {self.status}")
            return

        self.logger.info(f"Starting server {self.name}")

        # Check if server JAR exists
        jar_path = Path(self.jar_full_path)
        if not jar_path.exists():
            self.logger.error(f"Server JAR file not found at {jar_path}")
            # Try to download again
            self.logger.info(
                f"Attempting to download JAR file again for {self.type} version {self.version}"
            )
            jar_result = self._download_jar(self.type, self.version, self.jar)
            if not jar_result:
                self.logger.error("Failed to download JAR file, cannot start server")
                return
            else:
                self.logger.info(f"JAR downloaded successfully to {jar_result}")
        else:
            self.logger.debug(
                f"Server JAR file exists at {jar_path} (size: {os.path.getsize(jar_path)} bytes)"
            )

        # Accept EULA if not already accepted
        eula_path = self.path / "eula.txt"
        if not eula_path.exists():
            self.logger.info("EULA not accepted yet, accepting now")
            self.accept_eula()

        self.status = ServerStatus.STARTING
        await self._save_state()
        await self.send_websocket({"type": "status", "data": "starting"})
        self._shutdown_event.clear()

        java_opts = [
            f"-Xmx{self.max_ram}M",
            f"-Xms{self.min_ram}M",
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

        start_command = f'java {" ".join(java_opts)} -jar "{self.jar_full_path}" nogui'
        self.logger.info(f"Starting server with command: {start_command}")

        try:
            self.process = await asyncio.create_subprocess_exec(
                "java",
                *java_opts,
                "-jar",
                str(self.jar_full_path),
                "nogui",
                cwd=self.path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            self.logger.info(f"Started process with PID {self.process.pid}")
        except Exception as e:
            self.logger.error(f"Failed to start server process: {e}", exc_info=True)
            self.status = ServerStatus.OFFLINE
            await self._save_state()
            await self.send_websocket({"type": "status", "data": "offline"})
            return

        self.output_task = asyncio.create_task(self._capture_output())
        

        # Start performance monitoring
        asyncio.create_task(self.monitor_performance())

    async def _capture_output(self):
        if not self.process or not self.process.stdout:
            self.logger.error("Cannot capture output: process or stdout is None")
            return

        self.logger.debug("Started output capture task")
        self.logs = []

        while True:
            line_bytes = await self.process.stdout.readline()
            if not line_bytes:  # EOF
                break
            line = line_bytes.decode().strip()
            if not line:
                continue

            self.logs.append(line)
            self.logger.debug(f"Server output: {line}")

            # Broadcast to WebSocket
            if hasattr(self, "output_callback") and self.output_callback:
                await self.output_callback(line)  # no need for run_coroutine_threadsafe

            # Check for EULA warning
            if "You need to agree to the EULA" in line:
                self.logger.info("EULA needs to be accepted")
                self.eula_needs_acceptance = True

            # Detect server state
            if "Done" in line:
                self.logger.info("Server reported as fully started")
                self.status = ServerStatus.ONLINE
                self.started_at = datetime.now()
                await self._save_state()
                await self.send_websocket({"type": "status", "data": "online"})
            
            if "joined the game" in line:
                await self.send_websocket({"type": "player_update", "data" : await self.players})
            
            if "left the game" in line:
                await self.send_websocket({"type": "player_update", "data" : await self.players})
                

            # Handle startup failure cases
            elif "Failed to start the minecraft server" in line:
                self.logger.error("Server failed to start")
                self.status = ServerStatus.OFFLINE
                await self._save_state()
            elif "Error occurred during initialization of VM" in line:
                self.logger.error(
                    "JVM initialization error - likely incorrect memory settings"
                )
                self.status = ServerStatus.OFFLINE
                await self._save_state()

        self.logger.info("Server process has terminated")
        self.status = ServerStatus.OFFLINE
        self.started_at = None
        await self._save_state()

    def set_output_callback(self, callback):
        """Set a callback function that will be called for each console output line.
        The callback should be an async function that takes a string parameter."""
        self.logger.debug("Setting output callback")
        self.output_callback = callback

        # Send the last few log lines to catch up the client with recent history
        if hasattr(self, "logs") and self.logs and callable(callback):
            self.logger.debug(
                f"Sending last {min(50, len(self.logs))} log lines to new client"
            )
            for line in self.logs[-50:]:  # Send the last 50 lines to the new connection
                if asyncio.iscoroutinefunction(callback):
                    asyncio.run_coroutine_threadsafe(callback(line), loop)
                else:
                    self.logger.error("Provided callback is not a coroutine function")

    async def get_usage(self):
        usage = await self.measure_process_usage()
        return f"CPU: {usage['cpu']:.1f}%, Memory: {usage['memory']:.1f} MB"

    async def stop(self):
        if self.status not in [ServerStatus.OFFLINE, ServerStatus.STOPPING]:
            self.logger.info(f"Stopping server {self.name}")
            self._shutdown_event.set()
            self.started_at = None
            self.status = ServerStatus.STOPPING
            await self._save_state()
            await self.send_websocket({"type": "status", "data": "stopping"})

            try:
                self.logger.debug("Attempting to save world and stop server via RCON")
                with self.rcon_connection() as mcr:
                    mcr.command("save-all")
                    time.sleep(2)
                    mcr.command("stop")
                # close rcon connection
                if self._rcon:
                    self._rcon.disconnect()
                    self._rcon = None
                self.logger.info("Server stop command sent via RCON")
            except Exception as e:
                self.logger.warning(
                    f"Failed to stop server via RCON: {e}. Terminating process."
                )
                if self.process:
                    self.process.terminate()

            self.logger.debug("Waiting for output thread to complete")
            try:
                await asyncio.wait_for(self.output_task, timeout=30)
            except asyncio.TimeoutError:
                self.logger.warning("Output thread did not exit, killing process")

                if self.process:
                    self.process.kill()
            if not self.output_task.done():
                self.output_task.cancel()
                try:
                    await self.output_task
                except asyncio.CancelledError:
                    pass

            self.logger.info("Server stopped")
            self.status = ServerStatus.OFFLINE
            await self._save_state()
            await self.send_websocket({"type": "status", "data": "offline"})

    async def kill(self):
        if self.status in [ServerStatus.ONLINE, ServerStatus.STARTING]:
            self.logger.info(f"Force-killing server {self.name}")
            self.status = ServerStatus.STOPPING
            await self._save_state()
            if self.process:
                self.process.terminate()

            if self.output_task and not self.output_task.done():
                self.output_task.cancel()

            self.status = ServerStatus.OFFLINE
            await self._save_state()
            self.logger.info("Server killed")

    async def restart(self):
        self.logger.info(f"Restarting server {self.name}")
        await self.stop()
        await self.start()

    async def delete(self):
        self.logger.info(f"Deleting server {self.name}")
        await self.stop()
        try:
            shutil.rmtree(self.path)
            self.logger.info(f"Server directory {self.path} removed")
        except Exception as e:
            self.logger.error(f"Failed to delete server directory: {e}")

    async def send_command(self, command: str):
        if self.process and self.process.returncode is None and self.process.stdin:
            self.logger.debug(f"Sending command: {command}")
            try:
                self.process.stdin.write((command + "\n").encode())
                await self.process.stdin.drain()
                self.logger.debug("Command sent successfully")
            except Exception as e:
                self.logger.error(f"Failed to send command: {e}")

    @property
    def ip(self):
        try:
            hostname = socket.gethostname()
            private_ip = f"{socket.gethostbyname(hostname)}:{self.port}"
            public_ip = f"{subprocess.check_output(['curl', '-s', 'ifconfig.me'],stderr=subprocess.DEVNULL).decode('utf-8').strip()}:{self.port}"
            self.logger.debug(
                f"Server IP addresses - private: {private_ip}, public: {public_ip}"
            )
            return {"private": private_ip, "public": public_ip}
        except Exception as e:
            self.logger.error(f"Error getting IP addresses: {e}")
            return {
                "private": f"localhost:{self.port}",
                "public": f"unknown:{self.port}",
            }

    def get_player_stats(self, player_name: str) -> Dict[str, Any]:
        stats_path = self.path / "world" / "stats" / f"{player_name}.json"
        self.logger.debug(f"Looking for player stats at {stats_path}")
        if stats_path.exists():
            try:
                with open(stats_path) as f:
                    stats = json.load(f)
                self.logger.debug(f"Found stats for {player_name}")
                return stats
            except Exception as e:
                self.logger.error(f"Error reading player stats: {e}")
        else:
            self.logger.debug(f"No stats file found for {player_name}")
        return {}

    def whitelist_add(self, player_name: str) -> bool:
        self.logger.info(f"Adding {player_name} to whitelist")
        try:
            with self.rcon_connection() as mcr:
                response = mcr.command(f"whitelist add {player_name}")
                success = "Added" in response
                self.logger.debug(
                    f"Whitelist add result: {success} (response: {response})"
                )
                return success
        except Exception as e:
            self.logger.error(f"Failed to add player to whitelist: {e}")
            return False

    def whitelist_remove(self, player_name: str) -> bool:
        self.logger.info(f"Removing {player_name} from whitelist")
        try:
            with self.rcon_connection() as mcr:
                response = mcr.command(f"whitelist remove {player_name}")
                success = "Removed" in response
                self.logger.debug(
                    f"Whitelist remove result: {success} (response: {response})"
                )
                return success
        except Exception as e:
            self.logger.error(f"Failed to remove player from whitelist: {e}")
            return False

    def ban_player(self, player_name: str, reason: str = "") -> bool:
        self.logger.info(
            f"Banning player {player_name}" + (f" for: {reason}" if reason else "")
        )
        try:
            with self.rcon_connection() as mcr:
                response = mcr.command(f"ban {player_name} {reason}")
                success = "Banned" in response
                self.logger.debug(f"Ban result: {success} (response: {response})")
                return success
        except Exception as e:
            self.logger.error(f"Failed to ban player: {e}")
            return False

    def unban_player(self, player_name: str) -> bool:
        self.logger.info(f"Unbanning player {player_name}")
        try:
            with self.rcon_connection() as mcr:
                response = mcr.command(f"pardon {player_name}")
                success = "Unbanned" in response
                self.logger.debug(f"Unban result: {success} (response: {response})")
                return success
        except Exception as e:
            self.logger.error(f"Failed to unban player: {e}")
            return False

    def __str__(self):
        return f"Server {self.name} is {self.status}"
