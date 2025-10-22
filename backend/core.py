from __future__ import annotations
import asyncio

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
from api.v1 import router as api_v1_router



# Create the FastAPI app at module level
app = FastAPI(
    title="MineGimme API",
    description="API for MineGimme (Local Minecraft Server Management and Hosting)",
    version="1.0.0",
    # Disable automatic redirects for routes with/without trailing slashes
    redirect_slashes=False,
    docs_url=None,  # Disable default docs URL
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_v1_router)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add middleware to debug auth headers

@app.get("/docs", include_in_schema=False)
async def custom_docs():
    return FileResponse("static/stoplight/index.html")

class APIConfig:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 25401,
        allowed_origins: Optional[list[str]] = None
    ) -> None:
        self.host = host
        self.port = port
        self.allowed_origins = allowed_origins or [
            "https://nub.mahirou.online",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
        ]

class APIServer:
    """Manages FastAPI server and route handlers"""

    def __init__(
        self,
        config: APIConfig,
    ) -> None:
        self.logger = logging.getLogger("bot")
        self.config = config
        self.start_time = datetime.now()
        self.app = app
        self.app.state.backend = self

    async def start(self) -> None:
        """Start the FastAPI server"""
        config = uvicorn.Config(
            app=self.app,
            host=self.config.host,
            port=self.config.port
        )
        server = uvicorn.Server(config)
        try:
            self.logger.info(f"Starting API server on {self.config.host}:{self.config.port}")
            await server.serve()
        except Exception as e:
            self.logger.error(f"Failed to start API server: {str(e)}")
            raise
    
if __name__ == "__main__":
    config = APIConfig()
    server = APIServer(config)
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")