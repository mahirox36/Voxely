from pydantic import BaseModel
from pydantic import BaseModel, Field

class CreateServerRequest(BaseModel):
    server: str
    type: str = Field(default="vanilla", pattern="^(vanilla|paper|spigot)$")
    version: str = "1.21.1"
    maxRam: int = Field(default=1024, gt=0)
class ServerNameRequest(BaseModel):
    server: str
