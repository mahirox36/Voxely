from fastapi import APIRouter

from . import auth, files, plugins, server, websocket  # noqa: F401

apiV1 = APIRouter(prefix="/v1")
# apiV1.include_router(plugins.api, prefix="/plugins", tags=["plugins"])
# apiV1.include_router(server.api, prefix="/server", tags=["server"])
apiV1.include_router(websocket.api, prefix="/websocket", tags=["websocket"])
apiV1.include_router(files.api, prefix="/files", tags=["files"])
apiV1.include_router(auth.api, prefix="/auth", tags=["auth"])
