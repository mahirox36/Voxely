import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from typing import List
from pydantic import BaseModel
from datetime import datetime
from ..auth import get_current_user
from .utils import get_server_instance
import zipfile
from fastapi.responses import FileResponse

router = APIRouter(tags=["files"])


class FileListResponse(BaseModel):
    path: str
    name: str
    type: str
    size: int | None
    modified: str | None


# @router.get("/{server_name}/files", response_model=List[FileListResponse])
# async def list_files(request: Request, server_name: str, path: str = ""):
#     """List files in the server directory"""
#     current_user = await get_current_user(request)

#     try:
#         server = await get_server_instance(server_name)
#         base_path = server.path / path if path else server.path

#         if not base_path.exists():
#             raise HTTPException(status_code=404, detail="Path not found")

#         files = []
#         for entry in base_path.iterdir():
#             try:
#                 stat = entry.stat()
#                 files.append(FileListResponse(
#                     path=str(entry.relative_to(server.path)),
#                     name=entry.name,
#                     type="directory" if entry.is_dir() else "file",
#                     size=stat.st_size if not entry.is_dir() else None,
#                     modified=datetime.fromtimestamp(stat.st_mtime).isoformat()
#                ))
#             except Exception as e:
#                 print(f"Error processing {entry}: {e}")
#                 continue

#         return sorted(files, key=lambda x: (x.type == "file", x.name.lower()))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# elif msg_type == "write":
#     file_path = data.get("path", "")
#     content = data.get("data", "")
#     full_path = server.path / file_path
#     try:
#         with open(full_path, "w", encoding="utf-8") as f:
#             f.write(content)
#         await websocket.send_json(
#             {
#                 "type": "info",
#                 "data": f"File '{file_path}' saved successfully.",
#             }
#         )
#     except Exception as e:
#         await websocket.send_json(
#             {
#                 "type": "error",
#                 "data": f"Failed to save file '{file_path}': {e}",
#             }
#         )
# elif msg_type == "read":
#     file_path = data.get("path", "")
#     full_path = server.path / file_path
#     try:
#         with open(full_path, "r", encoding="utf-8") as f:
#             content = f.read()
#         await websocket.send_json(
#             {
#                 "type": "file_content",
#                 "path": file_path,
#                 "data": content,
#             }
#         )
#     except Exception as e:
#         await websocket.send_json(
#             {
#                 "type": "error",
#                 "data": f"Failed to read file '{file_path}': {e}",
#             }
#         )


@router.get("/{server_name}/files/get/{path:path}")
async def get_file(request: Request, server_name: str, path: str):
    """Get a specific file from the server directory"""
    current_user = await get_current_user(request)

    try:
        server = await get_server_instance(server_name)
        file_path = server.path / path

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {"path": str(file_path.relative_to(server.path)), "data": content}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{server_name}/files/write/{path:path}")
async def write_file(request: Request, server_name: str, path: str):
    """Write data to a specific file in the server directory"""
    current_user = await get_current_user(request)
    body = await request.json()
    content = body.get("data", "")

    try:
        server = await get_server_instance(server_name)
        file_path = server.path / path

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {"message": f"File '{path}' saved successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def zip_files_async(zip_path: Path, server_path: Path, files_to_zip: list[str]):
    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor()

    def sync_zip():
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_rel_path in files_to_zip:
                file_path = server_path / file_rel_path
                if file_path.exists():
                    if file_path.is_file():
                        zipf.write(file_path, arcname=file_rel_path)
                    elif file_path.is_dir():
                        for root, dirs, files in os.walk(file_path):
                            root_path = Path(root)
                            for file in files:
                                abs_file_path = root_path / file
                                zipf.write(
                                    abs_file_path,
                                    arcname=abs_file_path.relative_to(server_path),
                                )

    await loop.run_in_executor(executor, sync_zip)


@router.post("/{server_name}/files/upload/{path:path}")
async def upload_file(
    request: Request, server_name: str, path: str, file: UploadFile = File(...)
):
    """Upload a file to the server directory"""
    current_user = await get_current_user(request)
    try:
        server = await get_server_instance(server_name)
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file uploaded")
        if not path or path in ["/", ".", "./", "", "current_directory_super_long_because_empty_string_is_bad_and_also_if_there_were_someone_stupid_enough_to_name_a_folder_like_this_we_need_to_handle_it_properly"]:
            dest_path = server.path / file.filename
        else:
            dest_path = server.path / path / file.filename

        with open(dest_path, "wb") as f:
            content = await file.read()
            f.write(content)

        return {"message": f"File '{file.filename}' uploaded successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{server_name}/files/delete/{path:path}")
async def delete_file(request: Request, server_name: str, path: str):
    """Delete a specific file from the server directory"""
    current_user = await get_current_user(request)

    try:
        server = await get_server_instance(server_name)
        file_path = server.path / path

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        file_path.unlink()

        return {"message": f"File '{path}' deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{server_name}/files/zip")
async def zip_files(request: Request, server_name: str):
    """Zip multiple files in the server directory"""
    current_user = await get_current_user(request)
    body = await request.json()
    files_to_zip: List[str] = body.get("paths", [])
    zip_name: str = body.get("name", "archive.zip")

    try:
        server = await get_server_instance(server_name)
        zip_path = server.path / zip_name
        
        if zip_path.suffix != ".zip":
            zip_path = zip_path.with_suffix(".zip")

        await zip_files_async(zip_path, server.path, files_to_zip)

        return {"message": f"Files zipped successfully into '{zip_name}'."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{server_name}/files/unzip")
async def unzip_file(request: Request, server_name: str):
    """Unzip a file in the server directory"""
    current_user = await get_current_user(request)
    body = await request.json()
    zip_file_path: str = body.get("path", "")

    try:
        server = await get_server_instance(server_name)
        full_zip_path = server.path / zip_file_path

        if not full_zip_path.exists() or not full_zip_path.is_file():
            raise HTTPException(status_code=404, detail="Zip file not found")

        with zipfile.ZipFile(full_zip_path, "r") as zipf:
            zipf.extractall(server.path)

        return {"message": f"File '{zip_file_path}' unzipped successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{server_name}/files/copy")
async def copy_file(request: Request, server_name: str):
    """Copy a file in the server directory"""
    current_user = await get_current_user(request)
    body = await request.json()
    source_path: str = body.get("source", "")
    dest_path: str = body.get("destination", "")

    try:
        server = await get_server_instance(server_name)
        full_source_path = server.path / source_path
        full_dest_path = server.path / dest_path

        if not full_source_path.exists() or not full_source_path.is_file():
            raise HTTPException(status_code=404, detail="Source file not found")

        with open(full_source_path, "rb") as src_file:
            content = src_file.read()

        with open(full_dest_path, "wb") as dest_file:
            dest_file.write(content)

        return {
            "message": f"File copied from '{source_path}' to '{dest_path}' successfully."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{server_name}/files/move")
async def move_file(request: Request, server_name: str):
    """Move a file in the server directory"""
    current_user = await get_current_user(request)
    body = await request.json()
    source_path: str = body.get("source", "")
    dest_path: str = body.get("destination", "")

    try:
        server = await get_server_instance(server_name)
        full_source_path = server.path / source_path
        full_dest_path = server.path / dest_path

        if not full_source_path.exists() or not full_source_path.is_file():
            raise HTTPException(status_code=404, detail="Source file not found")

        full_source_path.rename(full_dest_path)

        return {
            "message": f"File moved from '{source_path}' to '{dest_path}' successfully."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{server_name}/files/download/{path:path}")
async def download_file(request: Request, server_name: str, path: str):
    """Download a specific file from the server directory"""
    current_user = await get_current_user(request)

    try:
        server = await get_server_instance(server_name)
        file_path = server.path / path

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(
                status_code=404, detail=f"File not found: {str(file_path)}"
            )

        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type="application/octet-stream",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
