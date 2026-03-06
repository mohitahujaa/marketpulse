"""
Market data endpoints — powered by CoinGecko.
"""
from fastapi import APIRouter, Depends, Query

from app.middleware.auth import get_current_active_user
from app.models.user import User
from app.services.coingecko import coingecko_service
from app.utils.response import success_response

router = APIRouter(prefix="/market", tags=["Market Data"])


@router.get("/search", summary="Search for coins by name or symbol")
async def search_coins(
    q: str = Query(..., min_length=1, max_length=100, description="Search query, e.g. 'bitcoin' or 'BTC'"),
    _: User = Depends(get_current_active_user),
):
    """
    Search CoinGecko for coins matching your query.
    Use the returned `id` field when adding coins to a watchlist.
    """
    results = await coingecko_service.search_coins(q)
    return success_response(data=results)
