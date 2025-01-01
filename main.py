from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from itsdangerous import URLSafeTimedSerializer, BadSignature
import asyncio
import os
import json
from typing import Dict, Optional
from pydantic import BaseModel
from contextlib import asynccontextmanager

from Libs.accounts import Accounts
from Libs.servers import Server, get_servers
from Libs.jar import MinecraftServerDownloader
from Libs.websocket import WebSocketManager

# Initialize global variables
online_servers: Dict[str, Server] = {}
accounts = Accounts()
manager = WebSocketManager()

# Base models
class CreateServerRequest(BaseModel):
    name: str
    type: str
    version: str
    minRam: int
    maxRam: int
    port: int
    maxPlayers: int

class AccountsInfo(BaseModel):
    username: str
    password: str

class TokenData(BaseModel):
    username: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    monitoring_task = asyncio.create_task(monitor_servers())
    yield
    monitoring_task.cancel()
    try:
        await monitoring_task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load secret key
if not os.path.exists(".secrets/config.json"):
    os.makedirs(".secrets", exist_ok=True)
    with open(".secrets/config.json", "w") as f:
        json.dump({"SECRET_KEY": "your-secret-key-here"}, f)

with open(".secrets/config.json") as f:
    config = json.load(f)
    SECRET_KEY = config["SECRET_KEY"]

serializer = URLSafeTimedSerializer(SECRET_KEY)

def format_server_name(name: str, to_storage: bool = True) -> str:
    return name.replace(" ", "_.") if to_storage else name.replace("_.", " ")

async def monitor_servers():
    while True:
        for server_name, server in online_servers.items():
            try:
                metrics = await server.get_metrics(True)
                await manager.broadcast({
                    "type": "metrics",
                    "server": server_name,
                    "metrics": metrics
                })
            except Exception as e:
                print(f"Error monitoring server {server_name}: {e}")
        await asyncio.sleep(60)

async def get_current_user(token: str) -> Optional[str]:
    try:
        return serializer.loads(token, max_age=604800)
    except BadSignature:
        return None

# Auth Routes
@app.post("/api/auth/register")
async def register(account: AccountsInfo):
    if accounts.account_exists(account.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    accounts.register(account.username, account.password)
    return {"token": serializer.dumps(account.username)}

@app.post("/api/auth/login")
async def login(account: AccountsInfo):
    if accounts.login(account.username, account.password):
        return {"token": serializer.dumps(account.username)}
    raise HTTPException(status_code=401, detail="Invalid credentials")

# Server Routes
@app.get("/api/servers")
async def get_servers_list(username: str = Depends(get_current_user)):
    if not username:
        raise HTTPException(status_code=401)
    
    servers_list = get_servers(True)
    servers_info = []
    
    for server in servers_list:
        try:
            server_obj = Server(format_server_name(server))
            metrics = await server_obj.get_metrics()
            servers_info.append({
                "name": server,
                "status": server_obj.status,
                "type": server_obj.data["type"],
                "version": server_obj.data["version"],
                "port": server_obj.data["port"],
                "metrics": metrics
            })
        except Exception as e:
            print(f"Error getting server info for {server}: {e}")
    
    return {"servers": servers_info}

@app.post("/api/servers")
async def create_server(request: CreateServerRequest, username: str = Depends(get_current_user)):
    if not username:
        raise HTTPException(status_code=401)
    
    try:
        request.maxRam *= 1024
        request.minRam *= 1024
        server_name = format_server_name(request.name)
        
        Server(server_name, request.type, request.version, request.minRam, 
               request.maxRam, request.port, request.maxPlayers)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/servers/{server_name}")
async def get_server_info(server_name: str, username: str = Depends(get_current_user)):
    if not username:
        raise HTTPException(status_code=401)
    
    try:
        server = Server(format_server_name(server_name))
        metrics = await server.get_metrics()
        
        return {
            "name": server_name,
            "type": server.data["type"],
            "version": server.data["version"],
            "maxRam": server.data["maxRam"],
            "minRam": server.data["minRam"],
            "port": server.data["port"],
            "maxPlayers": server.data["maxPlayers"],
            "ip": server.get_ip(),
            "status": server.status,
            "metrics": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/servers/{server_name}/start")
async def start_server(server_name: str, username: str = Depends(get_current_user)):
    if not username:
        raise HTTPException(status_code=401)
    
    try:
        server = Server(format_server_name(server_name))
        
        async def output_callback(line: str):
            await manager.broadcast({
                "type": "console",
                "server": server_name,
                "line": line
            })
            
        server.set_output_callback(output_callback)
        online_servers[server_name] = server
        server.start()
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/servers/{server_name}/stop")
async def stop_server(server_name: str, username: str = Depends(get_current_user)):
    if not username:
        raise HTTPException(status_code=401)
    
    try:
        server = online_servers.get(server_name)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        server.stop()
        online_servers.pop(server_name)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/servers/{server_name}/command")
async def send_command(server_name: str, command: str, username: str = Depends(get_current_user)):
    if not username:
        raise HTTPException(status_code=401)
    
    try:
        server = online_servers.get(server_name)
        if not server:
            raise HTTPException(status_code=404)
        
        await server.send_command(command)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/servers/{server_name}/eula")
async def accept_eula(server_name: str, username: str = Depends(get_current_user)):
    if not username:
        raise HTTPException(status_code=401)
    
    try:
        server = Server(format_server_name(server_name))
        server.accept_eula()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/versions")
async def get_versions(username: str = Depends(get_current_user)):
    if not username:
        raise HTTPException(status_code=401)
    
    downloader = MinecraftServerDownloader()
    return {
        "versions": {
            "Fabric": downloader.get_fabric_versions(),
            "Paper": downloader.get_paper_versions(),
            "Vanilla": downloader.get_vanilla_versions()
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)