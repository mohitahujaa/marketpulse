"""
Watchlist endpoints: full CRUD + live price fetching.
"""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.middleware.auth import get_current_active_user
from app.models.user import User
from app.schemas.watchlist import AddCoinRequest, WatchlistCreate, WatchlistResponse, WatchlistUpdate
from app.services import watchlist as watchlist_service
from app.utils.response import success_response

router = APIRouter(prefix="/watchlists", tags=["Watchlists"])


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a new watchlist")
async def create_watchlist(
    payload: WatchlistCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    wl = await watchlist_service.create_watchlist(payload, current_user, db)
    return success_response(
        data=WatchlistResponse.model_validate(wl),
        message="Watchlist created.",
        status_code=status.HTTP_201_CREATED,
    )


@router.get("", summary="List watchlists (own for users, all for admins)")
async def list_watchlists(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    watchlists = await watchlist_service.list_watchlists(current_user, db)
    return success_response(data=[WatchlistResponse.model_validate(wl) for wl in watchlists])


@router.get("/{watchlist_id}", summary="Get a single watchlist")
async def get_watchlist(
    watchlist_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    wl = await watchlist_service.get_watchlist(watchlist_id, current_user, db)
    return success_response(data=WatchlistResponse.model_validate(wl))


@router.patch("/{watchlist_id}", summary="Update watchlist name or description")
async def update_watchlist(
    watchlist_id: uuid.UUID,
    payload: WatchlistUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    wl = await watchlist_service.update_watchlist(watchlist_id, payload, current_user, db)
    return success_response(data=WatchlistResponse.model_validate(wl), message="Watchlist updated.")


@router.delete("/{watchlist_id}", status_code=status.HTTP_200_OK, summary="Delete a watchlist")
async def delete_watchlist(
    watchlist_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await watchlist_service.delete_watchlist(watchlist_id, current_user, db)
    return success_response(message="Watchlist deleted.")


# ---------------------------------------------------------------------------
# Coin items
# ---------------------------------------------------------------------------

@router.post("/{watchlist_id}/coins", status_code=status.HTTP_201_CREATED, summary="Add a coin to watchlist")
async def add_coin(
    watchlist_id: uuid.UUID,
    payload: AddCoinRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a crypto coin to a watchlist using its CoinGecko ID.
    Example: `{"coin_id": "bitcoin", "symbol": "BTC"}`
    """
    item = await watchlist_service.add_coin(watchlist_id, payload, current_user, db)
    return success_response(data={"item_id": str(item.id), "coin_id": item.coin_id}, message="Coin added.")


@router.delete("/{watchlist_id}/coins/{item_id}", summary="Remove a coin from watchlist")
async def remove_coin(
    watchlist_id: uuid.UUID,
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await watchlist_service.remove_coin(watchlist_id, item_id, current_user, db)
    return success_response(message="Coin removed from watchlist.")


# ---------------------------------------------------------------------------
# Live prices
# ---------------------------------------------------------------------------

@router.get("/{watchlist_id}/prices", summary="Get live prices for all coins in watchlist")
async def get_prices(
    watchlist_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetches live USD prices from CoinGecko for every coin in the watchlist.
    Includes: current price, market cap, and 24h % change.
    """
    prices = await watchlist_service.get_watchlist_prices(watchlist_id, current_user, db)
    return success_response(data=prices)
