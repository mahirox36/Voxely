"""
Utility module for the Modrinth API wrapper.
Contains helper classes, enums, and functions for working with the Modrinth API.
"""

from json import dumps
from typing import Any, Optional, Union, TypeVar, Dict, overload
import logging
from enum import StrEnum
from datetime import datetime
from urllib.parse import quote

T = TypeVar('T')

logger = logging.getLogger("modrinth")

# Helper types for validation
OptionalT = TypeVar('OptionalT')
RequiredT = TypeVar('RequiredT')
all = [
    "format_datetime",
    "validate_input",
    "list_to_query_param",
    "MISSING",
    "ModrinthException",
    "RateLimitError",
    "AuthenticationError",
    "NotFoundError",
    "ValidationError",
    "ProjectType",
    "SideType",
    "ProjectStatus",
    "RequestedStatus",
    "MonetizationStatus",
    "VersionType",
    "DependencyType",
    "VersionStatus",
    "logger"
]


class ModrinthException(Exception):
    """Base exception for all Modrinth API errors."""
    pass

class RateLimitError(ModrinthException):
    """Raised when the API rate limit is exceeded."""
    pass

class AuthenticationError(ModrinthException):
    """Raised when authentication fails."""
    pass

class NotFoundError(ModrinthException):
    """Raised when a resource is not found."""
    pass

class ValidationError(ModrinthException):
    """Raised when input validation fails."""
    pass

class _MissingSentinel:
    """
    A sentinel object to represent missing values.
    This is used instead of None because None might be a valid value in some cases.
    """
    def __eq__(self, other: Any) -> bool:
        return self is other

    def __hash__(self) -> int:
        return id(self)

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "..."

MISSING: Any = _MissingSentinel()

def format_datetime(date: Optional[str]) -> Optional[datetime]:
    """
    Convert an ISO 8601 formatted date string to a datetime object.
    
    Args:
        date (Optional[str]): An ISO 8601 formatted date string
        
    Returns:
        Optional[datetime]: A datetime object if the input is valid, None otherwise
        
    Example:
        >>> format_datetime("2024-04-22T10:30:00Z")
        datetime.datetime(2024, 4, 22, 10, 30)
        >>> format_datetime(None)
        None
    """
    return datetime.fromisoformat(date.replace('Z', '+00:00')) if date else None

@overload
def validate_input(value: Any, field_name: str, *, required: bool = True) -> RequiredT: # type: ignore
    ...

@overload
def validate_input(value: Any, field_name: str, *, required: bool = False) -> Optional[OptionalT]: # type: ignore
    ...

def validate_input(value: Any, field_name: str, *, required: bool = True) -> Any:
    """
    Validate input values for API calls.
    
    Args:
        value: The value to validate
        field_name (str): Name of the field being validated
        required (bool): Whether the field is required
        
    Raises:
        ValidationError: If validation fails
        
    Returns:
        The validated value, or None if not required and missing
    """
    if required:
        if value is MISSING or value is None:
            raise ValidationError(f"{field_name} is required")
        return value
    return value if value is not MISSING else None

def list_to_query_param(values: list[str], param) -> str:
    """
    Convert a list of values into a URL query parameter string.
    
    :param: values (list[str]): The list of values to convert.
    :param: param (str): The parameter name to use in the query string.

    Returns:
        str: A URL query parameter string.

    Example:
        >>> list_to_query_param(["mod", "plugin"])
        "[mod&plugin]"
    """
    # %22 is the URL-encoded representation of a double quote (")
    # %2C is the URL-encoded representation of a comma (,)
    # + is the URL-encoded representation of a space
    
    json_array = dumps(values)
    logger.debug(json_array)
    return f"{param}={quote(json_array)}"

class ProjectType(StrEnum):
    """Enum for Modrinth project types."""
    MOD = "mod"
    MODPACK = "modpack"
    RESOURCEPACK = "resourcepack"
    SHADER = "shader"
    PLUGIN = "plugin"
    DATAPACK = "datapack"
    
class SideType(StrEnum):
    """Enum for Modrinth side support."""
    REQUIRED = "required"
    OPTIONAL = "optional"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"

class ProjectStatus(StrEnum):
    """Enum for Modrinth project status."""
    APPROVED = "approved"
    ARCHIVED = "archived"
    REJECTED = "rejected"
    DRAFT = "draft"
    UNLISTED = "unlisted"
    PROCESSING = "processing"
    WITHHELD = "withheld"
    SCHEDULED = "scheduled"
    PRIVATE = "private"
    UNKNOWN = "unknown"

class RequestedStatus(StrEnum):
    """Enum for Modrinth requested status."""
    APPROVED = "approved"
    ARCHIVED = "archived"
    UNLISTED = "unlisted"
    PRIVATE = "private"
    DRAFT = "draft"


class MonetizationStatus(StrEnum):
    """Enum for Modrinth monetization status."""
    MONETIZED = "monetized"
    DEMONETIZED = "demonetized"
    FORCE_DEMONETIZED = "force-demonetized"
    UNKNOWN = "unknown"

class VersionType(StrEnum):
    """
    Enum for Modrinth version types.
    
    Attributes:
        RELEASE: Stable release version
        SNAPSHOT: Development snapshot version
        ALPHA: Alpha testing version
        BETA: Beta testing version
    """
    RELEASE = "release"
    SNAPSHOT = "snapshot"
    ALPHA = "alpha"  
    BETA = "beta"

class DependencyType(StrEnum):
    """Enum for Modrinth dependency types.
    
    Attributes:
        REQUIRED: Required dependency
        OPTIONAL: Optional dependency
        INCOMPATIBLE: Incompatible dependency
        EMBEDDED: Embedded dependency
    """
    REQUIRED = "required"
    OPTIONAL = "optional"
    INCOMPATIBLE = "incompatible"
    EMBEDDED = "embedded"

class VersionStatus(StrEnum):
    """Enum for Modrinth version status.
    
    Attributes:
        LISTED: Version is listed and available for download
        ARCHIVED: Version is archived and not available for download
        DRAFT: Version is a draft and not publicly available
        UNLISTED: Version is unlisted and not publicly available
        SCHEDULED: Version is scheduled for future release
        UNKNOWN: Status is unknown or not specified
    """
    LISTED = "listed"
    ARCHIVED = "archived"
    DRAFT = "draft"
    UNLISTED = "unlisted"
    SCHEDULED = "scheduled"
    UNKNOWN = "unknown"