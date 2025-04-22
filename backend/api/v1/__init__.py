from fastapi import APIRouter
from .auth import router as auth_router
from .servers import router as servers_router

router = APIRouter(prefix="/api/v1")

router.include_router(auth_router)
router.include_router(servers_router)

__all__ = ["router"]