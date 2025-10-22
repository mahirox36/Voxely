from dataclasses import dataclass, field
from enum import StrEnum, auto
from pathlib import Path
from typing import Any, Dict, Optional, Union, List, Callable
from rich import print
import json
from datetime import datetime

class PropertyValidationError(Exception):
    pass

class ServerType(StrEnum):
    VANILLA = auto()
    PAPER = auto()
    FABRIC = auto()
    FORGE = auto()
    PURPUR = auto()

class Gamemode(StrEnum):
    SURVIVAL = "survival"
    CREATIVE = "creative"
    ADVENTURE = "adventure"
    SPECTATOR = "spectator"

class Difficulty(StrEnum):
    PEACEFUL = "peaceful"
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"

@dataclass
class PropertyDefinition:
    type: type
    default: Any
    validator: Optional[Callable] = None
    versions: List[str] = field(default_factory=lambda: ["*"])
    server_types: List[ServerType] = field(default_factory=lambda: [t for t in ServerType])
    description: str = ""

@dataclass
class Properties:
    _definitions: Dict[str, PropertyDefinition] = field(default_factory=dict)
    _values: Dict[str, Any] = field(default_factory=dict)
    _server_type: ServerType = ServerType.VANILLA
    _version: str = "1.21.1"

    def __post_init__(self):
        self._setup_property_definitions()
        
    def _setup_property_definitions(self):
        """Define all server properties with their types, defaults, and validators"""
        self._definitions = {
            "motd": PropertyDefinition(
                str, "A Minecraft Server",
                lambda x: len(x) <= 59,
                description="Message of the day"
            ),
            "server-port": PropertyDefinition(
                int, 25565,
                lambda x: 1 <= x <= 65535,
                description="Port for the server to listen on"
            ),
            "max-players": PropertyDefinition(
                int, 20,
                lambda x: 0 <= x <= 2147483647,
                description="Maximum number of players allowed"
            ),
            "level-seed": PropertyDefinition(
                str, "",
                lambda x: True,
                description="Seed for world generation"
            ),
            "gamemode": PropertyDefinition(
                Gamemode, Gamemode.SURVIVAL,
                lambda x: x in Gamemode,
                description="Default game mode"
            ),
            "difficulty": PropertyDefinition(
                Difficulty, Difficulty.EASY,
                lambda x: x in Difficulty,
                description="Game difficulty"
            ),
            "level-type": PropertyDefinition(
                str, "minecarft:normal",
                description="World generation type"
            ),
            # Add more properties with specific version/server type support
            "simulation-distance": PropertyDefinition(
                int, 10,
                lambda x: 0 <= x <= 32,
                versions=["1.18.0+"],
                description="Simulation distance in chunks"
            ),
            "resource-pack": PropertyDefinition(
                str, "",
                lambda x: isinstance(x, str),
                description="Resource pack URL"
            ),
            # Paper-specific properties
            "paper-world-settings": PropertyDefinition(
                dict, {},
                server_types=[ServerType.PAPER],
                description="Paper-specific world settings"
            ),
        }

    def validate_property(self, key: str, value: Any) -> bool:
        if key not in self._definitions:
            return True  # Allow unknown properties
            
        definition = self._definitions[key]
        
        # Check version compatibility
        if "*" not in definition.versions:
            version_match = False
            for ver in definition.versions:
                if ver.endswith("+"):
                    min_ver = ver[:-1]
                    if self._version >= min_ver:
                        version_match = True
                        break
                elif ver == self._version:
                    version_match = True
                    break
            if not version_match:
                raise PropertyValidationError(f"Property {key} is not supported in version {self._version}")

        # Check server type compatibility
        if self._server_type not in definition.server_types:
            raise PropertyValidationError(f"Property {key} is not supported for server type {self._server_type}")

        # Type conversion
        try:
            if isinstance(value, str):
                if definition.type == bool:
                    value = value.lower() == "true"
                elif definition.type == int:
                    value = int(value)
                elif definition.type == float:
                    value = float(value)
                elif issubclass(definition.type, StrEnum):
                    value = definition.type(value)
        except (ValueError, TypeError) as e:
            raise PropertyValidationError(f"Invalid type for property {key}: {str(e)}")

        # Custom validation
        if definition.validator and not definition.validator(value):
            raise PropertyValidationError(f"Validation failed for property {key}")

        return True

    def set_server_info(self, server_type: ServerType, version: str):
        self._server_type = server_type
        self._version = version

    def __getattr__(self, name: str) -> Any:
        normalized_name = name.replace("_", "-")
        if normalized_name in self._values:
            return self._values[normalized_name]
        elif normalized_name in self._definitions:
            return self._definitions[normalized_name].default
        raise AttributeError(f"Property {name} not found")

    def __setattr__(self, name: str, value: Any):
        if name.startswith("_"):
            super().__setattr__(name, value)
            return

        normalized_name = name.replace("_", "-")
        if self.validate_property(normalized_name, value):
            self._values[normalized_name] = value

class ServerProperties:
    def __init__(self, file_path: Path, server_type: ServerType = ServerType.VANILLA, version: str = "1.21.1"):
        self.path = file_path
        self.properties = Properties()
        self.properties.set_server_info(server_type, version)
        
        # Ensure parent directory exists before creating backup directory
        if not self.path.parent.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            
        self.backup_path = file_path.parent / "properties_backups"
        self.backup_path.mkdir(parents=True, exist_ok=True)
        self.load()

    def create_backup(self):
        """Create a backup of the current properties file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_path / f"server.properties.{timestamp}"
        
        # Make sure backup directory exists
        if not self.backup_path.exists():
            self.backup_path.mkdir(parents=True, exist_ok=True)
            
        if self.path.exists():
            import shutil
            shutil.copy2(self.path, backup_file)
            return backup_file
        return None

    def restore_backup(self, backup_file: Union[str, Path]):
        """Restore properties from a backup file"""
        backup_path = Path(backup_file)
        if backup_path.exists():
            # Ensure target directory exists
            if not self.path.parent.exists():
                self.path.parent.mkdir(parents=True, exist_ok=True)
                
            import shutil
            shutil.copy2(backup_path, self.path)
            self.load()
            return True
        return False

    def load(self):
        """Load properties with enhanced error handling and validation"""
        if not self.path.exists():
            return

        try:
            with open(self.path, "r", encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            try:
                                setattr(self.properties, key, value)
                            except PropertyValidationError as e:
                                print(f"Warning: {str(e)}")
                        except ValueError:
                            print(f"Warning: Skipping malformed line: {line}")
        except Exception as e:
            print(f"Error loading properties: {str(e)}")
            self.create_backup()
            
    def save(self):
        """Save properties with backup creation"""
        self.create_backup()
        try:
            with open(self.path, "w", encoding='utf-8') as file:
                file.write(f"# Generated by Voxely on {datetime.now().isoformat()}\n")
                file.write(f"# Server Type: {self.properties._server_type}\n")
                file.write(f"# Minecraft Version: {self.properties._version}\n\n")
                
                # Sort properties by name for consistency
                for key in sorted(self.properties._values.keys()):
                    value = self.properties._values[key]
                    if key in self.properties._definitions:
                        file.write(f"# {self.properties._definitions[key].description}\n")
                    file.write(f"{key}={value}\n")
        except Exception as e:
            print(f"Error saving properties: {str(e)}")
            return False
        return True

    def get(self, key: str, default: Any = None) -> Any:
        """Get a property value with default fallback"""
        try:
            return getattr(self.properties, key.replace("-", "_"))
        except AttributeError:
            return default

    def set(self, key: str, value: Any):
        """Set a property value with validation"""
        try:
            setattr(self.properties, key.replace("-", "_"), value)
            return True
        except PropertyValidationError as e:
            print(f"Error setting property: {str(e)}")
            return False

    def export_json(self, file_path: Optional[Path] = None) -> Union[str, bool]:
        """Export properties to JSON format"""
        data = {
            "server_type": self.properties._server_type,
            "version": self.properties._version,
            "properties": self.properties._values
        }
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
                return True
            except Exception as e:
                print(f"Error exporting to JSON: {str(e)}")
                return False
        return json.dumps(data, indent=2)

    def import_json(self, file_path: Path) -> bool:
        """Import properties from JSON format"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            self.properties.set_server_info(
                ServerType(data["server_type"]),
                data["version"]
            )
            for key, value in data["properties"].items():
                self.set(key, value)
            return True
        except Exception as e:
            print(f"Error importing from JSON: {str(e)}")
            return False
