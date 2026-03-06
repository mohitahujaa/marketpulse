"""
Pagination utilities for list endpoints.

Implements offset-based pagination with configurable limits.
Production-ready with proper defaults and validation.
"""
from typing import Generic, List, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """
    Standard pagination query parameters.
    
    Usage in endpoint:
        @router.get("/items")
        async def list_items(pagination: PaginationParams = Depends()):
            ...
    """
    skip: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(default=50, ge=1, le=100, description="Maximum items to return")
    
    @property
    def offset(self) -> int:
        """Alias for skip (SQL OFFSET terminology)."""
        return self.skip
    
    def to_dict(self) -> dict:
        """Convert to dict for query building."""
        return {"offset": self.skip, "limit": self.limit}


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper.
    
    Example response:
    {
        "success": true,
        "data": [...],
        "pagination": {
            "total": 150,
            "skip": 0,
            "limit": 50,
            "has_more": true
        }
    }
    """
    data: List[T]
    total: int = Field(description="Total number of items")
    skip: int = Field(description="Number of items skipped")
    limit: int = Field(description="Maximum items returned")
    
    @property
    def has_more(self) -> bool:
        """Whether there are more items to fetch."""
        return self.skip + self.limit < self.total
    
    def to_response(self) -> dict:
        """Convert to API response format."""
        return {
            "success": True,
            "data": [item.model_dump() if hasattr(item, "model_dump") else item for item in self.data],
            "pagination": {
                "total": self.total,
                "skip": self.skip,
                "limit": self.limit,
                "has_more": self.has_more,
                "current_page": (self.skip // self.limit) + 1 if self.limit > 0 else 1,
                "total_pages": (self.total + self.limit - 1) // self.limit if self.limit > 0 else 1
            }
        }


def paginate_query(query, skip: int = 0, limit: int = 50):
    """
    Apply pagination to SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query object
        skip: Number of items to skip
        limit: Maximum items to return
        
    Returns:
        Paginated query
    """
    return query.offset(skip).limit(limit)
