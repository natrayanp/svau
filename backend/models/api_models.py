from pydantic import BaseModel, Field
from typing import Any, Dict, Generic, List, Optional, TypeVar
import datetime

T = TypeVar('T')  # Generic type for success data
E = TypeVar('E')  # Generic type for error details


class OperationMetadata(BaseModel):
    success: bool = Field(..., description="Whether the request was successful")
    entity: str = Field(..., description="Entity on which the operation was performed")
    operation: str = Field(..., description="Type of operation performed")
    message: str = Field(..., description="Human-readable message")
    count: int = Field(..., description="Number of entities affected")
    ids: List[str] = Field(..., description="List of IDs of entities affected")


class ApiResponse(BaseModel, Generic[T]):
    """Generic API response model for successful responses"""
    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Human-readable message")
    data: Optional[T] = Field(None, description="Response data payload")
    operation_metadata: Optional[OperationMetadata] = Field(None, description="Additional metadata about the operation")
    timestamp: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    
    class Config:
        json_encoders = {
            datetime.datetime: lambda v: v.isoformat(),
        }

class ErrorDetail(BaseModel, Generic[E]):
    """Generic error detail structure"""
    code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[E] = Field(None, description="Additional error details")
    field: Optional[str] = Field(None, description="Related field name if applicable")

class ErrorResponse(BaseModel, Generic[E]):
    """Generic error response model"""
    success: bool = Field(False, description="Always false for error responses")
    message: str = Field(..., description="Primary error message")
    error: Optional[ErrorDetail[E]] = Field(None, description="Structured error information")
    timestamp: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat())


class TableVersion(BaseModel):
    table_name: str = Field(..., description="Name of the table")
    table_version: int = Field(..., description="Global version number for the table")

class PaginatedData(BaseModel, Generic[T]):
    """Generic pagination wrapper with offset/limit and table version tracking"""
    items: List[T] = Field(..., description="List of items for current page")
    total: int = Field(..., description="Total number of items across all pages")
    offset: int = Field(..., description="Offset index for current page (0-based)")
    limit: int = Field(..., description="Number of items per page (limit)")
    org_id: int = Field(..., description="Organization identifier that owns the table")
    version: List[TableVersion] = Field(..., description="Version info for related tables")

class PaginatedDataResponse(BaseModel, Generic[T]):
    """Generic pagination wrapper with offset/limit and table version tracking"""
    data: PaginatedData[T] = Field(..., description="Paginated data")
    operation_metadata: Optional[OperationMetadata] = Field(None, description="Additional metadata about the operation")