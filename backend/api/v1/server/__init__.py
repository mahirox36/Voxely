from fastapi import APIRouter
from . import management, files, plugins, backups, logs, settings, players

router = APIRouter(prefix="/servers", tags=["servers"])
server = APIRouter(prefix="/{server_name}", tags=["servers"])

# Include all routers
# server.include_router(management.yes_router)
router.include_router(management.router)
server.include_router(files.router)
server.include_router(plugins.router)
server.include_router(backups.router)
server.include_router(logs.router)
server.include_router(settings.router)
server.include_router(players.router)

router.include_router(server)