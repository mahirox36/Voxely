from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import time
import asyncio
from .utils import get_server_instance

router = APIRouter(tags=["console"])

# WebSocket manager for real-time updates
websocket_connections = {}

@router.websocket("/{server_name}/console")
async def websocket_endpoint(websocket: WebSocket, server_name: str):
    """WebSocket endpoint for real-time console output"""
    await websocket.accept()
    
    if server_name not in websocket_connections:
        websocket_connections[server_name] = []
    websocket_connections[server_name].append(websocket)
    
    server = get_server_instance(server_name)
    
    async def send_to_websocket(message: str):
        try:
            formatted_message = format_console_message(message)
            await websocket.send_text(formatted_message)
        except Exception as e:
            print(f"Error sending message to WebSocket: {e}")
    
    server.set_output_callback(send_to_websocket)
    
    try:
        if hasattr(server, 'logs') and server.logs:
            for line in server.logs[-100:]:
                formatted_line = format_console_message(line)
                await websocket.send_text(formatted_line)
                await asyncio.sleep(0.01)
        else:
            await websocket.send_text(format_console_message("Console ready. Server not started yet.", "system"))
        
        while True:
            try:
                data = await websocket.receive_text()
                if data.startswith("cmd:"):
                    command = data[4:]
                    server.send_command(command)
            except WebSocketDisconnect:
                break
    except Exception as e:
        await websocket.close(code=1001, reason=str(e))
    finally:
        if server_name in websocket_connections:
            if websocket in websocket_connections[server_name]:
                websocket_connections[server_name].remove(websocket)

def format_console_message(message: str, message_type: str | None = None) -> str:
    # Use match-case for clearer message type detection (Python 3.10+)
    lowered = message.lower()
    if message_type is None:
        match True:
            case _ if "error" in lowered or "severe" in lowered:
                message_type = "error"
            case _ if "warn" in lowered or "warning" in lowered:
                message_type = "warning"
            case _ if "done " in lowered and "for help" in lowered:
                message_type = "success"
            case _ if "info" in lowered:
                message_type = "info"
            case _ if "debug" in lowered:
                message_type = "debug"
            case _ if "eula" in lowered:
                message_type = "eula"
            case _ if "fail" in lowered or "exception" in lowered or "traceback" in lowered:
                message_type = "critical"
            case _ if "starting" in lowered or "started" in lowered:
                message_type = "startup"
            case _ if "stopping" in lowered or "stopped" in lowered:
                message_type = "shutdown"
            case _:
                message_type = "default"
    
    return json.dumps({
        "text": message,
        "type": message_type,
        "timestamp": time.strftime("%H:%M:%S")
    })