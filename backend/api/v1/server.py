from modules.router import WebSocketManager, WSEventError, router
from modules.ServerService import ServerCreationRequest, ServerService

serverService = ServerService()


@router.on("server.backup")
async def start_backup(ws: WebSocketManager, server_id: str):
    server = await serverService.get_server_instance(server_id)
    if not server:
        return await ws.emit("server.backup.error", {"message": "Server not found"})

    await server.backup.create_backup()


@router.on("server.backup.list")
async def list_backups(ws: WebSocketManager, server_id: str):
    server = await serverService.get_server_instance(server_id)
    if not server:
        return await ws.emit(
            "server.backup.list.error", {"message": "Server not found"}
        )

    backups = await server.backup.list_backups()
    await ws.emit("server.backup.list.success", {"backups": backups})


@router.on("server.backup.restore")
async def restore_backup(ws: WebSocketManager, server_id: str, filename: str):
    server = await serverService.get_server_instance(server_id)
    if not server:
        return await ws.emit(
            "server.backup.restore.error", {"message": "Server not found"}
        )

    try:
        await server.backup.restore_backup(filename)
    except FileNotFoundError:
        await ws.emit(
            "server.backup.restore.error",
            {"message": f"Backup file {filename} not found"},
        )
    except Exception as e:
        await ws.emit("server.backup.restore.error", {"message": str(e)})


@router.on("server.list")
async def list_servers(ws: WebSocketManager):
    servers = serverService.servers.values()
    await ws.emit(
        "server.list.success",
        {"servers": [await server.export_server() for server in servers]},
    )


@router.on("server.get")
async def get_server(ws: WebSocketManager, server_id: str):
    server = await serverService.get_server_instance(server_id)
    if not server:
        return await ws.emit("server.get.error", {"message": "Server not found"})

    await ws.emit("server.get.success", {"server": await server.export_server()})


@router.on("server.delete")
async def delete_server(ws: WebSocketManager, server_id: str):
    server = await serverService.get_server_instance(server_id)
    if not server:
        return await ws.emit("server.delete.error", {"message": "Server not found"})

    await serverService.delete_server(server_id)
    await ws.emit(
        "server.delete.success",
        {"message": f"Server {server.config.name} deleted successfully"},
    )


@router.on("server.create")
async def create_server(ws: WebSocketManager, server_data: ServerCreationRequest):
    try:
        server = await serverService.create_server(server_data, ws)
        await ws.emit("server.create.success", {"server": await server.export_server()})
    except Exception as e:
        await ws.emit("server.create.error", {"message": str(e)})


@router.on("server.subscribe")
async def on_server_subscribe(ws: WebSocketManager, server_id: str):
    """Client starts watching a specific server."""
    server = await serverService.get_server_instance(server_id)
    if not server:
        raise WSEventError(404, f"Server '{server_id}' not found")

    await ws.subscribe_server(server)
    await ws.emit("server.subscribed", {"server_id": server_id})


@router.on("server.unsubscribe")
async def on_server_unsubscribe(ws: WebSocketManager, server_id: str):
    """Client stops watching a specific server."""
    await ws.unsubscribe_server(server_id)
    await ws.emit("server.unsubscribed", {"server_id": server_id})


# @router.on("server.versions")
# async def get_available_versions(ws: WebSocketManager):
#     """Get available Minecraft versions for different server types"""

#     try:
#         downloader = serverService.jar_downloader
#         purpur = downloader.get_purpur_versions()
#         purpur.reverse()
#         forge: List[str] = list(downloader.get_forge_versions().keys())
#         forge.reverse()
#         # forge = {i: key for i, key in enumerate(forge_keys, start=0)}
#         return {
#             "vanilla": downloader.get_vanilla_versions(),
#             "paper": downloader.get_paper_versions(),
#             "fabric": downloader.get_fabric_versions(),
#             "forge": forge,
#             "neoforge": downloader.get_neoforge_versions(),
#             "purpur": purpur,
#         }
#     except Exception as e:
#         raise HTTPException(
#             status_code=500, detail=f"Failed to fetch versions: {str(e)}"
#         )
