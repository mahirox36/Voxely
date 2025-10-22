import logging
from .server.utils import get_server_instance
from modules.modrinth import MISSING, ProjectType
from modules.modrinth import Client

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel

from .auth import get_current_user, User

router = APIRouter(prefix="/modrinth", tags=["modrinth"])
client = Client()

modrinth_logger = logging.getLogger("modrinth")
file_handler = logging.FileHandler("logs/modrinth.log")
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
modrinth_logger.addHandler(file_handler)


class Search(BaseModel):
    query: str = ""
    limit: int = 10
    offset: int = 0
    sort: str = "relevance"
    project_type: str = "mod"
    versions: Optional[str] = None
    categories: Optional[str] = None  # Comma-separated list of categories


@router.get("/search")
async def search_mods(
    query: str = "",
    limit: int = 10,
    offset: int = 0,
    sort: str = "relevance",
    project_type: str = "mod",
    versions: Optional[str] = None,
    categories: Optional[str] = None,
):
    """
    Search for mods on Modrinth.
    """
    try:
        category_list = categories.split(",") if categories else MISSING
        results = await client.search_projects(
            query=query,
            limit=limit,
            offset=offset,
            sort=sort,
            project_type=ProjectType(project_type),
            versions=versions or MISSING,
            categories=category_list,
        )
        return results.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/project/{project_id}")
async def get_project(project_id: str):
    """
    Get project details from Modrinth.
    """
    try:
        project = await client.get_project(project_id)
        return project.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# download modrinth mod, with server id and it saves in that server's mod folder
# the folder it's mods if the server is mod loader or plugins if the server is plugin loader
@router.post("/download/{server_id}")
async def download_mod(
    server_id: str, mod_id: str, user: User = Depends(get_current_user)
):
    """
    Download a mod from Modrinth and save it to the server's mod folder.
    """
    try:

        server = await get_server_instance(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        if not server.addon_path:
            raise HTTPException(
                status_code=400, detail="Server type does not support mods/plugins"
            )

        try:
            project = await client.get_project(mod_id)
        except Exception as e:
            raise HTTPException(status_code=404, detail="Mod not found") from e
        await (await project.get_latest_version()).download_primary(server.addon_path)
        return {
            "status": "success",
            "message": f"Mod {mod_id} downloaded to {server.addon_path} folder",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
