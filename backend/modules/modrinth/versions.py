"""
Modrinth Version Module.

This module provides high-level classes and functions for interacting with Modrinth version data.
It includes version management, file handling, and dependency tracking.

Example:
    >>> async with Client() as client:
    ...     project = await client.get_project("fabric-api")
    ...     version = await project.get_version("1.0.0")
    ...     print(f"Version: {version.name} ({version.version_number})")
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import logging
from .http import HTTPClient
from .utils import (
    MISSING,
    DependencyType,
    VersionStatus,
    VersionType,
    validate_input,
    ValidationError,
    NotFoundError,
    format_datetime,
)
all = [
    "File",
    "Dependency",
    "Version",
    "Versions",
]

logger = logging.getLogger("modrinth.versions")


class File:
    """
    Represents a project file.

    Attributes:
        hashes (Dict[str, str]): File hashes (sha1, sha512)
        url (str): Download URL
        filename (str): Name of the file
        primary (bool): Whether this is the primary file
        size (int): File size in bytes
        file_type (Optional[str]): Type of the file
    """

    def __init__(self, data: Dict[str, Any]):
        self.hashes: Dict[str, str] = validate_input(
            data.get("hashes", {}), "hashes", required=True
        )
        self.url: str = validate_input(data.get("url"), "url", required=True)
        self.filename: str = validate_input(
            data.get("filename"), "filename", required=True
        )
        self.primary: bool = validate_input(
            data.get("primary"), "primary", required=True
        )
        self.size: int = validate_input(data.get("size"), "size", required=True)
        self.file_type: Optional[str] = validate_input(
            data.get("file_type"), "file_type", required=False
        )

    async def download(self, path: str | Path, chunk_size: int = 8192) -> str:
        """
        Download the file to the specified path.

        Args:
            path (str): Directory to save the file in
            chunk_size (int): Size of chunks to download

        Returns:
            str: Path to the downloaded file
        """
        import os
        import aiohttp

        logger.info(f"Downloading file {self.filename} to {path}")

        os.makedirs(path, exist_ok=True)
        filepath = os.path.join(path, self.filename)

        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                response.raise_for_status()

                with open(filepath, "wb") as f:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        f.write(chunk)

        logger.debug(f"File downloaded successfully to {filepath}")
        return filepath

    def __repr__(self) -> str:
        return f"<File filename='{self.filename}' size={self.size}>"


class Dependency:
    """
    Represents a version dependency.

    Attributes:
        version_id (str): ID of the required version
        project_id (str): ID of the required project
        file_name (Optional[str]): Name of the required file
        dependency_type (DependencyType): Type of dependency (required, optional, etc.)
    """

    def __init__(self, data: Dict[str, Any]):
        self.version_id: str = validate_input(
            data.get("version_id"), "version_id", required=False
        )
        self.project_id: str = validate_input(
            data.get("project_id"), "project_id", required=False
        )
        self.file_name: Optional[str] = validate_input(
            data.get("file_name"), "file_name", required=False
        )
        self.dependency_type: DependencyType = DependencyType(
            validate_input(
                data.get("dependency_type"), "dependency_type", required=True
            )
        )

    def __repr__(self) -> str:
        return f"<Dependency project='{self.project_id}' version='{self.version_id}'>"


class Version:
    """
    Represents a project version.

    Attributes:
        id (str): Version identifier
        name (str): Display name
        version_number (str): Version number (semantic versioning)
        changelog (Optional[str]): Changes in this version
        dependencies (List[Dependency]): Required dependencies
        game_versions (List[str]): Supported Minecraft versions
        version_type (VersionType): Release channel type
        loaders (List[str]): Supported mod loaders
        featured (bool): Whether this is featured
        status (VersionStatus): Version status
        project_id (str): Associated project ID
        author_id (str): Version author ID
        date_published (datetime): Publication date
        downloads (int): Download count
        files (List[File]): Downloadable files
    """

    def __init__(self, data: Dict[str, Any]):
        self.id: str = validate_input(data.get("id"), "id", required=True)
        self.name: str = validate_input(data.get("name"), "name", required=True)
        self.version_number: str = validate_input(
            data.get("version_number"), "version_number", required=True
        )
        self.changelog: Optional[str] = validate_input(
            data.get("changelog"), "changelog", required=False
        )
        self.dependencies: List[Dependency] = [
            Dependency(dep) for dep in data.get("dependencies", [])
        ]
        self.game_versions: List[str] = validate_input(
            data.get("game_versions", []), "game_versions", required=True
        )
        self.version_type: VersionType = VersionType(
            validate_input(data.get("version_type"), "version_type", required=True)
        )
        self.loaders: List[str] = validate_input(
            data.get("loaders", []), "loaders", required=True
        )
        self.featured: bool = validate_input(
            data.get("featured"), "featured", required=True
        )
        self.status: VersionStatus = VersionStatus(
            validate_input(data.get("status"), "status", required=True)
        )
        self.requested_status: Optional[str] = validate_input(
            data.get("requested_status"), "requested_status", required=False
        )
        self.project_id: str = validate_input(
            data.get("project_id"), "project_id", required=True
        )
        self.author_id: str = validate_input(
            data.get("author_id"), "author_id", required=True
        )
        self.date_published: datetime = datetime.fromisoformat(
            validate_input(data.get("date_published"), "date_published", required=True)
        )
        self.downloads: int = validate_input(
            data.get("downloads"), "downloads", required=True
        )
        self.changelog_url: Optional[str] = validate_input(
            data.get("changelog_url"), "changelog_url", required=False
        )
        self.files: List[File] = [
            File(file_data) for file_data in data.get("files", [])
        ]

    def __repr__(self) -> str:
        return f"<Version id='{self.id}' name='{self.name}' version='{self.version_number}'>"

    def get_primary_file(self) -> Optional[File]:
        """Get the primary file for this version."""
        return next((file for file in self.files if file.primary), None)

    async def download_primary(self, path: str | Path) -> Optional[str]:
        """
        Download the primary file for this version.

        Args:
            path (str): Directory to save the file in

        Returns:
            Optional[str]: Path to the downloaded file, or None if no primary file
        """
        primary = self.get_primary_file()
        if primary:
            return await primary.download(path)
        return None


class Versions:
    """
    Manages version-related operations for the Modrinth API.

    This class provides methods to fetch and manage versions of a project.

    Example:
        >>> async with Client() as client:
        ...     project = await client.get_project("fabric-api")
        ...     versions = await project.get_versions()
        ...     print(f"Found {len(versions)} versions")
    """

    def __init__(self, http_client: HTTPClient):
        """
        Initialize the Versions manager.

        Args:
            http_client (HTTPClient): The HTTP client to use for API requests
        """
        self.http_session = http_client
    
    async def get_versions(self, version_ids: List[str]) -> List[Version]:
        """
        Fetch all versions for a given project.

        Args:
            project_id (str): ID of the project

        Returns:
            List[Version]: List of versions for the project

        Raises:
            NotFoundError: If the project is not found
            ValidationError: If the API returns invalid data
        """
        logger.info(f"Fetching versions: {version_ids}")
        try:
            versions_data = await self.http_session._get_versions(version_ids)
            return [Version(data) for data in versions_data]
        except Exception as e:
            logger.error(f"Failed to fetch versions: {str(e)}", exc_info=True)
            raise NotFoundError(f"Failed to fetch versions: {str(e)}")
    
    async def get_version(self, version_id: str) -> Version:
        """
        Fetch a specific version for a given project.

        Args:
            version_id (str): ID of the version

        Returns:
            Version: The requested version

        Raises:
            NotFoundError: If the project or version is not found
            ValidationError: If the API returns invalid data
        """
        logger.info(f"Fetching version: {version_id}")
        try:
            version_data = await self.http_session._get_version(version_id)
            return Version(version_data)
        except Exception as e:
            logger.error(f"Failed to fetch version: {str(e)}", exc_info=True)
            raise NotFoundError(f"Failed to fetch version: {str(e)}")