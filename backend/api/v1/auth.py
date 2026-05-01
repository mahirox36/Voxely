import logging
import os
import secrets
from datetime import UTC, datetime, timedelta
from json import dumps, loads
from pathlib import Path
from typing import Any, Dict

import psutil
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request, status
from jose import JWTError, jwt
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

# Load environment variables
load_dotenv()

DATA_FILE = Path("servers/data.json")
router = APIRouter(prefix="/auth", tags=["auth"])

# Setup rate limiting
limiter = Limiter(key_func=get_remote_address)

logger = logging.getLogger(__name__)

# Security configuration - Load from environment variables
SECRET_KEY: str = os.getenv("SECRET_KEY", "None")
if (
    SECRET_KEY == "None"
):  # made it to "None" just  to avoid typing errors, but it will be generated if not set
    # Generate a new one only if not provided (for development)
    SECRET_KEY = secrets.token_urlsafe(32)
    logger.warning(
        "SECRET_KEY not found in environment. Using generated key. "
        "For production, set SECRET_KEY environment variable."
    )

ROOT_PASSWORD = os.getenv("ROOT_PASSWORD")
if not ROOT_PASSWORD:
    logger.error(
        "ROOT_PASSWORD not found in environment. Please set ROOT_PASSWORD environment variable."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


# Initialize root password if not exists
def initialize_root_password(password: str):
    """Generate and save root password if it doesn't exist"""
    if not ROOT_PASSWORD:
        # Generate random password
        new_password = password
        if not DATA_FILE.parent.exists():
            DATA_FILE.parent.mkdir(exist_ok=True)
        if DATA_FILE.exists():
            with open(DATA_FILE) as f:
                data: Dict[str, Any] = loads(f.read())
            data["SECRET_KEY"] = SECRET_KEY
            data["ROOT_PASSWORD"] = new_password
        else:
            data = {"SECRET_KEY": SECRET_KEY, "ROOT_PASSWORD": new_password}
        with open(DATA_FILE, "w") as f:
            f.write(dumps(data))

        logger.info("=" * 50)
        logger.info("ROOT PASSWORD GENERATED!")
        logger.info(f"Password: {new_password}")
        logger.info("Save this password - it's stored in .env file")
        logger.info("=" * 50)

        return new_password
    return ROOT_PASSWORD


# Get or generate root password
# ROOT_PASSWORD = initialize_root_password()


# Models
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    username: str = "root"


class UserRequest(BaseModel):
    username: str
    password: str


# JWT utilities
def create_access_token() -> str:
    """Create a JWT access token for root user"""
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": "root", "exp": expire, "iat": datetime.now(UTC)}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> str:
    """Decode JWT token and return username"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")  # type: ignore
        if username != "root":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user"
            )
        return username
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Authentication dependency
async def get_current_user(request: Request) -> UserResponse:
    """Get the current authenticated user from request"""
    # Get Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        auth_header = request.query_params.get("token")

    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Parse "Bearer {token}" format
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer {token}'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    username = decode_token(token)

    return UserResponse(username=username)


# Routes
@router.get("/first_time")
async def first():
    if not ROOT_PASSWORD:
        return True
    return False


@router.get("/system-info")
def get_system_info():
    total_ram = round(psutil.virtual_memory().total / (1024**2))  # MB
    return {"ram_mb": total_ram}


@router.post("/token", response_model=Token)
@limiter.limit("5/minute")
async def login(request: Request, form_data: UserRequest):
    """Login as root user and get access token

    Rate limited to 5 attempts per minute to prevent brute force attacks.
    """
    # Check credentials
    if form_data.username != "root":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username. Only 'root' user exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    global ROOT_PASSWORD
    if not ROOT_PASSWORD:
        ROOT_PASSWORD = initialize_root_password(form_data.password)

    if form_data.password != ROOT_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token()
    return Token(access_token=f"{access_token}")


@router.get("/me", response_model=UserResponse)
async def get_me(request: Request):
    """Get current user info"""
    current_user = await get_current_user(request)
    return current_user


@router.post("/verify")
async def verify_token(request: Request):
    """Verify token is valid"""
    current_user = await get_current_user(request)
    return {"valid": True, "username": current_user.username}


@router.post("/logout")
async def logout(request: Request):
    """Logout endpoint"""
    await get_current_user(request)
    return {"message": "Successfully logged out"}
