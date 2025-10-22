from fastapi import APIRouter, HTTPException, Request
from typing import List, Optional
from pydantic import BaseModel
from ..auth import get_current_user
from .utils import get_server_instance

router = APIRouter(tags=["plugins"])

class PluginInfo(BaseModel):
    name: str
    version: str
    enabled: bool
    description: Optional[str]

@router.get("/{server_name}/plugins", response_model=List[PluginInfo])
async def list_plugins(request: Request, server_name: str):
    """List installed plugins"""
    current_user = await get_current_user(request)
    
    try:
        server = await get_server_instance(server_name)
        plugins_dir = server.path / "plugins"
        
        if not plugins_dir.exists():
            return []
            
        plugins = []
        for jar in plugins_dir.glob("*.jar"):
            try:
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