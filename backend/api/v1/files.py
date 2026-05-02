import asyncio
import os
import shutil
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from modules.ServerService import ServerService
from pydantic import BaseModel

from .auth import get_current_user

api = APIRouter(tags=["files"])
serverService = ServerService()


class FileListResponse(BaseModel):
    path: str
    name: str
    type: str
    size: int | None
    modified: str | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def validate_path(base_path: Path, requested_path: Path) -> Path:
    """
    Validate that *requested_path* resolves to a location inside *base_path*.

    Prevents path-traversal attacks (``../``, absolute paths, symlink escapes).

    Args:
        base_path: The allowed root directory (e.g. a server's data directory).
        requested_path: A relative or absolute path supplied by the caller.

    Returns:
        The validated, fully-resolved absolute path.

    Raises:
        HTTPException 400: If the resolved path escapes *base_path*.
    """
    try:
        base_absolute = base_path.resolve()
        resolved = (base_path / requested_path).resolve()
        resolved.relative_to(base_absolute)  # raises ValueError if outside
        return resolved
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Access denied: path is outside the allowed directory.",
        )


def _safe_zip_extract(zipf: zipfile.ZipFile, dest: Path) -> None:
    """
    Extract *zipf* to *dest* while guarding against zip-slip attacks.

    Each member path is validated against *dest* before extraction.

    Raises:
        HTTPException 400: If a zip entry would escape *dest*.
    """
    dest_resolved = dest.resolve()
    for member in zipf.namelist():
        member_path = (dest / member).resolve()
        try:
            member_path.relative_to(dest_resolved)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Zip entry '{member}' would escape the target directory.",
            )
        zipf.extract(member, dest)


# ---------------------------------------------------------------------------
# File endpoints
# ---------------------------------------------------------------------------


@api.get("/get/{path:path}")
async def get_file(request: Request, server_name: str, path: str):
    """Return the text content of a file inside the server directory."""
    await get_current_user(request)

    try:
        server = await serverService.get_server_instance(server_name)
        if not server:
            raise HTTPException(404, "Server not found")
        validated_path = validate_path(server.path, Path(path))

        if not validated_path.exists() or not validated_path.is_file():
            raise HTTPException(status_code=404, detail="File not found.")

        content = validated_path.read_text(encoding="utf-8")
        return {"path": str(validated_path.relative_to(server.path)), "data": content}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@api.post("/write/{path:path}")
async def write_file(request: Request, server_name: str, path: str):
    """Write (overwrite) text content to a file inside the server directory."""
    await get_current_user(request)
    body = await request.json()
    content: str = body.get("data", "")

    try:
        server = await serverService.get_server_instance(server_name)
        if not server:
            raise HTTPException(404, "Server not found")
        validated_path = validate_path(server.path, Path(path))

        # Create any intermediate directories that don't exist yet.
        validated_path.parent.mkdir(parents=True, exist_ok=True)
        validated_path.write_text(content, encoding="utf-8")

        return {"message": f"File '{path}' saved successfully."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@api.post("/upload/{path:path}")
async def upload_file(
    request: Request,
    server_name: str,
    path: str,
    file: UploadFile = File(...),
):
    """Upload a file into *path* inside the server directory."""
    await get_current_user(request)

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file name provided.")

    try:
        server = await serverService.get_server_instance(server_name)
        if not server:
            raise HTTPException(404, "Server not found")

        # An empty / root-like path means upload directly into the server root.
        base = Path(path.strip("/")) if path.strip("/") else Path(".")
        validated_dir = validate_path(server.path, base)
        validated_dir.mkdir(parents=True, exist_ok=True)

        dest = validate_path(server.path, base / file.filename)
        dest.write_bytes(await file.read())

        return {"message": f"File '{file.filename}' uploaded successfully."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@api.post("/create/{path:path}")
async def create_file(request: Request, server_name: str, path: str):
    """Create an empty file at *path* inside the server directory."""
    await get_current_user(request)

    try:
        server = await serverService.get_server_instance(server_name)
        if not server:
            raise HTTPException(404, "Server not found")
        validated_path = validate_path(server.path, Path(path))

        if validated_path.exists():
            if validated_path.is_file():
                raise HTTPException(
                    status_code=400, detail="A file already exists at this path."
                )
            raise HTTPException(
                status_code=400, detail="A directory already exists at this path."
            )

        validated_path.parent.mkdir(parents=True, exist_ok=True)
        validated_path.touch()

        return {"message": f"File '{validated_path.name}' created successfully."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@api.post("/create_folder/{path:path}")
async def create_folder(request: Request, server_name: str, path: str):
    """Create a new directory at *path* inside the server directory."""
    await get_current_user(request)

    try:
        server = await serverService.get_server_instance(server_name)
        if not server:
            raise HTTPException(404, "Server not found")
        validated_path = validate_path(server.path, Path(path))

        if validated_path.exists():
            if not validated_path.is_dir():
                raise HTTPException(
                    status_code=400, detail="A file already exists at this path."
                )
            raise HTTPException(status_code=400, detail="Folder already exists.")

        _PROTECTED_NAMES = {"mods", "plugins"}
        if validated_path.name in _PROTECTED_NAMES:
            raise HTTPException(
                status_code=400, detail=f"'{validated_path.name}' is a protected name."
            )

        validated_path.mkdir(parents=True, exist_ok=False)

        return {"message": f"Folder '{validated_path.name}' created successfully."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@api.delete("/delete/{path:path}")
async def delete_file(request: Request, server_name: str, path: str):
    """Delete a file or directory at *path* inside the server directory."""
    await get_current_user(request)

    _PROTECTED_NAMES = {"mods", "plugins"}

    try:
        server = await serverService.get_server_instance(server_name)
        if not server:
            raise HTTPException(404, "Server not found")
        validated_path = validate_path(server.path, Path(path))

        if not validated_path.exists():
            raise HTTPException(status_code=404, detail="Path not found.")

        if validated_path.name in _PROTECTED_NAMES:
            raise HTTPException(
                status_code=400, detail="Cannot delete a protected directory."
            )

        if validated_path.is_file():
            validated_path.unlink()
        elif validated_path.is_dir():
            shutil.rmtree(validated_path)
        else:
            raise HTTPException(
                status_code=400, detail="Unknown filesystem entry type."
            )

        return {"message": f"'{path}' deleted successfully."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Zip / unzip
# ---------------------------------------------------------------------------


async def _zip_files_async(
    zip_path: Path, server_path: Path, files_to_zip: list[str]
) -> None:
    """Asynchronously compress *files_to_zip* (relative to *server_path*) into *zip_path*."""

    def _sync_zip() -> None:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for rel in files_to_zip:
                abs_path = server_path / rel
                if not abs_path.exists():
                    continue
                if abs_path.is_file():
                    zf.write(abs_path, arcname=rel)
                elif abs_path.is_dir():
                    for root, _dirs, files in os.walk(abs_path):
                        for name in files:
                            full = Path(root) / name
                            zf.write(full, arcname=full.relative_to(server_path))

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(ThreadPoolExecutor(), _sync_zip)


@api.post("/zip")
async def zip_files(request: Request, server_name: str):
    """Compress a list of paths into a zip archive inside the server directory."""
    await get_current_user(request)
    body = await request.json()
    files_to_zip: List[str] = body.get("paths", [])
    zip_name: str = body.get("name", "archive.zip")

    try:
        server = await serverService.get_server_instance(server_name)
        if not server:
            raise HTTPException(404, "Server not found")

        # Validate every path that will be zipped.
        for rel in files_to_zip:
            validate_path(server.path, Path(rel))

        zip_path = validate_path(server.path, Path(zip_name))
        if zip_path.suffix != ".zip":
            zip_path = zip_path.with_suffix(".zip")

        await _zip_files_async(zip_path, server.path, files_to_zip)

        return {"message": f"Files zipped successfully into '{zip_path.name}'."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@api.post("/unzip")
async def unzip_file(request: Request, server_name: str):
    """Extract a zip archive inside the server directory (zip-slip safe)."""
    await get_current_user(request)
    body = await request.json()
    zip_file_path: str = body.get("path", "")

    try:
        server = await serverService.get_server_instance(server_name)
        if not server:
            raise HTTPException(404, "Server not found")
        validated_zip = validate_path(server.path, Path(zip_file_path))

        if not validated_zip.exists() or not validated_zip.is_file():
            raise HTTPException(status_code=404, detail="Zip file not found.")

        with zipfile.ZipFile(validated_zip, "r") as zf:
            _safe_zip_extract(zf, server.path)

        return {"message": f"'{zip_file_path}' extracted successfully."}
    except HTTPException:
        raise
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=400, detail="The provided file is not a valid zip archive."
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Copy / move / download
# ---------------------------------------------------------------------------


@api.post("/copy")
async def copy_file(request: Request, server_name: str):
    """Copy a file from one location to another inside the server directory."""
    await get_current_user(request)
    body = await request.json()
    source_path: str = body.get("source", "")
    dest_path: str = body.get("destination", "")

    try:
        server = await serverService.get_server_instance(server_name)
        if not server:
            raise HTTPException(404, "Server not found")
        src = validate_path(server.path, Path(source_path))
        dst = validate_path(server.path, Path(dest_path))

        if not src.exists() or not src.is_file():
            raise HTTPException(status_code=404, detail="Source file not found.")

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

        return {
            "message": f"File copied from '{source_path}' to '{dest_path}' successfully."
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@api.post("/move")
async def move_file(request: Request, server_name: str):
    """Move (rename) a file inside the server directory."""
    await get_current_user(request)
    body = await request.json()
    source_path: str = body.get("source", "")
    dest_path: str = body.get("destination", "")

    try:
        server = await serverService.get_server_instance(server_name)
        if not server:
            raise HTTPException(404, "Server not found")
        src = validate_path(server.path, Path(source_path))
        dst = validate_path(server.path, Path(dest_path))

        if not src.exists() or not src.is_file():
            raise HTTPException(status_code=404, detail="Source file not found.")

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), dst)

        return {
            "message": f"File moved from '{source_path}' to '{dest_path}' successfully."
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@api.get("/download/{path:path}")
async def download_file(request: Request, server_name: str, path: str):
    """Stream a file from the server directory to the client."""
    await get_current_user(request)

    try:
        server = await serverService.get_server_instance(server_name)
        if not server:
            raise HTTPException(404, "Server not found")
        validated_path = validate_path(server.path, Path(path))

        if not validated_path.exists() or not validated_path.is_file():
            raise HTTPException(status_code=404, detail="File not found.")

        return FileResponse(
            path=validated_path,
            filename=validated_path.name,
            media_type="application/octet-stream",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
