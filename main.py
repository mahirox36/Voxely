from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from rich import print
from Libs.basemodels import CreateServerRequest, ServerNameRequest
from Libs.servers import Server, status, Type, ExistingServer
from typing import Dict

online_servers: Dict[str, ExistingServer] = {}

app = FastAPI()
app.mount("/static", StaticFiles(directory="website"), name="static")

@app.get("/")
def read_root():
    return FileResponse("website/homepage.html")


@app.post("/create")
def create(request: CreateServerRequest):
    try:
        server_type = request.type
    except KeyError:
        raise HTTPException(status_code=422, detail="Invalid server type")
    
    Server(request.server, server_type, request.version, maxRam=request.maxRam)
    return {"status": "created"}

@app.post("/start")
def start(request: ServerNameRequest):
    try:
        online_servers.update({request.server: ExistingServer(request.server)})
    except KeyError:
        raise HTTPException(status_code=404, detail="Server not found")
    online_servers.get(request.server).start()
    return {"status": "started"}

@app.post("/stop")
def stop(request: ServerNameRequest):
    try:
        server = online_servers.get(request.server)
    except KeyError:
        raise HTTPException(status_code=404, detail="Server not found")
    server.stop()
    online_servers.pop(request.server)
    return {"status": "stopped"}

@app.post("/accept_eula")
def accept_eula(request: ServerNameRequest):
    try:
        ExistingServer(request.server).acceptEula()
    except KeyError:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"status": "accepted"}

@app.post("/is_created")
def is_created(request: ServerNameRequest):
    try:
        ExistingServer(request.server)
        return {"status": True}
    except FileNotFoundError:
        return {"status": False}

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8001)