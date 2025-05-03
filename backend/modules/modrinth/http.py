"""
Modrinth HTTP Client Module.

This module provides a low-level HTTP client for interacting with the Modrinth API.
It handles rate limiting, retries, and error handling for all API requests.

Features:
- Automatic rate limit handling with exponential backoff
- Request retries for transient failures
- Detailed error reporting
- Session management
- Input validation
"""

import aiohttp
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union, TypeVar
from .utils import (
    MISSING,
    ModrinthException,
    RateLimitError,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    list_to_query_param,
    validate_input
)

all = [
    "HTTPClient",
]
logger = logging.getLogger("modrinth.http")

T = TypeVar('T')

class RateLimiter:
    """Handles API rate limiting."""
    
    def __init__(self, calls_per_minute: int = 300):
        self.calls_per_minute = calls_per_minute
        self.calls: List[datetime] = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """
        Acquire permission to make an API call.
        Blocks if rate limit would be exceeded.
        """
        async with self._lock:
            now = datetime.now()
            # Remove calls older than 1 minute
            self.calls = [t for t in self.calls if now - t < timedelta(minutes=1)]
            
            if len(self.calls) >= self.calls_per_minute:
                # Wait until oldest call is more than 1 minute old
                wait_time = timedelta(minutes=1) - (now - self.calls[0])
                if wait_time.total_seconds() > 0:
                    logger.warning(f"Rate limit reached. Waiting {wait_time.total_seconds():.2f}s")
                    await asyncio.sleep(wait_time.total_seconds())
            
            self.calls.append(now)

class HTTPClient:
    """
    Base HTTP client for the Modrinth API.
    
    This class handles all HTTP communication with the Modrinth API including:
    - Session management
    - Rate limiting
    - Error handling
    - Request retries
    
    Attributes:
        BASE_URL (str): Base URL for the Modrinth API
        DEFAULT_HEADERS (Dict[str, str]): Default headers sent with every request
        MAX_RETRIES (int): Maximum number of retry attempts for failed requests
    """

    BASE_URL = "https://api.modrinth.com/v2"
    DEFAULT_HEADERS = {
        "User-Agent": "Voxely/1.0.0 (python-modrinth-api)"
    }
    MAX_RETRIES = 3

    def __init__(self, timeout: int = 30):
        """
        Initialize the HTTP client.
        
        Args:
            timeout (int): Request timeout in seconds
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = RateLimiter()
        self._initialize_session()
    
    def _initialize_session(self):
        """Initialize the aiohttp ClientSession with default settings."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=self.DEFAULT_HEADERS
            )
    
    async def close(self):
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def __aenter__(self):
        """Context manager entry."""
        self._initialize_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Any:
        """
        Handle API response and possible errors.
        
        Args:
            response (aiohttp.ClientResponse): The API response to handle
            
        Returns:
            Any: Parsed response data
            
        Raises:
            RateLimitError: When rate limit is exceeded
            AuthenticationError: When authentication fails
            NotFoundError: When resource is not found
            ModrinthException: For other API errors
        """
        try:
            if response.status == 429:  # Rate limit exceeded
                retry_after = int(response.headers.get('Retry-After', 60))
                raise RateLimitError(
                    f"Rate limit exceeded. Retry after {retry_after} seconds"
                )
            
            response.raise_for_status()
            return await response.json()
            
        except aiohttp.ContentTypeError:
            text = await response.text()
            raise ModrinthException(f"Invalid JSON response: {text}")
        except aiohttp.ClientResponseError as e:
            if e.status == 401:
                raise AuthenticationError("Authentication failed")
            elif e.status == 404:
                raise NotFoundError("Resource not found")
            raise ModrinthException(f"HTTP {e.status}: {e.message}")

    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> Union[Dict[str, Any], List[Any]]:
        """
        Make an HTTP request to the Modrinth API.
        
        Args:
            method (str): HTTP method (GET, POST, etc.)
            endpoint (str): API endpoint (relative to BASE_URL)
            **kwargs: Additional arguments for the request
            
        Returns:
            Union[Dict[str, Any], List[Any]]: Parsed response data
            
        Raises:
            ModrinthException: For any API errors
        """
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        retries = 0
        
        while True:
            try:
                # Wait for rate limit
                await self.rate_limiter.acquire()
                if params := kwargs.get("params"):
                    if isinstance(params, dict):
                        for key, value in list(params.items()):  # Iterate over a copy of the items
                            if isinstance(value, list):
                                string = list_to_query_param(value, key)
                                url += f"?{string}"
                                params.pop(key)
                
                logger.info(f"Making {method} request to {url}")
                logger.debug(f"Request params: {kwargs.get('params', {})}")
                logger.debug(f"Request headers: {kwargs.get('headers', {})}")
                
                async with self.session.request(method, url, **kwargs) as response: # type: ignore
                    logger.debug(f"Response status: {response.status}")
                    logger.debug(f"Response headers: {dict(response.headers)}")
                    response_data = await self._handle_response(response)
                    logger.debug(f"Response data: {response_data}")
                    return response_data
                    
            except (
                aiohttp.ServerConnectionError,
                aiohttp.ServerTimeoutError,
                asyncio.TimeoutError
            ) as e:
                retries += 1
                logger.warning(f"Request failed (attempt {retries}/{self.MAX_RETRIES}): {str(e)}")
                if retries >= self.MAX_RETRIES:
                    logger.error(f"Max retries exceeded: {str(e)}")
                    raise ModrinthException(f"Max retries exceeded: {str(e)}")
                
                # Exponential backoff
                wait_time = 2 ** retries
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                continue
                
            except Exception as e:
                logger.error(f"Request failed: {str(e)}", exc_info=True)
                if isinstance(e, ModrinthException):
                    raise
                raise ModrinthException(f"Request failed: {str(e)}")

    def _facets_to_list(
        self,
        versions: str = MISSING,
        project_type: str = MISSING,
        categories: List[str] = MISSING,
        open_source: bool = MISSING,
        client_side: bool = MISSING,
        server_side: bool = MISSING,
    ) -> List[List[str]]:
        """
        Convert filter parameters to a faceted search list.
        
        Args:
            versions (str, optional): Version filter
            project_type (str, optional): Project type filters
            categories (List[str], optional): Category filters
            open_source (bool, optional): Filter by open source projects
            client_side (bool, optional): Filter by client-side projects
            server_side (bool, optional): Filter by server-side projects
            
        Returns:
            List[List[str]]: Formatted faceted search list
        """
        facets = []
        
        if categories is not MISSING:
            for category in categories:
                facets.append([f"categories:{category}"])
        
        if versions is not MISSING:
            facets.append([f"versions:{versions}"])
        
        if project_type is not MISSING:
            facets.append([f"project_type:{project_type}"])
        
        if open_source is not MISSING:
            facets.append([f"open_source:{'true' if client_side else 'false'}"])
        
        if client_side is not MISSING:
            facets.append([f"client_side:{'true' if client_side else 'false'}"])
        
        if server_side is not MISSING:
            facets.append([f"server_side:{'true' if server_side else 'false'}"])
        
        return facets

    async def _get_project(self, project_id: str) -> Dict[str, Any]:
        """
        Fetch a project by ID.
        
        Args:
            project_id (str): The project ID or slug
            
        Returns:
            Dict[str, Any]: Project data
            
        Raises:
            NotFoundError: If project is not found
        """
        validate_input(project_id, "project_id")
        result = await self._request("GET", f"project/{project_id}")
        if not isinstance(result, dict):
            raise ModrinthException("Expected a dictionary response for project data")
        return result
    
    async def _get_projects(self, project_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch multiple projects by ID.
        
        Args:
            project_ids (List[str]): List of project IDs or slugs
            
        Returns:
            List[Dict[str, Any]]: List of project data
        """
        validate_input(project_ids, "project_ids")
        result = await self._request("GET", "projects", params={"ids": project_ids})
        if not isinstance(result, list):
            raise ModrinthException("Expected a list response for project data")
        return result

    async def _search_project(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        sort: str = "relevance",
        versions: str = MISSING,
        project_type: str = MISSING,
        categories: List[str] = MISSING,
        open_source: bool = MISSING,
    ) -> Dict[str, Union[List[Dict[str, Union[str, int, List[str]]]], int]]:
        """
        Search for projects.
        
        Args:
            query (str): Search query
            limit (int): Maximum number of results (default: 10)
            offset (int): Results offset for pagination (default: 0)
            sort (str): Sort method (default: "relevance")
            versions (str, optional): Filter by versions
            project_type (str, optional): Filter by project types
            categories (List[str], optional): Filter by categories
            open_source (bool): Filter by open source projects (default: False)
            
        Returns:
            Dict[str, Union[List[Dict[str, Any]], int]]: Search results
        """
        validate_input(query, "query")
        
        facets = self._facets_to_list(
            versions=versions,
            project_type=project_type,
            categories=categories,
            open_source=open_source,
        )
        
        params = {
            "query": query,
            "limit": limit,
            "offset": offset,
            "sort": sort
        }
        if facets:
            params["facets"] = facets

        result = await self._request("GET", "search", params=params)
        if not isinstance(result, dict):
            raise ModrinthException("Expected a dictionary response for search results")
        return result

    async def _get_categories_tags(self) -> List[Dict[str, Any]]:
        """Fetch all category tags."""
        result = await self._request("GET", "tag/category")
        if not isinstance(result, list):
            raise ModrinthException("Expected a list response for category tags")
        return result
    
    async def _get_loader_tags(self) -> List[Dict[str, Any]]:
        """Fetch all loader tags."""
        result = await self._request("GET", "tag/loader")
        if not isinstance(result, list):
            raise ModrinthException("Expected a list of dictionaries for loader tags")
        return result

    async def _get_game_versions(self) -> List[Dict[str, Any]]:
        """Fetch all game versions."""
        result = await self._request("GET", "tag/game_version")
        if not isinstance(result, list):
            raise ModrinthException("Expected a list of dictionaries for game versions")
        return result
    
    async def _get_project_types(self) -> List[str]:
        """Fetch all project types."""
        result = await self._request("GET", "tag/project_type")
        if not isinstance(result, list):
            raise ModrinthException("Expected a list of strings for project types")
        return result

    async def _get_version(self, version_id: str) -> Dict[str, Any]:
        """
        Fetch a version by ID.
        
        Args:
            version_id (str): The version ID
            
        Returns:
            Dict[str, Any]: Version data
            
        Raises:
            NotFoundError: If version is not found
            ValidationError: If version_id is invalid
        """
        validate_input(version_id, "version_id")
        result = await self._request("GET", f"version/{version_id}")
        if not isinstance(result, dict):
            raise ModrinthException("Expected a dictionary response for version data")
        return result
    async def _get_versions(self, project_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch all versions for a given project.
        
        Args:
            project_ids (str): ID of the project
            
        Returns:
            List[Dict[str, Any]]: List of versions for the project
            
        Raises:
            NotFoundError: If the project is not found
            ValidationError: If the API returns invalid data
        """
        validate_input(project_ids, "project_ids")
        result = await self._request("GET", f"versions", params={"ids": project_ids})
        if not isinstance(result, list):
            raise ModrinthException("Expected a list response for version data")
        return result