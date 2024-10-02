import os
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer, BadSignature
import uvicorn
from Libs.accounts import Accounts
from Libs.basemodels import CreateServerRequest, ServerNameRequest, AccountsInfo
from Libs.servers import Server, ExistingServer, get_servers
from Libs.jar import MinecraftServerDownloader
import time
import json
from rich import print
from typing import Dict

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

online_servers: Dict[str, ExistingServer] = {}
accounts = Accounts()

app = FastAPI(docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="website"), name="static")
web = Jinja2Templates(directory="website")

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

def sendServerName(server: str):
    return server.replace("_.", " ")
def receiveServerName(server: str):
    return server.replace(" ", "_.")
def addServerOnline(server):
    return receiveServerName(server)
def removeServerOnline(server):
    return sendServerName(server)

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
    Server(addServerOnline(request.server), server_type, request.version, maxRam=request.maxRam)
    return {"status": "created"}

@app.post("/start")
def start(request: ServerNameRequest):
    try:
        server = ExistingServer(addServerOnline(request.server))
        online_servers.update({request.server: server})
        print(online_servers)
    except KeyError:
        raise HTTPException(status_code=404, detail="Server not found")
    print("Starting server")
    server.start()
    return {"status": "started"}

@app.post("/stop")
def stop(request: ServerNameRequest):
    try:
        server = online_servers.get(removeServerOnline(request.server))
    except KeyError:
        raise HTTPException(status_code=404, detail="Server not found")
    server.stop()
    online_servers.pop(request.server)
    return {"status": "stopped"}

@app.post("/accept_eula")
def accept_eula(request: ServerNameRequest):
    try:
        ExistingServer(request.server.replace(" ","_.")).acceptEula()
    except KeyError:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"status": "accepted"}

@app.post("/is_created")
def is_created(request: ServerNameRequest):
    try:
        ExistingServer(request.server.replace(" ","_."))
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
    return render("dash.html", request)

@app.get("/create")
def create_page(request: Request, user: str = Depends(get_current_user)):
    if user == False:
        return HTMLResponse(status_code=302, headers={"Location": "/login"})
    
    return render("create.html", request)

@app.get("/servers/{server}")
def server_page(request: Request, server: str, user: str = Depends(get_current_user)):
    if user == False:
        return HTMLResponse(status_code=302, headers={"Location": "/login"})
    if server not in get_servers():
        return HTMLResponse(status_code=404)
    serverMinecraft = ExistingServer(server)
    data = serverMinecraft.data
    data["name"] = sendServerName(data["name"])
    return render("server.html", request, server=data)


# Discord and Github Routes
@app.get("/discord")
def discord():
    return HTMLResponse(status_code=302, headers={"Location": "https://discord.gg/YmDsbFHHtQ"})
@app.get("/github")
def github():
    return HTMLResponse(status_code=302, headers={"Location": "https://github.com/mahirox36/MineGimmeThat"})

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8001)