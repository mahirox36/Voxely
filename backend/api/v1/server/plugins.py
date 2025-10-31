import logging
from pathlib import Path
import traceback
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Optional
from pydantic import BaseModel

from modules.modrinth.utils import Facet, FacetType, SideType
from modules.servers import Addon
from ..auth import UserResponse, get_current_user
from .utils import get_server_instance

from modules.modrinth import Client

modrinth_logger = logging.getLogger("modrinth")
file_handler = logging.FileHandler("logs/modrinth.log")
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
modrinth_logger.addHandler(file_handler)

router = APIRouter(tags=["plugins"])

client = Client()


class SearchRequest(BaseModel):
    query: str = ""
    limit: int = 10
    offset: int = 0
    sort: str = "relevance"
    project_type: str = "mod"
    versions: Optional[List[str]] = None
    categories: Optional[List[str]] = None


class DownloadRequest(BaseModel):
    version: Optional[str] = None
    project_version: Optional[str] = None


@router.post("/plugins/search")
async def search_mods(
    request: SearchRequest,
):
    """
    Search for mods on Modrinth.
    """
    try:
        facets = []
        if request.project_type:
            facets.append(Facet(FacetType.PROJECT_TYPE, ":", request.project_type))
        if request.versions:
            for version in request.versions:
                facets.append(Facet(FacetType.VERSIONS, ":", version))
        if request.categories:
            for category in request.categories:
                facets.append(Facet(FacetType.CATEGORIES, ":", category))
        facets.append(Facet(FacetType.SERVER_SIDE, "!=", SideType.UNSUPPORTED.value))
        results = await client.search_projects(
            query=request.query,
            limit=request.limit,
            offset=request.offset,
            index=request.sort,
            facets=facets,
        )
        return results.to_dict()
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/plugins/get/{project_id}")
async def get_project(
    project_id: str,
):
    """
    Get project details from Modrinth.
    """
    try:
        project = await client.get_project(project_id)
        return project.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/plugins/get_versions/{project_id}")
async def get_project_versions(
    project_id: str,
):
    """
    Get project details from Modrinth.
    """
    try:
        project = await client.get_project(project_id)
        versions = await project.get_versions()
        return [version.to_dict() for version in versions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/plugins/get/{project_id}")
async def get_versions(
    project_id: str,
):
    """
    Get project details from Modrinth.
    """
    try:
        project = await client.get_project(project_id)
        versions = await project.get_versions()
        return [version.to_dict() for version in versions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/plugins/download/{project_id}")
async def download_mod(
    server_name: str,
    project_id: str,
    request: DownloadRequest,
):
    """
    Download a mod from Modrinth and save it to the server's mod folder.
    """
    try:

        server = await get_server_instance(server_name)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        if not server.addon_path:
            raise HTTPException(
                status_code=400, detail="Server type does not support mods/plugins"
            )

        try:
            if not request.project_version:
                project = await client.get_project(project_id)
                # version = project.get_version()
                version = await project.get_latest_version(request.version, server.type)
            else:
                version = await client.get_version(request.project_version)
        except Exception as e:
            raise HTTPException(status_code=404, detail="Mod not found") from e
        path = await version.download_primary(server.addon_path)
        server_addon = Addon(project=project, version=version, path=Path(path))
        await server.add_addon(server_addon)
        return {
            "status": "success",
            "message": f"Mod {project_id} downloaded to {server.addon_path} folder",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/plugins/remove/{project_id}")
async def remove_mod(
    server_name: str,
    project_id: str,
):
    """
    Remove a mod/plugin from the server by project ID.
    """
    try:
        server = await get_server_instance(server_name)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        await server.remove_addon(project_id, True)

        return {
            "status": "success",
            "message": f"Mod/Plugin with project ID {project_id} removed from server {server_name}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/plugins/list")
async def list_plugins(server_name: str):
    """
    List all mods/plugins installed on the server.
    """
    try:
        server = await get_server_instance(server_name)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        return server.export_addons()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# Get available categories
@router.get("/plugins/categories")
async def get_categories():
    """
    Get available categories from Modrinth.
    """
    try:
        tags = await client.get_category_tags()
        return [tag.to_dict() for tag in tags]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# Get Server Type (mod or plugin)
@router.get("/plugins/type")
async def get_server_type(
    server_name: str,
):
    """
    Get the server's addon type (mod or plugin).
    """
    try:
        server = await get_server_instance(server_name)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        return {
            "type": server.addon_type,
            "version": server.version,
            "loader": server.type,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
