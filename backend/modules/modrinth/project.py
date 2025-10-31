"""
Modrinth Project Module.

This module provides high-level classes and functions for interacting with Modrinth projects.
It includes project searching, version management, and file downloads.

Example:
    >>> async with Client() as client:
    ...     # Search for a project
    ...     results = await client.search_projects("JEI", limit=1)
    ...     if results.hits:
    ...         project = results.hits[0]
    ...         print(f"Found {project.title} by {project.team}")
"""

from typing import List, Dict, Any, Optional, Union

from datetime import datetime
import aiohttp
import os
import logging
from .http import HTTPClient
from .versions import *
from .utils import (
    MISSING,
    Facet,
    MonetizationStatus,
    NotFoundError,
    ProjectStatus,
    ProjectType,
    RequestedStatus,
    SideType,
    format_datetime,
    validate_input,
    ValidationError,
)
from rich import print
from dataclasses import asdict, dataclass

logger = logging.getLogger("modrinth.project")

all = ["Project", "Projects", "SearchResult", "GalleryItem", "License"]


class License:
    """
    Represents a project license.

    Attributes:
        id (str): License identifier
        name (str): Display name
        url (Optional[str]): URL to license text
    """

    def __init__(self, data: Dict[str, Any]):
        self._data = dict(data)
        self.id: str = validate_input(data.get("id"), "id", required=True)
        self.name: str = validate_input(data.get("name"), "name", required=True)
        self.url: Optional[str] = validate_input(data.get("url"), "url", required=False)

    def __repr__(self) -> str:
        return f"<License id='{self.id}' name='{self.name}'>"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert license data to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the license
        """
        return self._data


class GalleryItem:
    """
    Represents a project gallery item.

    Attributes:
        url (str): Image URL
        featured (bool): Whether this is a featured image
        title (Optional[str]): Image title
        description (Optional[str]): Image description
        created (datetime): When the image was added
        ordering (int): Display order
    """

    def __init__(self, data: Dict[str, Any]):
        self._data = dict(data)
        self.url: str = validate_input(data.get("url"), "url", required=True)
        self.featured: bool = validate_input(
            data.get("featured"), "featured", required=True
        )
        self.ordering: int = validate_input(
            data.get("ordering"), "ordering", required=True
        )
        self.created: datetime = datetime.fromisoformat(
            validate_input(data.get("created"), "created", required=True)
        )
        self.title: Optional[str] = validate_input(
            data.get("title"), "title", required=False
        )
        self.description: Optional[str] = validate_input(
            data.get("description"), "description", required=False
        )

    def __repr__(self) -> str:
        return f"<GalleryItem url='{self.url}' featured={self.featured}>"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert gallery item data to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the gallery item
        """
        return self._data

class ProjectHit:
    """
    Represents a single hit in a project search result.
    
    """
    def __init__(self, data: Dict[str, Any]):
        self.slug: str = validate_input(data.get("slug"), "slug", required=True)
        self.title: str = validate_input(data.get("title"), "title", required=True)
        self.description: str = validate_input(data.get("description"), "description", required=True)
        self.categories: List[str] = validate_input(data.get("categories"), "categories", required=True)
        self.client_side: Optional[SideType] = SideType(validate_input(data.get("client_side"), "client_side", required=True))
        self.server_side: Optional[SideType] = SideType (validate_input(data.get("server_side"), "server_side", required=True))
        self.project_type: str = validate_input(data.get("project_type"), "project_type", required=True)
        self.downloads: int = validate_input(data.get("downloads"), "downloads", required=True)
        self.icon_url: Optional[str] = validate_input(data.get("icon_url"), "icon_url", required=False)
        self.color: Optional[int] = validate_input(data.get("color"), "color", required=False)
        self.thread_id: Optional[str] = validate_input(data.get("thread_id"), "thread_id", required=False)
        self.monetization_status: Optional[str] = validate_input(data.get("monetization_status"), "monetization_status", required=False)
        self.author: str = validate_input(data.get("author"), "author", required=True)
        self.display_categories: List[str] = validate_input(data.get("display_categories"), "display_categories", required=True)
        self.versions: List[str] = validate_input(data.get("versions"), "versions", required=True)
        self.follows: int = validate_input(data.get("follows"), "follows", required=True)
        self.date_created: datetime = datetime.fromisoformat(validate_input(data.get("date_created"), "date_created", required=True))
        self.date_modified: datetime = datetime.fromisoformat(validate_input(data.get("date_modified"), "date_modified", required=True))
        self.latest_version: Optional[str] = validate_input(data.get("latest_version"), "latest_version", required=False)
        self.license: str = validate_input(data.get("license"), "license", required=True)
        self.gallery: List[str] = validate_input(data.get("gallery"), "gallery", required=True)
        self.featured_gallery: Optional[str] = validate_input(data.get("featured_gallery"), "featured_gallery", required=False)


class Project:
    """
    Represents a Modrinth project.

    Attributes:
        id (str): Project identifier
        slug (str): URL-friendly name
        title (str): Display name
        description (str): Short description
        downloads (int): Total download count
        followers (int): Number of followers
        license (License): Project license
        versions (List[str]): List of version IDs

    Example:
        >>> project = await client.get_project("fabric-api")
        >>> print(f"{project.title} - {project.description}")
        >>> latest = await project.get_latest_version()
        >>> print(f"Latest version: {latest.version_number}")
    """

    def __init__(self, data: Dict[str, Any]):
        self._data = dict(data)
        self.id: str = validate_input(data.get("id"), "id", required=True)
        self.project_type: str = validate_input(
            data.get("project_type"), "project_type", required=True
        )
        self.downloads: int = validate_input(
            data.get("downloads"), "downloads", required=True
        )
        self.team: str = validate_input(data.get("team"), "team", required=True)
        self.published: datetime = datetime.fromisoformat(
            validate_input(data.get("published"), "published", required=True)
        )
        self.updated: datetime = datetime.fromisoformat(
            validate_input(data.get("updated"), "updated", required=True)
        )
        self.followers: int = validate_input(
            data.get("followers"), "followers", required=True
        )
        self.license: Optional[License] = (
            License(data["license"]) if data.get("license") else None
        )

        # Optional fields with defaults
        self.slug: str = (
            validate_input(data.get("slug", ""), "slug", required=False) or ""
        )
        self.title: Optional[str] = validate_input(
            data.get("title"), "title", required=False
        )
        self.description: Optional[str] = validate_input(
            data.get("description"), "description", required=False
        )
        self.categories: List[str] = (
            validate_input(data.get("categories", []), "categories", required=False)
            or []
        )
        self.client_side: Optional[SideType] = SideType(
            validate_input(data.get("client_side"), "client_side", required=False)
        )
        self.server_side: Optional[SideType] = SideType(
            validate_input(data.get("server_side"), "server_side", required=False)
        )
        self.body: Optional[str] = validate_input(
            data.get("body"), "body", required=False
        )
        self.status: Optional[ProjectStatus] = ProjectStatus(
            validate_input(data.get("status"), "status", required=False)
        )
        self.requested_status: Optional[RequestedStatus]
        if data.get("requested_status"):
            self.requested_status = RequestedStatus(
                validate_input(
                    data.get("requested_status"), "requested_status", required=False
                )
            )
        else:
            self.requested_status = None
        self.additional_categories: List[str] = (
            validate_input(
                data.get("additional_categories", []),
                "additional_categories",
                required=False,
            )
            or []
        )
        self.issues_url: Optional[str] = validate_input(
            data.get("issues_url"), "issues_url", required=False
        )
        self.source_url: Optional[str] = validate_input(
            data.get("source_url"), "source_url", required=False
        )
        self.wiki_url: Optional[str] = validate_input(
            data.get("wiki_url"), "wiki_url", required=False
        )
        self.discord_url: Optional[str] = validate_input(
            data.get("discord_url"), "discord_url", required=False
        )
        self.donation_urls: List[Dict[str, Any]] = (
            validate_input(
                data.get("donation_urls", []), "donation_urls", required=False
            )
            or []
        )
        self.icon_url: Optional[str] = validate_input(
            data.get("icon_url"), "icon_url", required=False
        )
        self.color: Optional[int] = validate_input(
            data.get("color"), "color", required=False
        )
        self.versions: List[str] = (
            validate_input(data.get("versions", []), "versions", required=False) or []
        )
        self.game_versions: List[str] = (
            validate_input(
                data.get("game_versions", []), "game_versions", required=False
            )
            or []
        )
        self.loaders: List[str] = (
            validate_input(data.get("loaders", []), "loaders", required=False) or []
        )
        self.gallery: List[GalleryItem] = [
            GalleryItem(item) for item in data.get("gallery", [])
        ]

        # HTTP client for making API requests
        self._http: Optional[HTTPClient] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert project data to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the project
        """
        return self._data

    def __repr__(self) -> str:
        return f"<Project id='{self.id}' title='{self.title}'>"

    def _init_http(self, http: HTTPClient) -> None:
        """Initialize HTTP client for API requests."""
        self._http = http

    async def get_version(self, version_id) -> Version:
        """
        Get the latest version of the project.

        Args:
            version_id (str): ID of the version

        Returns:
            Version: The latest version object

        Raises:
            NotFoundError: If no versions are found
        """
        if not self.versions:
            logger.warning(f"No versions found for project {self.id}")
            raise NotFoundError("No versions found for this project")
        if self._http is None:
            logger.error(f"HTTP client not initialized for project {self.id}")
            raise ValueError("HTTP client is not initialized.")

        logger.info(f"Fetching version {id} for project {self.id}")
        return await Versions(self._http).get_version(version_id)

    async def get_versions(self) -> List[Version]:
        """
        Get all versions of the project.

        Returns:
            List[Version]: List of all versions for the project

        Raises:
            NotFoundError: If no versions are found
        """
        if not self.versions:
            logger.warning(f"No versions found for project {self.id}")
            raise NotFoundError("No versions found for this project")
        if self._http is None:
            logger.error(f"HTTP client not initialized for project {self.id}")
            raise ValueError("HTTP client is not initialized.")

        logger.info(f"Fetching all versions for project {self.id}")
        versions = Versions(self._http)
        return await versions.get_versions(self.versions)

    async def get_latest_version(self, game_version: Optional[str] = None, loader: Optional[str] = None) -> Version:
        """
        Get the latest version of the project.

        Args:
            game_version (str): The game version to filter by
            loader (str): The loader to filter by

        Returns:
            Version: The latest version object

        Raises:
            NotFoundError: If no versions are found
        """
        logger.info(f"Fetching latest version for project {self.id}")
        if not game_version:
            return await self.get_version(self.latest_version)
        versions = await self.get_versions()
        for version in versions:
            if game_version in version.game_versions:
                if loader:
                    if loader in version.loaders:
                        logger.debug(f"Latest version for project {self.id} matching game version {game_version} and loader {loader} is {version.id}")
                        return version
                else:
                    logger.debug(f"Latest version for project {self.id} matching game version {game_version} is {version.id}")
                    return version
        else:
            logger.warning(
                f"No versions found for project {self.id} matching game version {game_version}"
            )
            raise NotFoundError(
                f"No versions found for game version {game_version}"
            )
            
    @property
    def latest_version(self) -> str:
        """
        Get the latest version ID.

        Returns:
            str: The latest version ID

        Raises:
            NotFoundError: If no versions are found
        """
        if not self.versions:
            logger.warning(f"No versions found for project {self.id}")
            raise NotFoundError("No versions found for this project")
        logger.debug(f"Latest version for project {self.id} is {self.versions[0]}")
        return self.versions[0]  # First version in the list is the latest


class SearchResult:
    """Container for project search results."""

    def __init__(self, data: Dict[str, Any], http: HTTPClient):
        """
        Initialize search results.

        Args:
            data: Raw search result data
            http: HTTP client for API requests
        """
        self._data = dict(data)
        hits = data.get("hits", [])
        self.hits: List[Project] = []

        for hit in hits:
            project = Project(hit)
            project._init_http(http)
            self.hits.append(project)

        self.total_hits: int = data.get("total_hits", 0)
        self.offset: int = data.get("offset", 0)
        self.limit: int = data.get("limit", 0)

    async def get_versions(self) -> List[Version]:
        """
        Get all the latest versions for the projects in the search results.

        Returns:
            List[Version]: List of all versions for the projects

        Raises:
            NotFoundError: If no versions are found
        """
        if not self.hits:
            raise NotFoundError("No projects found in search results")

        if not self.hits:
            raise NotFoundError("No projects found in search results")
        if not self.hits[0]._http:
            raise ValueError("HTTP client is not initialized.")

        versions = Versions(self.hits[0]._http)
        versionsCodes = [project.latest_version for project in self.hits]
        if not versionsCodes:
            raise NotFoundError("No versions found for this project")
        return await versions.get_versions(versionsCodes)

    def __repr__(self) -> str:
        return f"<SearchResult hits={len(self.hits)} total={self.total_hits}>"

    def __iter__(self):
        return iter(self.hits)

    def __len__(self) -> int:
        return len(self.hits)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert search results to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the search results
        """
        return self._data


class Projects:
    """
    High-level interface for project operations.

    This class provides methods to search for projects and fetch project details.
    It is typically accessed through the Client class.

    Example:
        >>> async with Client() as client:
        ...     # Search for projects
        ...     results = await client.search_projects("fabric", limit=5)
        ...     print(f"Found {len(results)} projects")
    """

    def __init__(self, http_client: HTTPClient):
        """
        Initialize Projects manager.

        Args:
            http_client: HTTP client for API requests
        """
        self.http = http_client

    async def get_project(self, project_id: str) -> Project:
        """
        Fetch a project by ID or slug.

        Args:
            project_id (str): Project ID or slug

        Returns:
            Project: The requested project

        Raises:
            NotFoundError: If project is not found
            ValidationError: If project_id is invalid
        """
        data = await self.http._get_project(project_id)
        project = Project(data)
        project._init_http(self.http)
        return project

    async def get_projects(self, project_ids: List[str]) -> List[Project]:
        """
        Fetch multiple projects by ID or slug.

        Args:
            project_ids (List[str]): List of project IDs or slugs

        Returns:
            List[Project]: List of requested projects
        """
        data = await self.http._get_projects(project_ids)
        projects = []
        for project_data in data:
            project = Project(project_data)
            project._init_http(self.http)
            projects.append(project)
        return projects

    async def search_projects(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        index: str = "relevance",
        facets: List[Facet] | None = None
    ) -> SearchResult:
        """
        Search for projects with optional filters.

        Args:
            query (str): Search query
            limit (int): Maximum number of results (default: 10)
            offset (int): Results offset for pagination (default: 0)
            index (str): Sort method (default: "relevance")
            facets (List[Facet] | None): List of facets to filter search results

        Returns:
            SearchResult: Container with search results

        Example:
            >>> results = await client.search_projects(
            ...     "mods",
            ...     limit=5,
            ...     sort="downloads",
            ...     facets=[Facet("project_type", ":", "mod"), Facet("categories", ":", "MODPACK")]
            ... )
            >>> for project in results:
            ...     print(f"{project.title}: {project.description}")
        """
        data = await self.http._search_project(
            query=query,
            limit=limit,
            offset=offset,
            index=index,
            facets = facets
        )
        hits = data.get("hits", [])
        if not isinstance(hits, list):
            raise TypeError(f"Expected 'hits' to be a list, got {type(hits).__name__}")
        ids: List[str] = [str(project["project_id"]) for project in hits]
        data["hits"] = await self.http._get_projects(ids)
        return SearchResult(data, self.http)
