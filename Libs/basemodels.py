from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pydantic import BaseModel, Field

class CreateServerRequest(BaseModel):
    name: str
    type: str = Field(default="vanilla", pattern="^(vanilla|paper|fabric|custom)$")
    version: str = "1.21.1"
    port: int = Field(default=25565, ge=1, le=65535)
    minRam: int = Field(default=1, gt=0)
    maxRam: int = Field(default=2, gt=0)
    maxPlayers: int = Field(default=20, ge=1)
class ServerNameRequest(BaseModel):
    server: str
class AccountsInfo(BaseModel):
    username: str
    password: str