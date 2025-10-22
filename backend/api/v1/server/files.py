from fastapi import APIRouter, HTTPException, Request
from typing import List
from pydantic import BaseModel
from datetime import datetime
from ..auth import get_current_user
from .utils import get_server_instance

router = APIRouter(tags=["files"])

class FileListResponse(BaseModel):
    path: str
    name: str
    type: str
    size: int | None
    modified: str | None

@router.get("/{server_name}/files", response_model=List[FileListResponse])
async def list_files(request: Request, server_name: str, path: str = ""):
    """List files in the server directory"""
    current_user = await get_current_user(request)
    
    try:
        server = await get_server_instance(server_name)
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