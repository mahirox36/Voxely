from fastapi import APIRouter, HTTPException, Request
from typing import List
from pydantic import BaseModel
from datetime import datetime
from ..auth import get_current_user
from .utils import get_server_instance

router = APIRouter(tags=["backups"])

class BackupInfo(BaseModel):
    name: str
    size: int
    created: str
    path: str

@router.get("/{server_name}/backups", response_model=List[BackupInfo])
async def list_backups(request: Request, server_name: str):
    """List available backups"""
    current_user = await get_current_user(request)
    
    try:
        server = await get_server_instance(server_name)
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
        server = await get_server_instance(server_name)
        backup_path = await server.backup_server()
        
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
        server = await get_server_instance(server_name)
        backup_file = server.backup_path / backup_name
        
        if not backup_file.exists():
            raise HTTPException(status_code=404, detail="Backup not found")
            
        success = await server.restore_backup(str(backup_file))
        if not success:
            raise HTTPException(status_code=500, detail="Failed to restore backup")
            
        return {"message": "Backup restored successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))