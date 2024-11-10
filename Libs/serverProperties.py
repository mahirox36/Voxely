from dataclasses import asdict, dataclass, field
from typing import Any, Dict, NewType, Optional
from rich import print

@dataclass(frozen=True)
class Gamemode:
    survival: str = "survival"
    creative: str = "creative"
    adventure: str = "adventure"
    spectator: str = "spectator"


@dataclass(frozen=True)
class Difficulty:
    peaceful: str = "peaceful"
    easy: str = "easy"
    normal: str = "normal"
    hard: str = "hard"


@dataclass(frozen=True)
class LevelType:
    normal: str = "minecraft:normal"
    flat: str = "minecraft:flat"
    large_biomes: str = "minecraft:large_biomes"
    amplified: str = "minecraft:amplified"
    customized: str = "minecraft:customized"


@dataclass(frozen=True)
class ResourcePack:
    none: str = ""
    vanilla: str = "vanilla"
    custom: str = "custom"

    
@dataclass
class Properties:
    # Basic server information
    motd: str = "A Minecraft Server"
    server_name: str = "Minecraft Server"
    level_name: str = "world"
    level_seed: Optional[str] = None
    level_type: LevelType = LevelType().normal
    max_players: int = 20
    
    # Server behavior settings
    gamemode: Gamemode = Gamemode().survival
    force_gamemode: bool = False
    difficulty: Difficulty = Difficulty().easy
    hardcore: bool = False
    pvp: bool = True
    allow_nether:bool = True
    spawn_protection: int = 16
    allow_flight: bool = False
    enable_command_block: bool = False
    white_list: bool = False
    
    # World generation settings
    generate_structures: bool = True
    generator_settings: str = "{}"
    
    # Spawn settings
    spawn_animals: bool = True
    spawn_monsters: bool = True
    spawn_npcs: bool = True

    # Performance settings
    view_distance: int = 10
    simulation_distance: int = 10
    max_tick_time: int = 60000
    entity_broadcast_range_percentage: int = 100
    max_chained_neighbor_updates: int = 1000000
    max_world_size: int = 29999984
    sync_chunk_writes: bool = True

    # Permissions and access settings
    op_permission_level: int = 4
    function_permission_level: int = 2
    player_idle_timeout: int = 0  # 0 for no timeout
    broadcast_console_to_ops: bool = True
    broadcast_rcon_to_ops: bool = True
    enforce_whitelist: bool = False
    enforce_secure_profile: bool = True

    # Network settings
    server_ip: Optional[str] = None
    server_port: int = 25565
    online_mode: bool = True
    prevent_proxy_connections: bool = False
    use_native_transport: bool = True
    network_compression_threshold: int = 256
    rate_limit: int = 0

    # Query settings
    enable_query: bool = False
    query_port: int = 25565
    
    # RCON settings
    enable_rcon: bool = False
    rcon_password: Optional[str] = None
    rcon_port: int = 25575

    # Resource pack settings
    require_resource_pack: bool = False
    resource_pack: ResourcePack = ResourcePack().vanilla
    resource_pack_id: Optional[str] = None
    resource_pack_prompt: Optional[str] = None
    resource_pack_sha1: Optional[str] = None

    # Miscellaneous settings
    enable_jmx_monitoring: bool = False
    enable_status: bool = True
    debug: bool = False
    log_ips: bool = True
    initial_disabled_packs: Optional[str] = None
    initial_enabled_packs: str = "vanilla"
    hide_online_players: bool = False
    region_file_compression: str = "deflate"
    text_filtering_config: Optional[str] = None
    bug_report_link: Optional[str] = None
    accepts_transfers: bool= False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServerProperties':
        """Creates an instance of ServerProperties from a dictionary."""
        # Map nested keys to attributes with underscores
        converted_data = {}
        for key, value in data.items():
            # Replace '.' in keys with '_' to match class attribute names
            converted_key = key.replace('.', '_').replace("-","_")
            converted_data[converted_key] = value
        return cls(**converted_data)

    def to_dict(self) -> Dict[str, Any]:
        """Converts the ServerProperties instance to a dictionary."""
        data = asdict(self)
        converted_data = {}
        for key, value in data.items():
            # Replace '_' in attribute names with '.' to match original format
            if key in ["query_port", "rcon_password","rcon_port"]:
                converted_key = key.replace('_', '.')
            else: 
                converted_key = key.replace('_', '-')
            converted_data[converted_key] = value
        return converted_data
    


class ServerProperties:
    def __init__(self, file_path='server.properties'):
        self.file_path = file_path
        self.properties: Optional[Properties] = None
        self.load()

    def load(self):
        """Reads the server.properties file and loads it into a dictionary."""
        propertiesDict= {}
        try:
            with open(self.file_path, 'r') as file:
                for line in file:
                    # Ignore comments and empty lines
                    if line.startswith('#') or line.strip() == '':
                        continue
                    # Try to split each line at the '=' character
                    try:
                        key, value = line.strip().split('=', 1)
                        propertiesDict[key] = value
                    except ValueError:
                        print(f"Warning: Skipping malformed line in {self.file_path}: {line.strip()}")
        except FileNotFoundError:
            print(f"Error: The file {self.file_path} does not exist.")
        except IOError as e:
            print(f"Error: An I/O error occurred while reading {self.file_path}: {e}")
        self.properties  = Properties.from_dict(propertiesDict)
        return self.properties
    def save(self):
        """Writes the dictionary back to the server.properties file."""
        try:
            with open(self.file_path, 'w') as file:
                for key, value in self.properties.to_dict().items():
                    file.write(f"{key}={value}\n")
        except IOError as e:
            print(f"Error: An I/O error occurred while writing to {self.file_path}: {e}")

    def get(self, key, default=None):
        """Gets a value from the properties dictionary."""
        return self.properties.to_dict().get(key, default)

    def set(self, key, value):
        """Sets a value in the properties dictionary."""
        self.properties.to_dict()[key] = value

    def delete(self, key):
        """Deletes a key from the properties dictionary, if it exists."""
        if key in self.properties.to_dict():
            del self.properties.to_dict()[key]