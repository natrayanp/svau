# utils/response_utils.py
from typing import Any, Optional, List, Dict, Type, Generic, TypeVar
from pydantic import BaseModel, Field
from fastapi import HTTPException, status
import datetime

T = TypeVar('T')  # Generic type for success data
E = TypeVar('E')  # Generic type for error details

class ApiResponse(BaseModel, Generic[T]):
    """Generic API response model for successful responses"""
    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Human-readable message")
    data: Optional[T] = Field(None, description="Response data payload")

    
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
    

class PaginatedData(BaseModel, Generic[T]):
    """Generic pagination wrapper"""
    items: List[T] = Field(..., description="List of items for current page")
    total: int = Field(..., description="Total number of items across all pages")
    page: int = Field(..., description="Current page number (1-based)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")

# ==================== SUCCESS RESPONSE HELPERS ====================

def success_response(
    data: Optional[T] = None, 
    message: str = "Success",
    **kwargs: Any
) -> ApiResponse[T]:
    """
    Create a successful API response with generic data type
    
    Args:
        data: The response data (any type)
        message: Success message
        **kwargs: Additional fields to include in response
    
    Returns:
        ApiResponse[T]: Typed success response
    """
    response_data = {
        "success": True,
        "message": message,
        "data": data,
        **kwargs
    }
    return ApiResponse[T](**response_data)


def paginated_response(
    items: List[T],
    total: int,
    page: int,
    page_size: int,
    message: str = "Success"
) -> ApiResponse[PaginatedData[T]]:
    """
    Create a paginated API response
    
    Args:
        items: List of items for current page
        total: Total number of items
        page: Current page number
        page_size: Number of items per page
        message: Success message
    
    Returns:
        ApiResponse[PaginatedData[T]]: Paginated response
    """
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    
    pagination_data = PaginatedData[T](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )
    
    return success_response(
        data=pagination_data,
        message=message
    )


def empty_success_response(
    message: str = "Operation completed successfully"
) -> ApiResponse[None]:
    """
    Create a success response without data
    
    Args:
        message: Success message
    
    Returns:
        ApiResponse[None]: Success response with no data
    """
    return success_response[None](data=None, message=message)


# ==================== ERROR RESPONSE HELPERS ====================

def error_response(
    message: str = "An error occurred",
    error_code: Optional[str] = None,
    error_details: Optional[E] = None,
    field: Optional[str] = None,
    **kwargs: Any
) -> ErrorResponse[E]:
    """
    Create an error API response with generic error details
    
    Args:
        message: Primary error message
        error_code: Machine-readable error code
        error_details: Additional error context
        field: Related field name if applicable
        **kwargs: Additional fields
    
    Returns:
        ErrorResponse[E]: Structured error response
    """
    error_detail = None
    if error_code or error_details or field:
        error_detail = ErrorDetail[E](
            code=error_code or "UNKNOWN_ERROR",
            message=message,
            details=error_details,
            field=field
        )
    
    response_data = {
        "success": False,
        "message": message,
        "error": error_detail,
        **kwargs
    }
    
    return ErrorResponse[E](**response_response_data)


def not_found_error(
    resource: str = "Resource",
    resource_id: Optional[Any] = None,
    **kwargs: Any
) -> ErrorResponse[Dict[str, Any]]:
    """
    Create a standardized 404 Not Found error response
    
    Args:
        resource: Name of the resource not found
        resource_id: ID of the resource not found
        **kwargs: Additional fields
    
    Returns:
        ErrorResponse: Not found error response
    """
    message = f"{resource} not found"
    if resource_id is not None:
        message = f"{resource} with ID '{resource_id}' not found"
    
    return error_response(
        message=message,
        error_code="NOT_FOUND",
        error_details={"resource": resource, "resource_id": resource_id},
        **kwargs
    )


def validation_error(
    message: str = "Validation failed",
    field_errors: Optional[Dict[str, List[str]]] = None,
    **kwargs: Any
) -> ErrorResponse[Dict[str, Any]]:
    """
    Create a validation error response
    
    Args:
        message: Primary validation error message
        field_errors: Dictionary of field-specific errors
        **kwargs: Additional fields
    
    Returns:
        ErrorResponse: Validation error response
    """
    return error_response(
        message=message,
        error_code="VALIDATION_ERROR",
        error_details={"field_errors": field_errors or {}},
        **kwargs
    )


def unauthorized_error(
    message: str = "Authentication required",
    **kwargs: Any
) -> ErrorResponse[None]:
    """
    Create an unauthorized error response
    
    Args:
        message: Unauthorized message
        **kwargs: Additional fields
    
    Returns:
        ErrorResponse: Unauthorized error response
    """
    return error_response(
        message=message,
        error_code="UNAUTHORIZED",
        **kwargs
    )


def forbidden_error(
    message: str = "Access forbidden",
    required_permission: Optional[str] = None,
    **kwargs: Any
) -> ErrorResponse[Dict[str, Any]]:
    """
    Create a forbidden error response
    
    Args:
        message: Forbidden message
        required_permission: Required permission if applicable
        **kwargs: Additional fields
    
    Returns:
        ErrorResponse: Forbidden error response
    """
    details = {}
    if required_permission:
        details["required_permission"] = required_permission
    
    return error_response(
        message=message,
        error_code="FORBIDDEN",
        error_details=details if details else None,
        **kwargs
    )


# ==================== HTTP EXCEPTION HELPERS ====================

def http_exception(
    status_code: int,
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Any] = None
) -> HTTPException:
    """
    Create an HTTPException with standardized error format
    
    Args:
        status_code: HTTP status code
        message: Error message
        error_code: Machine-readable error code
        details: Additional error details
    
    Returns:
        HTTPException: Formatted HTTP exception
    """
    error_response = ErrorResponse(
        success=False,
        message=message,
        error=ErrorDetail(
            code=error_code or "HTTP_ERROR",
            message=message,
            details=details
        ) if error_code or details else None
    )
    
    return HTTPException(
        status_code=status_code,
        detail=error_response.dict()
    )
