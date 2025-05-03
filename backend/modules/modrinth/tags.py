"""
Modrinth Tags API Module.

This module provides a high-level interface to interact with the Modrinth API's tag-related endpoints.
It includes functionality for fetching category tags, loader tags, and game version tags.

Example:
    >>> async with Client() as client:
    ...     tags = await client.get_category_tags()
    ...     for tag in tags:
    ...         print(f"{tag.name} - {tag.project_type}")
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from .http import HTTPClient
from .utils import (
    MISSING, 
    VersionType, 
    validate_input,
    ValidationError,
    NotFoundError
)

logger = logging.getLogger("modrinth.tags")

all = [
    "CategoryTag",
    "LoaderTag",
    "GameVersionTag",
    "Tags",
]

class CategoryTag:
    """
    Represents a category tag for a Modrinth project.
    
    Attributes:
        icon (str): URL to the category's icon
        name (str): Display name of the category
        project_type (str): Type of projects this category applies to
        header (str): Header text for the category
    """

    def __init__(self, data: Dict[str, Any]):
        self.icon: str = validate_input(data.get("icon"), "icon", required=True)
        self.name: str = validate_input(data.get("name"), "name", required=True)
        self.project_type: str = validate_input(data.get("project_type"), "project_type", required=True)
        self.header: str = validate_input(data.get("header"), "header", required=True)
    
    def __repr__(self) -> str:
        return f"<CategoryTag name='{self.name}' type='{self.project_type}'>"

class LoaderTag:
    """
    Represents a loader tag for a Modrinth project.
    
    Attributes:
        icon (str): URL to the loader's icon
        name (str): Display name of the loader
        supported_project_types (List[str]): Project types this loader supports
    """

    def __init__(self, data: Dict[str, Any]):
        self.icon: str = validate_input(data.get("icon"), "icon", required=True)
        self.name: str = validate_input(data.get("name"), "name", required=True)
        self.supported_project_types: List[str] = validate_input(
            data.get("supported_project_types", []), 
            "supported_project_types",
            required=True
        )
    
    def __repr__(self) -> str:
        return f"<LoaderTag name='{self.name}'>"

class GameVersionTag:
    """
    Represents a game version tag for a Modrinth project.
    
    Attributes:
        version (str): The version string (e.g., "1.19.2")
        version_type (VersionType): Type of version (release, snapshot, etc.)
        date (datetime): Release date of the version
        major (bool): Whether this is a major version
    """

    def __init__(self, data: Dict[str, Any]):
        self.version: str = validate_input(data.get("version"), "version", required=True)
        self.version_type: VersionType = VersionType(
            validate_input(data.get("version_type"), "version_type", required=True)
        )
        try:
            self.date: datetime = datetime.fromisoformat(
                validate_input(data.get("date"), "date", required=True)
            )
        except ValueError as e:
            raise ValidationError(f"Invalid date format: {e}")
        
        self.major: bool = validate_input(data.get("major", False), "major", required=False)
    
    def __repr__(self) -> str:
        return f"<GameVersionTag version='{self.version}' type='{self.version_type.value}'>"

class Tags:
    """
    Manages tag-related operations for the Modrinth API.
    
    This class provides methods to fetch different types of tags from Modrinth,
    including categories, loaders, and game versions.
    
    Example:
        >>> async with Client() as client:
        ...     categories = await client.get_category_tags()
        ...     print(f"Found {len(categories)} categories")
    """
    
    def __init__(self, http_client: HTTPClient):
        """
        Initialize the Tags manager.
        
        Args:
            http_client (HTTPClient): The HTTP client to use for API requests
        """
        self.http_session = http_client
    
    async def get_category_tags(self) -> List[CategoryTag]:
        """
        Fetch all category tags from the Modrinth API.
        
        Returns:
            List[CategoryTag]: List of category tags
            
        Raises:
            NotFoundError: If the category tags endpoint is not found
            ValidationError: If the API returns invalid data
        """
        logger.info("Fetching category tags")
        try:
            tags = await self.http_session._get_categories_tags()
            return [CategoryTag(tag) for tag in tags]
        except Exception as e:
            logger.error(f"Failed to fetch category tags: {str(e)}", exc_info=True)
            raise NotFoundError(f"Failed to fetch category tags: {str(e)}")
    
    async def get_loader_tags(self) -> List[LoaderTag]:
        """
        Fetch all loader tags from the Modrinth API.
        
        Returns:
            List[LoaderTag]: List of loader tags
            
        Raises:
            NotFoundError: If the loader tags endpoint is not found
            ValidationError: If the API returns invalid data
        """
        logger.info("Fetching loader tags")
        try:
            tags = await self.http_session._get_loader_tags()
            return [LoaderTag(tag) for tag in tags]
        except Exception as e:
            logger.error(f"Failed to fetch loader tags: {str(e)}", exc_info=True)
            raise NotFoundError(f"Failed to fetch loader tags: {str(e)}")
    
    async def get_game_version_tags(self) -> List[GameVersionTag]:
        """
        Fetch all game version tags from the Modrinth API.
        
        Returns:
            List[GameVersionTag]: List of game version tags
            
        Raises:
            NotFoundError: If the game version tags endpoint is not found
            ValidationError: If the API returns invalid data
        """
        logger.info("Fetching game version tags")
        try:
            tags = await self.http_session._get_game_versions()
            return [GameVersionTag(tag) for tag in tags]
        except Exception as e:
            logger.error(f"Failed to fetch game version tags: {str(e)}", exc_info=True)
            raise NotFoundError(f"Failed to fetch game version tags: {str(e)}")