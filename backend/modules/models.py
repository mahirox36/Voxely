"""
Modular models and enums for Voxely server management.

This module provides Pydantic models and enums for type safety and validation.
"""

from enum import StrEnum
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
from pydantic import BaseModel, Field, HttpUrl, SecretStr

from modules.modrinth import Project, Version


class ServerType(StrEnum):
    """Available Minecraft server types."""
    VANILLA = "vanilla"
    FABRIC = "fabric"
    PAPER = "paper"
    PURPUR = "purpur"
    FORGE = "forge"
    NEOFORGE = "neoforge"


class ServerStatus(StrEnum):
    """Server lifecycle states."""
    ONLINE = "online"
    OFFLINE = "offline"
    STARTING = "starting"
    STOPPING = "stopping"


class AddonType(StrEnum):
    """Types of server add-ons (mods, plugins)."""
    MOD = "mod"
    PLUGIN = "plugin"


# ============================================================================
# Pydantic Models
# ============================================================================


class AddonModel(BaseModel):
    """Represents a single addon (mod/plugin) with its metadata."""
    project: Any = Field(..., description="Modrinth project")
    version: Any = Field(..., description="Modrinth version")
    path: Path = Field(..., description="Local filesystem path to addon file")
    addon_type: AddonType = Field(..., description="Type of addon (mod/plugin)")

    class Config:
        use_enum_values = False


class ServerMetricsModel(BaseModel):
    """Server performance metrics."""
    cpu_usage: float = Field(default=0.0, ge=0, le=100, description="CPU usage percentage")
    memory_usage: float = Field(default=0.0, ge=0, description="Memory usage in MB")
    tps: Optional[float] = Field(default=None, ge=0, le=20, description="Ticks per second")
    player_count: int = Field(default=0, ge=0, description="Current player count")
    uptime: str = Field(default="Offline", description="Human-readable uptime")
    timestamp: datetime = Field(default_factory=datetime.now, description="Metric timestamp")


class BackupConfig(BaseModel):
    enabled: bool = False
    interval_hours: int = Field(default=24, ge=1)
    max_backups: int = Field(default=5, ge=1)
    last_backup: Optional[datetime] = None

class ServerConfigModel(BaseModel):
    """Server configuration and metadata."""
    id: str = Field(..., description="Unique server ID (UUID)")
    name: str = Field(..., min_length=1, max_length=32, description="Server name")
    type: ServerType = Field(default=ServerType.PAPER, description="Server type")
    version: str = Field(default="1.21.10", description="Minecraft version")
    
    # Resource allocation
    min_ram: int = Field(default=1024, ge=512, le=131072, description="Minimum RAM in MB")
    max_ram: int = Field(default=2048, ge=512, le=131072, description="Maximum RAM in MB")
    port: int = Field(default=25565, ge=1024, le=65535, description="Server port")
    players_limit: int = Field(default=20, ge=1, le=255, description="Max player count")

    # Lifecycle
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Last start timestamp")
    
    # Paths
    jar_path: Optional[str] = Field(default=None, description="Path to server JAR")
    
    # Content
    players: List[str] = Field(default_factory=list, description="Online players")
    addons: List[AddonModel] = Field(default_factory=list, description="Installed addons")
    eula_accepted: bool = Field(default=False, description="Whether EULA has been accepted")
    
    # Playit.gg integration
    use_playit: Optional[bool] = Field(default=True, description="Whether this server uses Playit.gg for tunneling")
    playit_secret: Optional[SecretStr] = Field(
        default=None, 
        description="The secret key for playit.gg tunneling"
    )
    
    backup: BackupConfig = Field(default_factory=BackupConfig)

    class Config:
        use_enum_values = False

class ServerResponse(BaseModel):
    """Server configuration and metadata."""
    id: str = Field(..., description="Unique server ID (UUID)")
    name: str = Field(..., min_length=1, max_length=32, description="Server name")
    type: ServerType = Field(default=ServerType.PAPER, description="Server type")
    version: str = Field(default="1.21.10", description="Minecraft version")
    status: ServerStatus = Field(default=ServerStatus.OFFLINE, description="Current status")
    
    # Resource allocation
    min_ram: int = Field(default=1024, ge=512, le=131072, description="Minimum RAM in MB")
    max_ram: int = Field(default=2048, ge=512, le=131072, description="Maximum RAM in MB")
    port: int = Field(default=25565, ge=1024, le=65535, description="Server port")
    players_limit: int = Field(default=20, ge=1, le=255, description="Max player count")

    # Lifecycle
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Last start timestamp")
    
    jar_path: Optional[str] = Field(default=None, description="Path to server JAR")
    
    # Content
    players: List[str] = Field(default_factory=list, description="Online players")
    # addons: List[AddonModel] = Field(default_factory=list, description="Installed addons")
    logs: List[str] = Field(default_factory=list, description="Recent console logs")
    
    eula_accepted: bool = Field(default=False, description="Whether EULA has been accepted")
    
    # Playit.gg integration
    use_playit: Optional[bool] = Field(default=True, description="Whether this server uses Playit.gg for tunneling")
    playit_secret: Optional[SecretStr] = Field(
        default=None, 
        description="The secret key for playit.gg tunneling"
    )
    
    backup: BackupConfig = Field(default_factory=BackupConfig, description="Backup configuration")
    metrics: Optional[ServerMetricsModel] = Field(default=None, description="Latest server performance metrics")
    

    class Config:
        use_enum_values = False

class ServerCreationRequest(BaseModel):
    """Request model for creating a new server."""
    name: str = Field(..., min_length=1, max_length=32, description="Server name")
    type: ServerType = Field(default=ServerType.PAPER, description="Server type")
    version: str = Field(default="1.20.4", description="Minecraft version")
    min_ram: int = Field(default=1024, ge=512, le=131072, description="Minimum RAM in MB")
    max_ram: int = Field(default=2048, ge=512, le=131072, description="Maximum RAM in MB")
    port: int = Field(default=25565, ge=1024, le=65535, description="Server port")
    players_limit: int = Field(default=20, ge=1, le=255, description="Max player count")
    
    class Config:
        use_enum_values = False


class ServerImportRequest(BaseModel):
    """Request model for importing a server from ZIP."""
    name: str = Field(..., min_length=1, max_length=32, description="Server name")
    zip_path: str = Field(..., description="Path to ZIP or Mrpack file")
    detect_type: bool = Field(default=True, description="Auto-detect server type from contents")
    

class WebSocketEvent(BaseModel):
    """WebSocket event for real-time communication."""
    event: str = Field(..., description="Event type")
    data: Any = Field(default=None, description="Event payload")
    timestamp: datetime = Field(default_factory=datetime.now, description="Event timestamp")


# ============================================================================
# Helper Functions
# ============================================================================


def get_addon_type_for_server(server_type: ServerType) -> Optional[AddonType]:
    """Determine if a server type supports addons and what type."""
    if server_type in (ServerType.PAPER, ServerType.PURPUR):
        return AddonType.PLUGIN
    elif server_type in (ServerType.FABRIC, ServerType.FORGE, ServerType.NEOFORGE):
        return AddonType.MOD
    return None


def get_addon_directory_name(addon_type: Optional[AddonType]) -> str:
    """Get the directory name for storing addons of a given type."""
    if addon_type == AddonType.MOD:
        return "mods"
    elif addon_type == AddonType.PLUGIN:
        return "plugins"
    return "addons"

# PlayerDB
class PlayerProperty(BaseModel):
    name: str
    value: str
    signature: Optional[str] = None

class PlayerMeta(BaseModel):
    cached_at: int

class PlayerDetails(BaseModel):
    meta: PlayerMeta
    username: str
    id: str  # Full UUID with dashes
    raw_id: str  # Trimmed UUID
    avatar: HttpUrl
    skin_texture: HttpUrl
    properties: List[PlayerProperty]
    name_history: List[str] = []

class PlayerData(BaseModel):
    player: PlayerDetails

class PlayerDBResponse(BaseModel):
    code: str
    message: str
    data: PlayerData
    success: bool