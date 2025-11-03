from __future__ import annotations
import asyncio

from datetime import datetime
from logging.handlers import RotatingFileHandler
import sys
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme
import logging


custom_theme = Theme(
    {
        "logging.level.debug": "bold italic #9b59b6",
        "logging.level.info": "bold #00c3ff",
        "logging.level.warning": "bold italic #ffae00",
        "logging.level.error": "bold #ff5c8a",
        "logging.level.critical": "bold blink reverse #ff0080 on #fff0f5",
    }
)
console = Console(force_terminal=True, theme=custom_theme)
rich_handler = RichHandler(
    level=logging.INFO,
    console=console,
    markup=True,
    rich_tracebacks=True,
    show_time=False,
    show_path=False,
)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.handlers.clear()

# Add handlers to root logger
root_logger.addHandler(rich_handler)

for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "auth"):
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.propagate = False  # Prevent double logs
    logger.setLevel(logging.DEBUG if "access" not in name else logging.INFO)
    logger.addHandler(rich_handler)


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical(
        "Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback)
    )
    console.print_exception(show_locals=True)


sys.excepthook = handle_exception

logger = logging.getLogger(__name__)

# Create the FastAPI app at module level
from api.v1 import router as api_v1_router

app = FastAPI(
    title="Voxely API",
    description="API for Voxely (Local Minecraft Server Management and Hosting)",
    version="1.0.0",
    # Disable automatic redirects for routes with/without trailing slashes
    redirect_slashes=False,
    # docs_url=None,  # Disable default docs URL
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


class APIConfig:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 25401,
        allowed_origins: Optional[list[str]] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.allowed_origins = allowed_origins or [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://backend:3000",
        ]


class APIServer:
    """Manages FastAPI server and route handlers"""

    def __init__(
        self,
        config: APIConfig,
    ) -> None:
        self.logger = logging.getLogger("api")
        self.config = config
        self.start_time = datetime.now()
        self.app = app
        self.app.state.backend = self

    async def start(self) -> None:
        """Start the FastAPI server"""
        config = uvicorn.Config(
            app=self.app, host=self.config.host, port=self.config.port
        )
        server = uvicorn.Server(config)
        try:
            self.logger.info(
                f"Starting API server on {self.config.host}:{self.config.port}"
            )
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
