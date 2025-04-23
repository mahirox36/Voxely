"""
Modrinth API Client.

This is the main entry point for the Modrinth API wrapper.
It provides a high-level interface to interact with Modrinth's API, combining
functionality from all other modules.

Features:
- Project searching and browsing
- Version management
- File downloading
- Tag management
- Rate limiting
- Error handling

Example:
    >>> from modrinth import Client
    >>> 
    >>> async with Client() as client:
    ...     # Search for a mod
    ...     results = await client.search_projects("JEI")
    ...     
    ...     if results.hits:
    ...         project = results.hits[0]
    ...         print(f"Found {project.title}")
    ...         
    ...         # Get the latest version
    ...         version = await project.get_latest_version()
    ...         
    ...         # Download the mod file
    ...         for file in version.files:
    ...             path = await file.download("mods")
    ...             print(f"Downloaded to {path}")
"""

from typing import Optional, List, Union, Dict, Any
from .http import HTTPClient
from .project import Project, Projects, SearchResult
from .versions import Version, File, Versions
from .tags import Tags, CategoryTag, LoaderTag, GameVersionTag
from .utils import (
    MISSING,
    ModrinthException,
    RateLimitError,
    AuthenticationError,
    NotFoundError,
    ValidationError
)
all = [
    "Client",
]

class Client(Projects, Tags, Versions):
    """
    Main client class for interacting with the Modrinth API.
    
    This class combines all functionality from other modules into a single interface.
    It inherits from Projects and Tags to provide direct access to their methods.
    
    Attributes:
        DEFAULT_TIMEOUT (int): Default request timeout in seconds
        
    Example:
        >>> async with Client() as client:
        ...     # Basic project search
        ...     results = await client.search_projects("fabric")
        ...     
        ...     # Get available categories
        ...     categories = await client.get_category_tags()
        ...     
        ...     # Advanced search with filters
        ...     mods = await client.search_projects(
        ...         "tech",
        ...         categories=["fabric", "technology"],
        ...         open_source=True
        ...     )
    """
    
    DEFAULT_TIMEOUT = 30

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize the Modrinth client.
        
        Args:
            timeout (int, optional): Request timeout in seconds
        """
        self.http = HTTPClient(timeout=timeout)
        Projects.__init__(self, self.http)
        Tags.__init__(self, self.http)
        Versions.__init__(self, self.http)

    async def __aenter__(self) -> "Client":
        """Async context manager entry."""
        await self.http.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.http.__aexit__(exc_type, exc_val, exc_tb)

    async def close(self):
        """Close the client and clean up resources."""
        await self.http.close()

    # Re-export common exceptions for convenience
    ModrinthException = ModrinthException
    RateLimitError = RateLimitError
    AuthenticationError = AuthenticationError
    NotFoundError = NotFoundError
    ValidationError = ValidationError