from fastapi import APIRouter, HTTPException, Request
from typing import List
from pydantic import BaseModel
from datetime import datetime
from ..auth import get_current_user
from .utils import get_server_instance

router = APIRouter(tags=["logs"])

class LogInfo(BaseModel):
    name: str
    size: int
    modified: str
    path: str

@router.get("/{server_name}/logs", response_model=List[LogInfo])
async def list_logs(request: Request, server_name: str):
    """List server log files"""
    current_user = await get_current_user(request)
    
    try:
        server = await get_server_instance(server_name)
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
        server = await get_server_instance(server_name)
        log_file = server.path / "logs" / log_name
        
        if not log_file.exists():
            raise HTTPException(status_code=404, detail="Log file not found")
            
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-last_lines:]
                return {"content": "".join(lines)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read log file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))