import asyncio
from functools import partial
from logging import getLogger
from fastapi import APIRouter, Body, HTTPException, Request
from typing import Any, Dict
from pydantic import BaseModel
from datetime import datetime
from ..auth import get_current_user
from .utils import get_server_instance
import nbtlib
from nbtlib import (
    Compound,
    Int,
    Byte,
    IntArray,
    Double,
    Float,
    Short,
    String,
    List,
    Long,
    ByteArray,
    LongArray,
)

# from nbtlib import File

logger = getLogger(__name__)
router = APIRouter(tags=["players"], prefix="/players")

async def load_nbt(file_path):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(nbtlib.load, file_path))

async def save_nbt(file):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, file.save)


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


@router.get("/get")
async def get(request: Request, server_name: str):
    server = await get_server_instance(server_name)
    players = await server.cached_players()
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
            data["name"] = players[player]
            data["uuid"] = player
        players_data.append(data)
    return players_data


@router.get("/status")
async def status(request: Request, server_name: str):
    server = await get_server_instance(server_name)
    players = await  server.cached_players()
    online_players = await server.players
    return {"online": len(online_players), "players": len(players), "online_players": online_players}


@router.post("/{player_uuid}")
async def update_player(
    request: Request,
    server_name: str,
    player_uuid: str,
    data: Dict[str, Any] = Body(...),
):
    server = await get_server_instance(server_name)
    players_folder = await  server.world_folder() / "playerdata"
    player_data_file = players_folder / f"{player_uuid}.dat"
    
    logger.info(player_data_file)

    try:
        file = await load_nbt(player_data_file)
    except FileNotFoundError:
        raise HTTPException(404, "Player data not found")

    # Convert JSON → NBT
    nbt_data = await asyncio.to_thread(nbt_to_json, file)

    # Update root compound
    for key, value in nbt_data.items():  # type: ignore
        file[key] = value

    # Save back
    await save_nbt(file)

    logger.info(f"Updated NBT for {player_uuid}")
    return {"status": "success", "updated_keys": list(data.keys())}