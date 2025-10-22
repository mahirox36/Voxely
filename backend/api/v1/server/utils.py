from typing import Dict, Any, Optional
import time
from modules.servers import Server

_server_instances: Dict[str, Server] = {}
_server_details_cache: Dict[str, Any] = {}
_cache_duration = 5

async def get_server_instance(server_name: str) -> Server:
    """Get a cached server instance or create a new one if it doesn't exist"""
    if server_name not in _server_instances:
        _server_instances[server_name] = await Server.init(server_name)
    return _server_instances[server_name]

async def process_server(server_name: str) -> Optional[dict]:
    """Process a single server and return its details"""
    try:
        current_time = time.time()
        if (server_name in _server_details_cache and 
            current_time - _server_details_cache[server_name]["timestamp"] < _cache_duration):
            return _server_details_cache[server_name]["data"]
        
        server = await get_server_instance(server_name)
        metrics = await server.get_metrics(True)
        
        response = {
            "name": server.name,
            "status": server.status,
            "type": server.type,
            "version": server.version,
            "metrics": metrics if isinstance(metrics, dict) else metrics.__dict__,
            "port": server.port,
            "maxPlayers": server.players_limit,
            "players": await server.players,
            "ip": server.ip
        }
        
        _server_details_cache[server_name] = {
            "data": response,
            "timestamp": current_time
        }
        
        return response
    except Exception as e:
        print(f"Error processing server {server_name}: {e}")
        return None