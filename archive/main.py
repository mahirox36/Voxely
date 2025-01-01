import asyncio
import os
from fastapi import FastAPI, HTTPException, Request, Response, Depends, WebSocket
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware  # Add CORS middleware
from itsdangerous import URLSafeTimedSerializer, BadSignature
import uvicorn
from Libs.accounts import Accounts
from Libs.basemodels import CreateServerRequest, ServerNameRequest, AccountsInfo
from Libs.servers import Server, get_servers
from Libs.jar import MinecraftServerDownloader
from contextlib import asynccontextmanager
from Libs.websocket import WebSocketManager
import time
import json
from rich import print
from typing import Dict, List
from rich.console import Console
console = Console()
# Initialize global variables
online_servers: Dict[str, Server] = {}
accounts = Accounts()
manager = WebSocketManager()

if not os.path.exists("servers"):
    os.makedirs("servers")

# Start the monitoring task when the application starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the monitoring task when the app starts
    monitoring_task = asyncio.create_task(monitor_servers())
    yield
    # Cancel the task when the app shuts down
    monitoring_task.cancel()
    try:
        await monitoring_task
    except asyncio.CancelledError:
        pass


app = FastAPI(docs_url=None, redoc_url=None, lifespan=lifespan)

# Add CORS middleware to allow frontend connections
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # In production, replace with your frontend URL
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

app.mount("/static", StaticFiles(directory="static"), name="static")
web = Jinja2Templates(directory="static")

# Load secret key
if not os.path.exists(".secrets/config.json"):
    with open(".secrets/config.json", "w") as f:
        json.dump({"SECRET_KEY": "secret"}, f)
    print("Please configure the secret key in .secrets/config.json")
    input("Press enter to exit")
    exit()
with open(".secrets/config.json", "r") as f:
    data = json.load(f)
    SECRET_KEY = data["SECRET_KEY"]
    if SECRET_KEY == "secret":
        print("Please configure the secret key in .secrets/config.json")
        input("Press enter to exit")
        exit()

serializer = URLSafeTimedSerializer(SECRET_KEY)

# Server name handling functions
def sendServerName(server: str):
    return server.replace("_.", " ")

def receiveServerName(server: str):
    return server.replace(" ", "_.")

def addServerOnline(server):
    return receiveServerName(server)

def removeServerOnline(server):
    return sendServerName(server)

# Console output handler
async def handle_console_output(server_name: str, message: str):
    """Broadcast console output to WebSocket clients"""
    if "RCON" not in str(message):
        await manager.broadcast({
            "type": "console",
            "server": server_name,
            "line": message
        })

# Server status handler
async def handle_server_status(server_name: str, status: str):
    """Handle server status updates and broadcast them to connected clients"""
    await manager.broadcast({
        "type": "status",
        "server": server_name,
        "status": status
    })


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Handle different types of messages
            if "command" in data:
                server_name = data.get("server")
                if server_name in online_servers:
                    server = online_servers[server_name]
                    try:
                        await server.send_command(data["command"])
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Error executing command: {str(e)}"
                        })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Server not found or not running"
                    })
            
            elif "get_status" in data:
                server_name = data.get("server")
                if server_name in online_servers:
                    server = online_servers[server_name]
                    await websocket.send_json({
                        "type": "status",
                        "server": server_name,
                        "status": server.status
                    })
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        manager.disconnect(websocket)
        
# Server monitoring task
async def monitor_servers():
    """Monitor server metrics and broadcast them periodically"""
    while True:
        for server_name, server in online_servers.items():
            try:
                # Get server metrics
                metrics = await server.get_metrics(True)
                await manager.broadcast({
                    "type": "metrics",
                    "server": server_name,
                    "metrics": metrics
                })
            except Exception as e:
                console.print_exception()
                print(f"Error monitoring server {server_name}: {e}")
        #TODO: Change it to every 1m
        await asyncio.sleep(1)  # Update every 5 seconds


def render(name: str,request: Request, **kwargs) -> HTMLResponse:
    kwargs.update({"time": time.time()})
    return web.TemplateResponse(name, {"request": request, **kwargs})

@app.get("/")
def read_root(request: Request):
    return HTMLResponse(status_code=302, headers={"Location": "/dashboard"})

@app.get("/homepage")
def homepage(request: Request):   
    return render("index.html", request)


@app.post("/create")
def create(request: CreateServerRequest):
    try:
        server_type = request.type
    except KeyError:
        raise HTTPException(status_code=422, detail="Invalid server type")
    request.maxRam = int(request.maxRam) * 1024
    request.minRam = int(request.minRam) * 1024
    Server(addServerOnline(request.name), server_type, request.version, request.minRam, request.maxRam, request.port, request.maxPlayers)
    return {"status": "created"}

async def setOnline(server: Server,server_name: str):
    while True:
        if server.status == "online":
            await handle_server_status(server_name, "online")
        await asyncio.sleep(1.0)
        

@app.post("/start")
async def start(request: ServerNameRequest):
    try:
        server_name = addServerOnline(request.server)
        server = Server(server_name)
        await handle_server_status(server_name, "starting")
        # Set up output callback
        async def output_callback(line: str):
            await handle_console_output(request.server, line)
        server.set_output_callback(output_callback)

        online_servers[request.server] = server
        server.start()
        asyncio.create_task(setOnline(server,server_name))
        # await handle_server_status(server_name, "online")
        return {"status": "started"}
    except Exception as e:
        print(str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop")
async def stop(request: ServerNameRequest):
    try:
        server_name = removeServerOnline(request.server)  # Ensure the correct format
        server = online_servers.get(server_name)
        
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        await handle_server_status(server_name, "stopping")

        # Stop the server and remove it from the online_servers dictionary
        server.stop()
        online_servers.pop(server_name, None)
        
        # Send a status update indicating the server has stopped
        await handle_server_status(server_name, "offline")
        
        return {"status": "stopped"}
    except Exception as e:
        print(f"Error stopping server {request.server}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/accept_eula")
def accept_eula(request: ServerNameRequest):
    try:
        Server(request.server.replace(" ","_.")).accept_eula()
    except KeyError:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"status": "accepted"}

@app.post("/is_created")
def is_created(request: ServerNameRequest):
    try:
        Server(request.server.replace(" ","_."))
        return {"status": True}
    except FileNotFoundError:
        return {"status": False}
    
@app.post("/servers")
def servers():
    return {"servers": get_servers(True)}

@app.post("/versions")
def versions():
    downloader =MinecraftServerDownloader()
    versions = {
        "Fabric"    : downloader.get_fabric_versions(),
        "Paper"     : downloader.get_paper_versions(),
        "Vanilla"   : downloader.get_vanilla_versions()
    }
    return versions

@app.post("/server_info")
def server_info(request: ServerNameRequest):
    try:
        server = Server(request.server.replace(" ","_."))
    except KeyError:
        raise HTTPException(status_code=404, detail="Server not found")
    ip = server.get_ip()
    return {
        "name": server.data["name"],
        "type": server.data["type"],
        "version": server.data["version"],
        "maxRam": server.data["maxRam"],
        "players": 5,
        "IP": server.ip,
        "status": server.status
    }
    
# Post register and login routes here
@app.post("/register")
def register(account: AccountsInfo, response: Response):
    if accounts.account_exists(account.username):
        return {"success": False}
    token = serializer.dumps(account.username)
    response.set_cookie(key="session_token", value=token)
    accounts.register(account.username, account.password)
    return {"success": True}

@app.post("/loginpost")
def login(account: AccountsInfo, response: Response):
    if accounts.login(account.username, account.password):
        token = serializer.dumps(account.username)
        response.set_cookie(key="session_token", value=token)
        return {"success": True}
    return {"success": False}

def get_current_user(request: Request):
    token = request.cookies.get("session_token")
    if not token:
        return False
    try:
        username = serializer.loads(token, max_age=604800)  # Token valid for 7 days
    except BadSignature:
        return False
    return username
@app.get("/login")
def login_page(request: Request, user: str = Depends(get_current_user)):
    if user != False:
        return HTMLResponse(status_code=302, headers={"Location": "/dashboard"})
    return render("login.html", request)

@app.get("/logout")
def logout(request: Request, response: Response):
    response.delete_cookie("session_token")
    return HTMLResponse(status_code=302, headers={"Location": "/"})

#Main Website like dashboard, servers, etc
@app.get("/dashboard")
def dashboard(request: Request, user: str = Depends(get_current_user)):
    if user == False:
        return HTMLResponse(status_code=302, headers={"Location": "/login"})
    
    # Get user's servers
    user_servers = get_servers(True)
    servers_info = []
    for server in user_servers:
        try:
            server_obj = Server(server.replace(" ", "_."))
            servers_info.append({
                "name": server,
                "status": server_obj.status
            })
        except Exception as e:
            print(f"Error getting server info for {server}: {e}")
            servers_info.append({
                "name": server,
                "status": "Unknown"
            })
    print(servers_info)

    # Mock data for other statistics
    # In a real scenario, you'd fetch this data from your database or other sources
    context = {
        "username": user,
        "notifications": [
            "3 new messages",
            "Server maintenance tomorrow",
            "New user joined"
        ],
        "active_users": 120,
        "new_signups": 30,
        "total_servers": len(user_servers),
        "servers": servers_info
    }
    return render("dash.html", request, **context)

@app.get("/settings")
def settings(request: Request, user: str = Depends(get_current_user)):
    if user == False:
        return HTMLResponse(status_code=302, headers={"Location": "/login"})
    
    return render("settings.html", request)

@app.get("/create")
def create_page(request: Request, user: str = Depends(get_current_user)):
    if user == False:
        return HTMLResponse(status_code=302, headers={"Location": "/login"})
    
    return render("create.html", request)

@app.get("/servers/{server}")
async def server_page(request: Request, server: str, user: str = Depends(get_current_user)):
    if user == False:
        return HTMLResponse(status_code=302, headers={"Location": "/login"})
    if server not in get_servers():
        return HTMLResponse(status_code=404)
    serverMinecraft = Server(server)
    data = serverMinecraft.data
    data["name"] = sendServerName(data["name"])
    data["public"] = serverMinecraft.ip["public"]
    data["private"] = serverMinecraft.ip["private"]
    metrics= await serverMinecraft.get_metrics()
    data["lengthPlayers"] = metrics["player_count"]
    data["uptime"] = metrics["uptime"]
    data["cpu"] = f"%{metrics["cpu_usage"]}"
    data["ram"] = f"%{metrics["memory_usage"]}"
    data["type"] = str(data["type"]).capitalize()
    print(data)
    return render("server.html", request, server=data)

@app.get("/test")
async def test(request: Request):
    await broadcast_message("Hello")
    return "ABC"

# Discord and Github Routes
@app.get("/discord")
def discord():
    return HTMLResponse(status_code=302, headers={"Location": "https://discord.gg/YmDsbFHHtQ"})
@app.get("/github")
def github():
    return HTMLResponse(status_code=302, headers={"Location": "https://github.com/mahirox36/MineGimmeThat"})

# Websocket

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(1)
            print(manager.active_connections)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        manager.disconnect(websocket)

async def broadcast_message(message: dict):
    await manager.broadcast(message)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8001)
    
#TODO: Add a Server Status in the server page
#TODO: Add a way to delete servers
#TODO: Add a way to edit servers
#TODO: Add Server uptime
#TODO: Add Server Cpu Usage, memory usage, disk usage,Players online, Description, and Version
#TODO: Add a way to change the server version
#TODO: Add Player Management, Logs, Terminal, Scheduled Tasks, Server Settings (Configurations), Server Files, Server Backups, and Metrics
#TODO: Add a way to change the server type
#TODO: Add a way to upload files to the server and download files from the server
#TODO: Easy Way to explore Configurations of the server or Mods/Plugins installed
#TODO: Add a way to install mods/plugins