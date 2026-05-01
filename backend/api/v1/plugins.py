import logging
from pathlib import Path
from typing import List, Optional

from modules.models import AddonModel
from modules.modrinth import Client
from modules.modrinth.utils import Facet, FacetType, SideType
from modules.router import WebSocketManager, router
from modules.ServerService import ServerService, get_addon_type_for_server
from pydantic import BaseModel, Field, field_validator

modrinth_logger = logging.getLogger("modrinth")

# Initialize Modrinth Client
client: Optional[Client] = None
serverService = ServerService()
# --- Schemas ---


class SearchRequest(BaseModel):
    query: str = Field(default="", max_length=100)
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    sort: str = Field(
        default="relevance", pattern="^(relevance|downloads|follows|newest|updated)$"
    )
    project_type: str = Field(default="mod", pattern="^(mod|plugin)$")
    versions: Optional[List[str]] = Field(default=None, max_length=50)
    categories: Optional[List[str]] = Field(default=None, max_length=50)

    @field_validator("versions", "categories")
    def validate_lists(cls, v):
        if v:
            for item in v:
                if not isinstance(item, str) or len(item) > 50:
                    raise ValueError("Items must be strings with max length 50")
        return v


class DownloadRequest(BaseModel):
    version: Optional[str] = Field(default=None, max_length=50)
    project_version: Optional[str] = Field(default=None, max_length=50)


# --- WebSocket Router ---
# Note: Using the EventRouter instance provided in your snippet


async def send_error(ws: WebSocketManager, event: str, message: str):
    await ws.emit(f"{event}.error", {"message": message})


@router.on_connect()
async def plugins_init(ws: WebSocketManager):
    global client
    if client is None:
        client = Client()
        modrinth_logger.info("Initialized Modrinth client")


@router.on("plugins.search")
async def search_mods(ws: WebSocketManager, request: SearchRequest):
    if not client:
        return await send_error(ws, "plugins.search", "Modrinth client not initialized")
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
        await ws.emit("plugins.search.success", results.to_dict())
    except Exception as e:
        modrinth_logger.error(f"Search error: {e}", exc_info=True)
        await send_error(ws, "plugins.search", "Failed to search Modrinth")


@router.on("plugins.get")
async def get_project(ws: WebSocketManager, project_id: str):
    if not client:
        return await send_error(ws, "plugins.search", "Modrinth client not initialized")
    try:
        project = await client.get_project(project_id)
        await ws.emit("plugins.get.success", project.to_dict())
    except Exception as e:
        await send_error(ws, "plugins.get", str(e))


@router.on("plugins.get_versions")
async def get_project_versions(ws: WebSocketManager, project_id: str):
    if not client:
        return await send_error(ws, "plugins.search", "Modrinth client not initialized")
    try:
        project = await client.get_project(project_id)
        versions = await project.get_versions()
        await ws.emit("plugins.get_versions.success", [v.to_dict() for v in versions])
    except Exception as e:
        await send_error(ws, "plugins.get_versions", str(e))


@router.on("plugins.download")
async def download_mod(
    ws: WebSocketManager, server_id: str, project_id: str, request: DownloadRequest
):
    if not client:
        return await send_error(ws, "plugins.search", "Modrinth client not initialized")
    try:
        server = await serverService.get_server_instance(server_id)
        if not server:
            return await send_error(ws, "plugins.download", "Server not found")

        if not server.addon_path:
            return await send_error(
                ws, "plugins.download", "Server type does not support addons"
            )

        # Notify frontend download started
        await ws.emit("plugins.download.started", {"project_id": project_id})

        if not request.project_version:
            project = await client.get_project(project_id)
            version = await project.get_latest_version(
                request.version, server.config.type
            )
        else:
            version = await client.get_version(request.project_version)
            project = await client.get_project(version.project_id)

        path = await version.download_primary(server.addon_path)
        server_addon = AddonModel(
            project=project,
            version=version,
            path=Path(path),
            addon_type=get_addon_type_for_server(server.config.type),  # type: ignore
        )
        await server.add_addon(server_addon)

        await ws.emit(
            "plugins.download.success",
            {
                "project_id": project_id,
                "version_id": version.id,
                "message": f"Downloaded to {server.addon_path}",
            },
        )
    except Exception as e:
        modrinth_logger.error(f"Download error: {e}")
        await send_error(ws, "plugins.download", "Failed to download plugin")


@router.on("plugins.remove")
async def remove_mod(ws: WebSocketManager, server_id: str, project_id: str):
    if not client:
        return await send_error(ws, "plugins.search", "Modrinth client not initialized")
    try:
        server = await serverService.get_server_instance(server_id)
        if not server:
            return await send_error(ws, "plugins.remove", "Server not found")

        await server.remove_addon(project_id)
        await ws.emit("plugins.remove.success", {"project_id": project_id})
    except Exception as e:
        await send_error(ws, "plugins.remove", str(e))


@router.on("plugins.list")
async def list_plugins(ws: WebSocketManager, server_id: str):
    try:
        server = await serverService.get_server_instance(server_id)
        if not server:
            return await send_error(ws, "plugins.list", "Server not found")

        await ws.emit("plugins.list.success", server.addons)
    except Exception as e:
        await send_error(ws, "plugins.list", str(e))


@router.on("plugins.list.untracked")
async def list_untracked_plugins(ws: WebSocketManager, server_id: str):
    try:
        server = await serverService.get_server_instance(server_id)
        if not server:
            return await send_error(ws, "plugins.list.untracked", "Server not found")

        await ws.emit(
            "plugins.list.untracked.success", await server.list_untracked_addons()
        )
    except Exception as e:
        await send_error(ws, "plugins.list.untracked", str(e))


@router.on("plugins.categories")
async def get_categories(ws: WebSocketManager):
    if not client:
        return await send_error(ws, "plugins.search", "Modrinth client not initialized")
    try:
        tags = await client.get_category_tags()
        await ws.emit("plugins.categories.success", [tag.to_dict() for tag in tags])
    except Exception as e:
        await send_error(ws, "plugins.categories", str(e))


@router.on("plugins.type")
async def get_server_type(ws: WebSocketManager, server_id: str):
    try:
        server = await serverService.get_server_instance(server_id)
        if not server:
            return await send_error(ws, "plugins.type", "Server not found")

        await ws.emit(
            "plugins.type.success",
            {
                "type": get_addon_type_for_server(server.config.type),
                "version": server.config.version,
                "loader": server.config.type,
            },
        )
    except Exception as e:
        await send_error(ws, "plugins.type", str(e))
