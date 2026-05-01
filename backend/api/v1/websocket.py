import logging
from typing import Optional
from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from modules.router import WebSocketManager
from .auth import decode_token  # Import JWT decoder from your auth module

api = APIRouter()
logger = logging.getLogger(__name__)

@api.websocket("/ws")
async def websocket(websocket: WebSocket, token: Optional[str] = None):
    """
    WebSocket endpoint for real-time messaging.
    Requires valid JWT Bearer token for authentication.
    Token can be passed as a query parameter: /ws?token=<your_token>
    """
    logger.info("WebSocket connection attempt")
    try:
        # Extract token from query params if not provided directly
        token = websocket.query_params.get("token")

        if not token:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="No token provided"
            )
            return

        # Validate JWT token using the same auth logic
        try:
            username = decode_token(token)
        except Exception:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token"
            )
            return

        if username != "root":
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized user"
            )
            return

        logger.info(f"WebSocket authenticated for user: {username}")

        # Create and start the WebSocket handler
        handler = WebSocketManager(websocket)
        await handler.start()

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except Exception:
            pass