from fastapi import APIRouter
from . import auth, server, modrinth

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(server.router)
router.include_router(modrinth.router)

__all__ = ["router"]