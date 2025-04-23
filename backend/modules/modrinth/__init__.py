"""
Modrinth API wrapper for Python.

This library provides a high-level interface to interact with the Modrinth API.
It supports searching for mods, downloading files, managing versions, and more.

Features:
- Asynchronous API with asyncio support
- Rate limiting and request retries
- Comprehensive error handling
- Type hints and validation
- File downloads with progress tracking
- Version management and filtering

Basic Usage:
    >>> from modrinth import Client
    >>> 
    >>> async with Client() as client:
    ...     # Search for mods
    ...     results = await client.search_projects("JEI")
    ...     
    ...     # Get project details
    ...     project = await client.get_project("fabric-api")
    ...     
    ...     # Get latest version
    ...     version = await project.get_latest_version()
    ...     
    ...     # Download files
    ...     for file in version.files:
    ...         path = await file.download("mods")

Advanced Usage:
    >>> async with Client() as client:
    ...     # Search with filters
    ...     results = await client.search_projects(
    ...         "tech",
    ...         limit=10,
    ...         categories=["fabric", "technology"],
    ...         game_versions=["1.20.1"],
    ...         open_source=True
    ...     )
    ...     
    ...     # Get available categories
    ...     categories = await client.get_category_tags()
    ...     
    ...     # Get game versions
    ...     versions = await client.get_game_version_tags()
"""

from .client import *
from .project import *
from .tags import *
from .utils import *
from .versions import *
__version__ = "1.0.0"
__author__ = "Mahiro"
__license__ = "MIT"
