from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status, Request
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
import asyncio
import time
import json
from functools import lru_cache
from datetime import datetime

from modules.servers import Server, ServerType, get_servers, ServerStatus, invalidate_server_cache
from modules.jar import MinecraftServerDownloader
from .auth import get_current_user, User

router = APIRouter(prefix="/servers", tags=["servers"])

# Models
class CreateServerRequest(BaseModel):
    name: str
    type: str
    version: str
    minRam: int
    maxRam: int
    port: int
    maxPlayers: int

class ServerResponse(BaseModel):
    name: str
    status: str
    type: str
    version: str
    metrics: Dict[str, str]
    port: int
    maxPlayers: int
    players: Optional[List[str]] = None  # Add players field
    ip : Optional[Dict[str, str]] = None  # Add IP field

class FileListResponse(BaseModel):
    path: str
    name: str
    type: str
    size: Optional[int]
    modified: Optional[str]

class PluginInfo(BaseModel):
    name: str
    version: str
    enabled: bool
    description: Optional[str]

class BackupInfo(BaseModel):
    name: str
    size: int
    created: str
    path: str

class LogInfo(BaseModel):
    name: str
    size: int
    modified: str
    path: str

# Cache for server details to improve performance
_server_details_cache: Dict[str, Any] = {}
_cache_timestamp = 0
_cache_duration = 5  # Cache duration in seconds

# WebSocket manager for real-time updates
websocket_connections: Dict[str, List[WebSocket]] = {}

# Server instances cache to prevent creating multiple instances of the same server
_server_instances: Dict[str, Server] = {}

# Helper function to get server instance (creates it if it doesn't exist)
def get_server_instance(server_name: str) -> Server:
    """Get a cached server instance or create a new one if it doesn't exist"""
    if server_name not in _server_instances:
        _server_instances[server_name] = Server(server_name)
    return _server_instances[server_name]

# Helper function to process a single server concurrently
async def process_server(server_name: str) -> Optional[ServerResponse]:
    try:
        # Check if we have a recent cached response for this server
        current_time = time.time()
        if (server_name in _server_details_cache and 
            current_time - _server_details_cache[server_name]["timestamp"] < _cache_duration):
            return _server_details_cache[server_name]["data"]
        
        # Create a server object and get its metrics
        server = get_server_instance(server_name)
        metrics = await server.get_metrics(True)
        
        # Create response object
        response = ServerResponse(
            name=server.name,
            status=server.status,
            type=server.type,
            version=server.version,
            metrics=metrics if isinstance(metrics, dict) else metrics.__dict__,
            port=server.port,
            maxPlayers=server.players_limit
        )
        
        # Cache the response
        _server_details_cache[server_name] = {
            "data": response,
            "timestamp": current_time
        }
        
        return response
    except Exception as e:
        print(f"Error processing server {server_name}: {e}")
        return None

# Route handlers for both with and without trailing slash
@router.get("", response_model=List[ServerResponse])
@router.get("/", response_model=List[ServerResponse])
async def list_servers(request: Request):
    """Get all servers with their current status"""
    # Authenticate the user
    current_user = await get_current_user(request)
    
    try:
        # Get the list of server names (this uses the cache we implemented)
        server_names = get_servers()
        
        if not server_names:
            return []
        
        # Process all servers concurrently for better performance
        tasks = [process_server(name) for name in server_names]
        servers_info = await asyncio.gather(*tasks)
        
        # Filter out any None values from errors
        return [server for server in servers_info if server is not None]
    except Exception as e:
        print(f"Error in list_servers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve servers: {str(e)}")


@router.get("/versions", response_model=Dict[str, List[str]])
async def get_available_versions(request: Request):
    """Get available Minecraft versions for different server types"""
    # Authenticate the user
    try:
        current_user = await get_current_user(request)
    except Exception as e:
        print(f"Authentication error in versions endpoint: {e}")
        raise
    
    try:
        print("Fetching versions...")
        downloader = MinecraftServerDownloader()
        vanilla = downloader.get_vanilla_versions()
        paper = downloader.get_paper_versions()
        fabric = downloader.get_fabric_versions()
        purpur = downloader.get_purpur_versions()
        
        print(f"Retrieved versions - Vanilla: {len(vanilla)}, Paper: {len(paper)}, Fabric: {len(fabric)}, Purpur: {len(purpur)}")
        
        return {
            "vanilla": vanilla,
            "paper": paper,
            "fabric": fabric,
            "purpur": purpur
        }
    except Exception as e:
        print(f"Error fetching versions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch versions: {str(e)}")

# Route handlers for both with and without trailing slash
@router.post("", status_code=201)
@router.post("/", status_code=201)
async def create_server(request: Request, server_request: CreateServerRequest):
    """Create a new Minecraft server"""
    # Authenticate the user
    current_user = await get_current_user(request)
    
    try:
        # Convert request type to ServerType enum
        server_type = None
        try:
            server_type = ServerType(server_request.type)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid server type. Must be one of: {', '.join([t.value for t in ServerType])}"
            )
        
        # Create and initialize server
        server = Server(
            name=server_request.name,
            type=server_type,
            version=server_request.version,
            min_ram=server_request.minRam,
            max_ram=server_request.maxRam,
            port=server_request.port,
            players_limit=server_request.maxPlayers
        )
        
        _server_instances[server_request.name] = server  # Cache the server instance
        
        # Don't automatically accept EULA
        return {"message": "Server created successfully", "needsEulaAcceptance": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Server-specific routes
@router.get("/{server_name}", response_model=ServerResponse)
async def get_server(server_name: str, request: Request):
    """Get details for a specific server"""
    current_user = await get_current_user(request)
    
    try:
        # Check if server exists first to avoid unnecessary processing
        server_names = get_servers()
        if server_name not in server_names:
            raise HTTPException(status_code=404, detail=f"Server '{server_name}' not found")
        
        # Check if we have a recent cached response for this server
        current_time = time.time()
        if (server_name in _server_details_cache and 
            current_time - _server_details_cache[server_name]["timestamp"] < _cache_duration):
            return _server_details_cache[server_name]["data"]
        
        # Create server object and get metrics
        server = get_server_instance(server_name)
        metrics = await server.get_metrics(True)
        players = server.players
        
        # Prepare the response
        response = ServerResponse(
            name=server.name,
            status=server.status,
            type=server.type,
            version=server.version,
            metrics=metrics if isinstance(metrics, dict) else metrics.__dict__,
            port=server.port,
            maxPlayers=server.players_limit,
            players=players,
            ip=server.ip
        )
        
        # Cache the response
        _server_details_cache[server_name] = {
            "data": response,
            "timestamp": current_time
        }
        
        return response
    except Exception as e:
        print(f"Error getting server {server_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get server details: {str(e)}")

@router.post("/{server_name}/start")
async def start_server(request: Request, server_name: str):
    """Start a Minecraft server"""
    # Authenticate the user
    current_user = await get_current_user(request)
    
    try:
        server = get_server_instance(server_name)
        if server.status == "online":
            raise HTTPException(status_code=400, detail="Server is already running")
        
        server.start()
        return {"message": "Server started successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{server_name}/stop")
async def stop_server(request: Request, server_name: str):
    """Stop a Minecraft server"""
    # Authenticate the user
    current_user = await get_current_user(request)
    
    try:
        server = get_server_instance(server_name)
        if server.status == "offline":
            raise HTTPException(status_code=400, detail="Server is not running")
        
        server.stop()
        return {"message": "Server stopped successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{server_name}/restart")
async def restart_server(request: Request, server_name: str):
    """Restart a Minecraft server"""
    # Authenticate the user
    current_user = await get_current_user(request)
    
    try:
        server = get_server_instance(server_name)
        server.restart()
        return {"message": "Server restarted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{server_name}/command")
async def send_command(
    request: Request,
    server_name: str,
    command: str
):
    """Send a command to a running Minecraft server"""
    # Authenticate the user
    current_user = await get_current_user(request)
    
    try:
        server = get_server_instance(server_name)
        if server.status != "online":
            raise HTTPException(status_code=400, detail="Server is not running")
        
        server.send_command(command)
        return {"message": "Command sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{server_name}/eula/accept")
async def accept_eula(request: Request, server_name: str):
    """Accept the Minecraft EULA for a server"""
    # Authenticate the user
    current_user = await get_current_user(request)
    
    try:
        server = get_server_instance(server_name)
        server.accept_eula()
        return {"message": "EULA accepted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{server_name}/eula/status")
async def check_eula_status(request: Request, server_name: str):
    """Check if EULA has been accepted for a server"""
    # Authenticate the user
    current_user = await get_current_user(request)
    
    try:
        server = get_server_instance(server_name)
        eula_path = server.path / "eula.txt"
        
        if not eula_path.exists():
            return {"accepted": False}
        
        with open(eula_path, "r") as f:
            content = f.read()
            return {"accepted": "eula=true" in content.lower()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/{server_name}/console")
async def websocket_endpoint(websocket: WebSocket, server_name: str):
    """WebSocket endpoint for real-time console output"""
    print(f"WebSocket connection request for {server_name}")
    await websocket.accept()
    print(f"WebSocket connection accepted for {server_name}")
    
    if server_name not in websocket_connections:
        websocket_connections[server_name] = []
    websocket_connections[server_name].append(websocket)
    
    # Get the server instance (reuse existing or create new)
    server = get_server_instance(server_name)
    
    # Setup callback for formatting and sending console output to this WebSocket
    async def send_to_websocket(message: str):
        try:
            # Format the message with color codes based on content
            formatted_message = format_console_message(message)
            await websocket.send_text(formatted_message)
        except Exception as e:
            print(f"Error sending message to WebSocket: {e}")
    
    # Set the output callback for this server
    server.set_output_callback(send_to_websocket)
    
    try:
        # Send initial console buffer
        print(f"Sending initial console buffer ({len(server.logs) if hasattr(server, 'logs') and server.logs else 0}) lines for {server_name}")
        if hasattr(server, 'logs') and server.logs:
            for line in server.logs[-100:]:  # Last 100 lines
                formatted_line = format_console_message(line)
                await websocket.send_text(formatted_line)
                await asyncio.sleep(0.01)  # Small delay to avoid flooding
        else:
            await websocket.send_text(format_console_message("Console ready. Server not started yet.", "system"))
        
        # Keep connection open and handle disconnection
        while True:
            try:
                # Wait for any message (can be used for heartbeat)
                data = await websocket.receive_text()
                if data.startswith("cmd:"):
                    # Handle commands sent from the frontend
                    command = data[4:]
                    print(f"Received command via WebSocket: {command}")
                    server.send_command(command)
            except WebSocketDisconnect:
                print(f"WebSocket disconnected for {server_name}")
                break
    except Exception as e:
        print(f"WebSocket error for {server_name}: {e}")
        await websocket.close(code=1001, reason=str(e))
    finally:
        # Clean up the connection
        if server_name in websocket_connections:
            if websocket in websocket_connections[server_name]:
                websocket_connections[server_name].remove(websocket)
                print(f"Removed WebSocket connection for {server_name}")
        print(f"WebSocket connection closed for {server_name}")

def format_console_message(message: str, message_type: Optional[str] = None) -> str:
    """Format console messages with JSON formatting for the frontend to render with colors"""
    # Detect message type if not provided
    if message_type is None:
        if "[INFO]" in message:
            message_type = "info"
        elif "[WARN]" in message or "[WARNING]" in message:
            message_type = "warning"
        elif "[ERROR]" in message or "[SEVERE]" in message:
            message_type = "error"
        elif "[DEBUG]" in message:
            message_type = "debug"
        elif "Done " in message and "seconds" in message:
            message_type = "success"
        elif "EULA" in message:
            message_type = "eula"
        else:
            message_type = "default"
    
    # Return JSON formatted message that the frontend can parse and style
    return json.dumps({
        "text": message,
        "type": message_type,
        "timestamp": time.strftime("%H:%M:%S")
    })

# Helper function for broadcasting console output
async def broadcast_console(server_name: str, message: str):
    """Broadcast console message to all connected WebSocket clients"""
    if server_name in websocket_connections:
        for connection in websocket_connections[server_name]:
            try:
                await connection.send_text(message)
            except:
                continue

@router.get("/{server_name}/files", response_model=List[FileListResponse])
async def list_files(request: Request, server_name: str, path: str = ""):
    """List files in the server directory"""
    current_user = await get_current_user(request)
    
    try:
        server = get_server_instance(server_name)
        base_path = server.path / path if path else server.path
        
        if not base_path.exists():
            raise HTTPException(status_code=404, detail="Path not found")
            
        files = []
        for entry in base_path.iterdir():
            try:
                stat = entry.stat()
                files.append(FileListResponse(
                    path=str(entry.relative_to(server.path)),
                    name=entry.name,
                    type="directory" if entry.is_dir() else "file",
                    size=stat.st_size if not entry.is_dir() else None,
                    modified=datetime.fromtimestamp(stat.st_mtime).isoformat()
               ))
            except Exception as e:
                print(f"Error processing {entry}: {e}")
                continue
                
        return sorted(files, key=lambda x: (x.type == "file", x.name.lower()))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{server_name}/plugins", response_model=List[PluginInfo])
async def list_plugins(request: Request, server_name: str):
    """List installed plugins"""
    current_user = await get_current_user(request)
    
    try:
        server = get_server_instance(server_name)
        plugins_dir = server.path / "plugins"
        
        if not plugins_dir.exists():
            return []
            
        plugins = []
        for jar in plugins_dir.glob("*.jar"):
            try:
                # TODO: Extract plugin info from jar manifest
                plugins.append(PluginInfo(
                    name=jar.stem,
                    version="Unknown",
                    enabled=True,
                    description=None
               ))
            except Exception as e:
                print(f"Error processing plugin {jar}: {e}")
                continue
                
        return plugins
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{server_name}/backups", response_model=List[BackupInfo])
async def list_backups(request: Request, server_name: str):
    """List available backups"""
    current_user = await get_current_user(request)
    
    try:
        server = get_server_instance(server_name)
        if not server.backup_path.exists():
            return []
            
        backups = []
        for backup in server.backup_path.glob(f"{server_name}_*.zip"):
            try:
                stat = backup.stat()
                backups.append(BackupInfo(
                    name=backup.name,
                    size=stat.st_size,
                    created=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    path=str(backup)
               ))
            except Exception as e:
                print(f"Error processing backup {backup}: {e}")
                continue
                
        return sorted(backups, key=lambda x: x.created, reverse=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{server_name}/backups")
async def create_backup(request: Request, server_name: str):
    """Create a new backup"""
    current_user = await get_current_user(request)
    
    try:
        server = get_server_instance(server_name)
        backup_path = server.backup_server()
        
        if not backup_path:
            raise HTTPException(status_code=500, detail="Failed to create backup")
            
        return {"message": "Backup created successfully", "path": backup_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{server_name}/backups/{backup_name}/restore")
async def restore_backup(request: Request, server_name: str, backup_name: str):
    """Restore from a backup"""
    current_user = await get_current_user(request)
    
    try:
        server = get_server_instance(server_name)
        backup_file = server.backup_path / backup_name
        
        if not backup_file.exists():
            raise HTTPException(status_code=404, detail="Backup not found")
            
        success = server.restore_backup(str(backup_file))
        if not success:
            raise HTTPException(status_code=500, detail="Failed to restore backup")
            
        return {"message": "Backup restored successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{server_name}/logs", response_model=List[LogInfo])
async def list_logs(request: Request, server_name: str):
    """List server log files"""
    current_user = await get_current_user(request)
    
    try:
        server = get_server_instance(server_name)
        logs_dir = server.path / "logs"
        
        if not logs_dir.exists():
            return []
            
        logs = []
        for log in logs_dir.glob("*.log*"):
            try:
                stat = log.stat()
                logs.append(LogInfo(
                    name=log.name,
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    path=str(log.relative_to(server.path))
               ))
            except Exception as e:
                print(f"Error processing log {log}: {e}")
                continue
                
        return sorted(logs, key=lambda x: x.modified, reverse=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{server_name}/logs/{log_name}")
async def get_log_content(request: Request, server_name: str, log_name: str, last_lines: int = 1000):
    """Get contents of a specific log file"""
    current_user = await get_current_user(request)
    
    try:
        server = get_server_instance(server_name)
        log_file = server.path / "logs" / log_name
        
        if not log_file.exists():
            raise HTTPException(status_code=404, detail="Log file not found")
            
        # Read the last N lines of the log file
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-last_lines:]
                return {"content": "".join(lines)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read log file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))