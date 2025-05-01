from backend.modules.modrinth.utils import MISSING, ProjectType
from modules.modrinth import Client

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

router = APIRouter(prefix="/modrinth", tags=["modrinth"])
client = Client()

class Search(BaseModel):
    query: str
    limit: int = 10
    offset: int = 0
    sort: str = "relevance"
    project_type: str = "mod"
    versions: str = "any"
    categories: Optional[List[str]] = None

@router.get("/search", response_model=Search)
async def search_mods(query: str, limit: int = 10, offset: int = 0, sort: str = "relevance", project_type: str = "mod", versions: str = "any", categories: Optional[List[str]] = None):
    """
    Search for mods on Modrinth.
    """
    try:
        results = await client.search_projects(query=query, limit=limit, offset=offset, sort=sort, project_type=ProjectType(project_type), versions=versions, categories=categories or MISSING)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get("/project/{project_id}")
async def get_project(project_id: str):
    """
    Get project details from Modrinth.
    """
    try:
        project = await client.get_project(project_id)
        return project
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e