from fastapi import APIRouter
from . import auth, server

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(server.router)

__all__ = ["router"]