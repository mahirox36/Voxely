from fastapi import APIRouter
from . import management, files, plugins, backups, logs, settings

router = APIRouter(prefix="/servers", tags=["servers"])

# Include all routers
router.include_router(management.router)
router.include_router(files.router)
router.include_router(plugins.router)
router.include_router(backups.router)
router.include_router(logs.router)
router.include_router(settings.router)