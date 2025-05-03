from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
import asyncio
import time
from ..auth import get_current_user
from modules.servers import Server, ServerType, get_servers
from modules.jar import MinecraftServerDownloader
from .utils import get_server_instance, process_server

router = APIRouter(tags=["management"])

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
    players: Optional[List[str]] = None
    ip: Optional[Dict[str, str]] = None

@router.get("/get", response_model=List[ServerResponse])
async def list_servers(request: Request):
    """Get all servers with their current status"""
    current_user = await get_current_user(request)
    
    try:
        server_names = get_servers()
        if not server_names:
            return []
        
        tasks = [process_server(name) for name in server_names]
        servers_info = await asyncio.gather(*tasks)
        return [server for server in servers_info if server is not None]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve servers: {str(e)}")

@router.get("/versions")
async def get_available_versions(request: Request):
    """Get available Minecraft versions for different server types"""
    current_user = await get_current_user(request)
    
    try:
        downloader = MinecraftServerDownloader()
        return {
            "vanilla": downloader.get_vanilla_versions(),
            "paper": downloader.get_paper_versions(),
            "fabric": downloader.get_fabric_versions(),
            "purpur": downloader.get_purpur_versions()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch versions: {str(e)}")

@router.post("/create", status_code=201)
async def create_server(request: Request, server_request: CreateServerRequest):
    """Create a new Minecraft server"""
    current_user = await get_current_user(request)
    
    try:
        try:
            server_type = ServerType(server_request.type)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid server type. Must be one of: {', '.join([t.value for t in ServerType])}"
            )
        
        server = Server(
            name=server_request.name,
            type=server_type,
            version=server_request.version,
            min_ram=server_request.minRam,
            max_ram=server_request.maxRam,
            port=server_request.port,
            players_limit=server_request.maxPlayers
        )
        
        return {"message": "Server created successfully", "needsEulaAcceptance": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{server_name}", response_model=ServerResponse)
async def get_server(server_name: str, request: Request):
    """Get details for a specific server"""
    current_user = await get_current_user(request)
    
    try:
        server_names = get_servers()
        if server_name not in server_names:
            raise HTTPException(status_code=404, detail=f"Server '{server_name}' not found")
            
        server_info = await process_server(server_name)
        if not server_info:
            raise HTTPException(status_code=500, detail="Failed to get server details")
            
        return server_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get server details: {str(e)}")

@router.post("/{server_name}/start")
async def start_server(request: Request, server_name: str):
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
    current_user = await get_current_user(request)
    try:
        server = get_server_instance(server_name)
        server.restart()
        return {"message": "Server restarted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{server_name}/command")
async def send_command(request: Request, server_name: str, command: str):
    current_user = await get_current_user(request)
    try:
        server = get_server_instance(server_name)
        if server.status != "online":
            raise HTTPException(status_code=400, detail="Server is not running")
        server.send_command(command)
        return {"message": "Command sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))