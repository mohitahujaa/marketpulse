"""
Admin-only endpoints for user management.

All routes require admin role.
Includes pagination for scalability.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.middleware.auth import require_admin
from app.models.user import User
from app.schemas.auth import UserPublic
from app.utils.response import success_response
from security.pagination import PaginationParams, paginate_query

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", summary="List all users with pagination [Admin only]")
async def list_users(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all registered users with pagination.
    
    Admin access required.
    
    Query parameters:
    - skip: Number of records to skip (default: 0)
    - limit: Maximum records to return (default: 50, max: 100)
    """
    # Get total count
    count_query = select(func.count()).select_from(User)
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated users
    query = select(User).order_by(User.created_at.desc())
    paginated_query = paginate_query(query, pagination.skip, pagination.limit)
    result = await db.execute(paginated_query)
    users = result.scalars().all()
    
    return success_response(
        data={
            "users": [UserPublic.model_validate(u, from_attributes=True) for u in users],
            "pagination": {
                "total": total,
                "skip": pagination.skip,
                "limit": pagination.limit,
                "has_more": pagination.skip + pagination.limit < total
            }
        }
    )


@router.patch("/users/{user_id}/deactivate", summary="Deactivate a user [Admin only]")
async def deactivate_user(
    user_id: uuid.UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User", str(user_id))

    user.is_active = False
    await db.flush()
    return success_response(message=f"User {user.email} deactivated.")


@router.patch("/users/{user_id}/activate", summary="Activate a user [Admin only]")
async def activate_user(
    user_id: uuid.UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User", str(user_id))

    user.is_active = True
    await db.flush()
    return success_response(message=f"User {user.email} activated.")
