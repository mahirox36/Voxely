from datetime import datetime
import json
import logging
import os
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
import asyncio
import time

from watchfiles import awatch
from ..auth import get_current_user
from modules.servers import Server, ServerType, get_servers
from modules.jar import MinecraftServerDownloader
from .utils import get_server_instance, process_server

logger = logging.getLogger(__name__)
router = APIRouter(tags=["management"])


class ServerResponse(BaseModel):
    name: str
    status: str
    type: str
    version: str
    metrics: Dict[str, str]
    port: int
    maxPlayers: int
    players: Optional[List[str]] = None
    ip: Optional[Dict[str, str]] = None


def format_console_message(message: str, message_type: str | None = None):
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
            case _ if (
                "fail" in lowered or "exception" in lowered or "traceback" in lowered
            ):
                message_type = "critical"
            case _ if "starting" in lowered or "started" in lowered:
                message_type = "startup"
            case _ if "stopping" in lowered or "stopped" in lowered:
                message_type = "shutdown"
            case _:
                message_type = "default"

    return {
        "text": message,
        "type": message_type,
        "timestamp": time.strftime("%H:%M:%S"),
    }


@router.get("/get", response_model=List[ServerResponse])
async def list_servers(request: Request):
    """Get all servers with their current status"""
    current_user = await get_current_user(request)

    try:
        server_names = get_servers()
        if not server_names:
            return []

        tasks = [process_server(name) for name in server_names]
        servers_info = await asyncio.gather(*tasks)
        return [server for server in servers_info if server is not None]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve servers: {str(e)}"
        )


@router.get("/versions")
async def get_available_versions(request: Request):
    """Get available Minecraft versions for different server types"""
    current_user = await get_current_user(request)

    try:
        downloader = MinecraftServerDownloader()
        purpur = downloader.get_purpur_versions()
        purpur.reverse()
        return {
            "vanilla": downloader.get_vanilla_versions(),
            "paper": downloader.get_paper_versions(),
            "fabric": downloader.get_fabric_versions(),
            "purpur": purpur,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch versions: {str(e)}"
        )


@router.post("/create", status_code=201)
async def create_server(
    request: Request,
    name: str = Form(...),
    type: str = Form(...),
    version: str = Form(...),
    minRam: int = Form(...),
    maxRam: int = Form(...),
    port: int = Form(...),
    maxPlayers: int = Form(...),
    jar_file: Optional[UploadFile] = File(None),  # optional file
):
    """Create a new Minecraft server"""
    current_user = await get_current_user(request)

    try:
        try:
            server_type = ServerType(type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid server type. Must be one of: {', '.join([t.value for t in ServerType])}",
            )
        if jar_file:
            # Save uploaded jar to 'versions/' folder
            file_location = f"versions/{jar_file.filename}"
            with open(file_location, "wb") as f:
                f.write(await jar_file.read())
            jar = file_location

        server = await Server.init(
            name=name,
            type=server_type,
            version=version,
            min_ram=minRam,
            max_ram=maxRam,
            port=port,
            players_limit=maxPlayers,
            jar=jar,
        )

        return {"message": "Server created successfully", "needsEulaAcceptance": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


HEARTBEAT_INTERVAL = 15


@router.websocket("/ws/{server_name}")
async def websocket_server(websocket: WebSocket, server_name: str):
    """WebSocket endpoint for real-time console + file updates"""
    current_user = await get_current_user(websocket)  # type: ignore
    await websocket.accept()
    server = await get_server_instance(server_name)
    server.append_websocket(websocket)

    def accepted_eula():
        eula_path = server.path / "eula.txt"
        return eula_path.exists()

    async def send_to_websocket(message: str):
        try:
            formatted_message = format_console_message(message)
            await websocket.send_json({"type": "console", "data": formatted_message})
        except Exception as e:
            print(f"Error sending message to WebSocket: {e}")

    server.set_output_callback(send_to_websocket)

    # Send recent logs
    if hasattr(server, "logs") and server.logs:
        for line in server.logs[-100:]:
            formatted_line = format_console_message(line)
            await websocket.send_json({"type": "console", "data": formatted_line})
            await asyncio.sleep(0.01)
    else:
        await websocket.send_json(
            {
                "type": "console",
                "data": format_console_message(
                    "Console ready. Server not started yet.", "system"
                ),
            }
        )

    async def get_info():
        metrics = await server.get_metrics(True)
        return {
            "name": server.name,
            "status": server.status,
            "type": server.type,
            "version": server.version,
            "metrics": metrics if isinstance(metrics, dict) else metrics.__dict__,
            "port": server.port,
            "maxPlayers": server.players_limit,
            "players": await server.players,
            "ip": server.ip,
        }

    async def send_heartbeat():
        while True:
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                break
            await asyncio.sleep(HEARTBEAT_INTERVAL)

    async def get_server_info():
        try:
            await websocket.send_json({"type": "info", "data": await get_info()})
        except Exception as e:
            await websocket.send_json({"type": "error", "data": str(e)})

    async def start_server():
        try:
            if server.status == "online":
                await websocket.send_json(
                    {"type": "error", "data": "Server is already running"}
                )
            await server.start()
        except Exception as e:
            await websocket.send_json({"type": "error", "data": str(e)})

    async def stop_server():
        try:
            if server.status == "offline":
                await websocket.send_json(
                    {"type": "error", "data": "Server is not running"}
                )
            await server.stop()
        except Exception as e:
            await websocket.send_json({"type": "error", "data": str(e)})

    async def restart_server():
        try:
            await server.restart()
        except Exception as e:
            await websocket.send_json({"type": "error", "data": str(e)})

    async def send_command(command: str):
        try:
            if server.status != "online":
                await websocket.send_json(
                    {"type": "error", "data": "Server is not running"}
                )
            await server.send_command(command)
        except Exception as e:
            await websocket.send_json({"type": "error", "data": str(e)})

    async def watch_files():
        base_path =  server.path
        if not base_path.exists():
            await websocket.send_json({"type": "error", "data": "Path not found"})
            return

        async def list_files():
            locked_files = ["server.json", "server.log", "server.jar", "eula.txt"]
            files = []
            for entry in base_path.rglob("*"):
                if entry.name in locked_files:
                    continue
                try:
                    stat = entry.stat()
                    files.append(
                        {
                            "path": str(entry.relative_to(server.path)).replace("\\", "/"),
                            "name": entry.name,
                            "type": "directory" if entry.is_dir() else "file",
                            "size": stat.st_size if not entry.is_dir() else None,
                            "modified": datetime.fromtimestamp(
                                stat.st_mtime
                            ).isoformat(),
                        }
                    )
                except Exception as e:
                    print(f"Error processing {entry}: {e}")
            return sorted(files, key=lambda x: (x["type"] == "file", x["name"].lower()))

        # Send initial list
        await websocket.send_json({"type": "file_init", "data": await list_files()})

        # Watch directory for changes
        async for changes in awatch(base_path):
            events = []
            for change_type, file_path in changes:
                events.append(
                    {
                        "event": change_type.name,
                        "path": os.path.relpath(file_path, server.path),
                    }
                )
            await websocket.send_json(
                {
                    "type": "file_update",
                    "changes": events,
                    "data": await list_files(),
                }
            )

    async def handle_messages():
        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("action", "")
                if msg_type == "pong":
                    continue
                elif msg_type == "start":
                    await start_server()
                elif msg_type == "restart":
                    await restart_server()
                elif msg_type == "stop":
                    await stop_server()
                elif msg_type == "command":
                    await send_command(data.get("data", ""))
                else:
                    continue
        except WebSocketDisconnect:
            logger.info("Client disconnected")
        except Exception as e:
            logger.warning(f"Message handling error: {e}")

    # --- Start tasks ---
    heartbeat_task = asyncio.create_task(send_heartbeat())
    message_task = asyncio.create_task(handle_messages())
    watch_task = asyncio.create_task(watch_files())

    try:
        await get_server_info()

        if not accepted_eula():
            await websocket.send_json({"type": "need_eula"})

        logger.info("WebSocket connection established")
        done, pending = await asyncio.wait(
            [heartbeat_task, message_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        logger.warning(f"WebSocket error: {e}")

    finally:
        for task in [heartbeat_task, message_task]:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        try:
            server.remove_websocket(websocket)
            await websocket.close()
        except Exception:
            pass
