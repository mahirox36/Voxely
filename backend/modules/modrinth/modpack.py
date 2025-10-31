"""
Modrinth .mrpack Files Module.

This module provides a high-level interface to interact with the Modrinth Modpack.
Provides functionality for parsing .mrpack files, downloading contained mods, and extracting overrides.

Example:
    >>> async with Client() as client:
    ...     tags = await client.get_category_tags()
    ...     for tag in tags:
    ...         print(f"{tag.name} - {tag.project_type}")
"""

import re
import aiohttp
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Union
import zipfile

from modules.modrinth.http import HTTPClient
from modules.modrinth.utils import SideType, validate_input


class FileNotModpack(Exception):
    def __init__(self, file) -> None:
        super().__init__(f"{file} not a Modpack (.mrpack)")


class FileCorrupted(Exception):
    def __init__(self, file) -> None:
        super().__init__(f"{file} is corrupted file")


class File:
    def __init__(
        self, data: Dict[str, Union[str, int, List[str], Dict[str, str]]]
    ) -> None:
        self._data = dict(data)
        self.full_path: Path = Path(
            validate_input(self._data.get("path"), "path", required=True)
        )
        self.folder: Path = self.full_path.parent
        self.name: str = self.full_path.name
        self.hashes: Dict[str, str] = validate_input(
            self._data.get("hashes"), "hashes", required=True
        )
        self.sha512: str = self.hashes.get("sha512", "")
        self.sha1: str = self.hashes.get("sha1", "")
        self.env: Optional[Dict[str, str]] = validate_input(
            self._data.get("env"), "env", required=False
        )
        self.client: Optional[SideType] = None
        self.server: Optional[SideType] = None

        if self.env:
            self.client = SideType(
                validate_input(self.env.get("client"), "client", required=False)
            )
            self.server = SideType(
                validate_input(self.env.get("server"), "server", required=False)
            )

        self.downloads: List[str] = validate_input(
            self._data.get("downloads"), "downloads", required=True
        )
        self.fileSize: int = validate_input(
            self._data.get("fileSize"), "fileSize", required=True
        )

    def to_dict(self) -> Dict[str, Union[str, int, List[str], Dict[str, str]]]:
        return self._data

    async def _download(
        self,
        parent_path: Path,
        session: aiohttp.ClientSession,
        skip_raised: bool = True,
    ):
        downloaded = []
        for path in self.downloads:
            async with session.get(path) as resp:
                if not skip_raised:
                    resp.raise_for_status()
                # (parent_path / self.full_path).parent.mkdir(parents=True, exist_ok=True)
                temp_path = parent_path / self.full_path
                temp_path.parent.mkdir(parents=True, exist_ok=True)
                temp_file = temp_path.with_suffix(temp_path.suffix + ".part")
                with open(temp_file, "wb") as f:
                    async for chunk in resp.content.iter_chunked(8192):
                        f.write(chunk)
                temp_file.rename(parent_path / self.full_path)
                downloaded.append(path)
        # https://cdn.modrinth.com/data/Q1DELmr6/versions/cXRUkPZQ/AL%27s%20Skeletons%20Revamped%2BFA%201.5.zip
        match = re.match(r"https://cdn\.modrinth\.com/data/([^/]+)/versions/([^/]+)/", self.downloads[0])
        project : Optional[str] = None
        version : Optional[str] = None
        if match:
            project, version = match.groups()
        return project, version

    async def download(
        self,
        parent_path: Path,
        session: aiohttp.ClientSession,
        skip_raised: bool = True,
        sem: Optional[asyncio.Semaphore] = None,
    ) -> tuple[str | None, str | None]:
        if sem:
            async with sem:
                return await self._download(parent_path, session, skip_raised)
        return await self._download(parent_path, session, skip_raised)


class Modpack:
    def __init__(
        self, file: Union[Path, str], session: Optional[aiohttp.ClientSession] = None
    ) -> None:
        """
        Class manages a modpack.

        Args:
            file (Union[Path, str]): the file path for a modpack

        Raises:
            FileNotFoundError: File not found
            FileNotModpack: is not a modpack (.mrpack)
        """
        self.session = session
        file = Path(file)
        if not file.exists():
            raise FileNotFoundError(str(file))
        if file.suffix != ".mrpack":
            raise FileNotModpack(file)
        self.path = file
        with zipfile.ZipFile(self.path) as fzip:
            try:
                index = fzip.open("modrinth.index.json")
            except:
                raise FileNotModpack(file)
            try:
                self._data: dict = json.loads(index.read())
            except:
                raise FileCorrupted(file)

        self.game: str = validate_input(self._data.get("game"), "game", required=False)
        self.formatVersion: int = validate_input(
            self._data.get("formatVersion"), "formatVersion", required=False
        )
        self.versionId: str = validate_input(
            self._data.get("versionId"), "versionId", required=False
        )
        self.name: str = validate_input(self._data.get("name"), "name", required=False)
        self.summary: Optional[str] = validate_input(
            self._data.get("summary"), "summary", required=False
        )
        self.files: List[File] = [
            File(file)
            for file in validate_input(self._data.get("files"), "files", required=True)
        ]
        self.dependencies: Dict[str, str] = validate_input(
            self._data.get("dependencies"), "dependencies", required=True
        )
        self.minecraft_version: str = validate_input(
            self.dependencies.get("minecraft"), "minecraft", required=True
        )

    async def __aenter__(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *exc):
        if self.session:
            await self.session.close()
            self.session = None

    async def download_mods(self, path: Union[Path, str], limit=5) -> List[tuple[str | None, str | None]]:
        sem = asyncio.Semaphore(limit)
        path = Path(path)
        close_after = False
        if not self.session:
            self.session = aiohttp.ClientSession()
            close_after = True
        tasks = [file.download(path, self.session, True, sem) for file in self.files]
        results = await asyncio.gather(*tasks)
        if close_after:
            await self.session.close()
            self.session = None
        return results

    def copy_override(
        self,
        path: Union[Path, str],
        override_client: bool = True,
        override_server: bool = True,
    ):
        path = Path(path)
        extracted = []

        with zipfile.ZipFile(self.path) as fzip:
            # Folders to look for inside the .mrpack
            override_folders = ["overrides/"]
            if override_client:
                override_folders.append("client-overrides/")
            if override_server:
                override_folders.append("server-overrides/")

            for member in fzip.namelist():
                for folder in override_folders:
                    if member.startswith(folder) and not member.endswith("/"):
                        # Create destination path WITHOUT the "overrides/" prefix
                        relative_path = Path(member).relative_to(folder)
                        dest_path = path / relative_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        with fzip.open(member) as source, open(
                            dest_path, "wb"
                        ) as target:
                            target.write(source.read())
                        extracted.append(dest_path)

        return extracted

    async def download_all(self, path: Union[Path, str]) -> List[tuple[str | None, str | None]]:
        downloads = await self.download_mods(path)
        self.copy_override(path)
        return downloads
