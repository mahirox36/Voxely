from fastapi import APIRouter, HTTPException, Request
from ..auth import get_current_user
from .utils import get_server_instance

router = APIRouter(tags=["settings"])

@router.post("/{server_name}/eula/accept")
async def accept_eula(request: Request, server_name: str):
    """Accept the Minecraft EULA for a server"""
    current_user = await get_current_user(request)
    
    try:
        server = await get_server_instance(server_name)
        server.accept_eula()
        return {"message": "EULA accepted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{server_name}/eula/status")
async def check_eula_status(request: Request, server_name: str):
    """Check if EULA has been accepted for a server"""
    current_user = await get_current_user(request)
    
    try:
        server = await get_server_instance(server_name)
        eula_path = server.path / "eula.txt"
        
        if not eula_path.exists():
            return {"accepted": False}
        
        with open(eula_path, "r") as f:
            content = f.read()
            return {"accepted": "eula=true" in content.lower()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))