import asyncio
from logging import getLogger
from typing import Any, Dict

import aiofiles
import nbtlib
from modules.router import WebSocketManager, WSEventError, router
from modules.ServerService import ServerService, ServerStatus
from nbtlib import (
    Byte,
    ByteArray,
    Compound,
    Double,
    Float,
    Int,
    IntArray,
    List,
    Long,
    LongArray,
    Short,
    String,
)
from pydantic import BaseModel, Field, validator

# from nbtlib import File

logger = getLogger(__name__)
serverService = ServerService()


class PlayerUpdateRequest(BaseModel):
    """Validation schema for player data updates"""

    data: Dict[str, Any] = Field(...)

    @validator("data")
    def validate_data_size(cls, v):
        # Prevent excessively large data payloads
        import json

        if len(json.dumps(v)) > 1_000_000:  # 1MB limit
            raise ValueError("Player data too large")
        return v


async def load_nbt(file_path):
    async with aiofiles.open(file_path, mode="rb") as f:
        data = await f.read()
    return nbtlib.File.parse(data)


async def save_nbt(file):
    await asyncio.to_thread(file.save)


def nbt_to_json(value):
    if isinstance(value, Compound):
        return {k: nbt_to_json(v) for k, v in value.items()}
    elif isinstance(value, List):
        return [nbt_to_json(v) for v in value]
    elif isinstance(value, Byte):
        return {"type": "byte", "value": int(value)}
    elif isinstance(value, Short):
        return {"type": "short", "value": int(value)}
    elif isinstance(value, Int):
        return {"type": "int", "value": int(value)}
    elif isinstance(value, Long):
        return {"type": "long", "value": int(value)}
    elif isinstance(value, Float):
        return {"type": "float", "value": float(value)}
    elif isinstance(value, Double):
        return {"type": "double", "value": float(value)}
    elif isinstance(value, String):
        return {"type": "string", "value": str(value)}
    elif isinstance(value, (ByteArray, IntArray, LongArray)):
        return {
            "type": value.__class__.__name__.replace("Tag", "").lower(),
            "value": [int(x) for x in value],
        }
    else:
        return value


def json_to_nbt(value):
    if isinstance(value, dict) and "type" in value and "value" in value:
        t, v = value["type"], value["value"]
        if t == "byte":
            return Byte(v)
        if t == "short":
            return Short(v)
        if t == "int":
            return Int(v)
        if t == "long":
            return Long(v)
        if t == "float":
            return Float(v)
        if t == "double":
            return Double(v)
        if t == "string":
            return String(v)
        if t == "bytearray":
            return nbtlib.tag.ByteArray(v)
        if t == "intarray":
            return nbtlib.tag.IntArray(v)
        if t == "longarray":
            return nbtlib.tag.LongArray(v)
        return v  # fallback

    elif isinstance(value, dict):
        return Compound({k: json_to_nbt(v) for k, v in value.items()})
    elif isinstance(value, list):
        if not value:
            return List()
        first = json_to_nbt(value[0])
        return List[type(first)]([json_to_nbt(v) for v in value])
    else:
        # plain JSON fallback (string, int, etc.)
        if isinstance(value, float):
            return Float(value)
        elif isinstance(value, int):
            return Int(value)
        elif isinstance(value, str):
            return String(value)
        return value


@router.on("players.get")
async def get(ws: WebSocketManager, server_id: str):
    server = await serverService.get_server_instance(server_id)
    if not server:
        raise WSEventError(404, "Server not found")
    players = server.players
    players_folder = await server.world_folder() / "playerdata"

    await server.send_command("/save-all")

    players_data: list[Any] = []

    for player in players:
        player_data = players_folder / f"{player}.dat"
        if not player_data.exists():
            continue
        file = await load_nbt(player_data)
        data = await asyncio.to_thread(nbt_to_json, file)
        if isinstance(data, dict):
            data["name"] = player.username
            data["uuid"] = player.uuid
        players_data.append(data)
    await ws.emit("players.get", players_data)


@router.on("player.update")
async def update_player(
    ws: WebSocketManager,
    server_id: str,
    player_uuid: str,
    data: Dict[str, Any],
):
    server = await serverService.get_server_instance(server_id)
    if not server:
        raise WSEventError(404, "Server not found")
    if server.status in (
        ServerStatus.ONLINE,
        ServerStatus.STARTING,
        ServerStatus.STOPPING,
    ):
        raise WSEventError(400, "Cannot update player data while server is running")

    player_data_file = (
        (await server.world_folder()) / "playerdata" / f"{player_uuid}.dat"
    )
    logger.info(player_data_file)

    try:
        nbt_file = await load_nbt(player_data_file)
    except FileNotFoundError:
        raise WSEventError(404, "Player data not found")

    updated_keys = []
    for key, value in data.items():
        nbt_file[key] = json_to_nbt(value)
        updated_keys.append(key)

    # 2. Save using the path specifically to be sure
    await asyncio.to_thread(nbt_file.save, player_data_file)

    logger.info(f"Updated {updated_keys} for {player_uuid}")
    await ws.emit("player.updated", {"status": "success", "updated_keys": updated_keys})
