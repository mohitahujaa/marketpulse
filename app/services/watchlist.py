"""
Watchlist service — CRUD operations and price fetching.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.core.logging import get_logger
from app.models.user import User, UserRole
from app.models.watchlist import Watchlist, WatchlistItem
from app.schemas.watchlist import (
    AddCoinRequest,
    WatchlistCreate,
    WatchlistPricesResponse,
    WatchlistUpdate,
)
from app.services.coingecko import coingecko_service

logger = get_logger("watchlist_service")


async def _get_watchlist_or_404(
    watchlist_id: uuid.UUID, db: AsyncSession, load_items: bool = True
) -> Watchlist:
    """Fetch watchlist by ID with eager-loaded items, raise 404 if missing."""
    query = select(Watchlist).where(Watchlist.id == watchlist_id)
    if load_items:
        query = query.options(selectinload(Watchlist.items))
    result = await db.execute(query)
    wl = result.scalar_one_or_none()
    if not wl:
        raise NotFoundException("Watchlist", str(watchlist_id))
    return wl


def _check_ownership(watchlist: Watchlist, user: User) -> None:
    """Admins can access any watchlist; users only their own."""
    if user.role != UserRole.ADMIN and watchlist.owner_id != user.id:
        raise ForbiddenException("You do not have access to this watchlist.")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

async def create_watchlist(payload: WatchlistCreate, owner: User, db: AsyncSession) -> Watchlist:
    wl = Watchlist(name=payload.name, description=payload.description, owner_id=owner.id)
    db.add(wl)
    await db.flush()
    await db.refresh(wl, ["items"])
    logger.info("Watchlist created", extra={"watchlist_id": str(wl.id), "user_id": str(owner.id)})
    return wl


async def list_watchlists(user: User, db: AsyncSession) -> list[Watchlist]:
    """Users see their own; admins see all."""
    query = select(Watchlist).options(selectinload(Watchlist.items))
    if user.role != UserRole.ADMIN:
        query = query.where(Watchlist.owner_id == user.id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_watchlist(watchlist_id: uuid.UUID, user: User, db: AsyncSession) -> Watchlist:
    wl = await _get_watchlist_or_404(watchlist_id, db)
    _check_ownership(wl, user)
    return wl


async def update_watchlist(
    watchlist_id: uuid.UUID, payload: WatchlistUpdate, user: User, db: AsyncSession
) -> Watchlist:
    wl = await _get_watchlist_or_404(watchlist_id, db)
    _check_ownership(wl, user)

    if payload.name is not None:
        wl.name = payload.name
    if payload.description is not None:
        wl.description = payload.description

    await db.flush()
    logger.info("Watchlist updated", extra={"watchlist_id": str(wl.id)})
    return wl


async def delete_watchlist(watchlist_id: uuid.UUID, user: User, db: AsyncSession) -> None:
    wl = await _get_watchlist_or_404(watchlist_id, db, load_items=False)
    _check_ownership(wl, user)
    await db.delete(wl)
    logger.info("Watchlist deleted", extra={"watchlist_id": str(wl.id)})


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------

async def add_coin(
    watchlist_id: uuid.UUID, payload: AddCoinRequest, user: User, db: AsyncSession
) -> WatchlistItem:
    wl = await _get_watchlist_or_404(watchlist_id, db)
    _check_ownership(wl, user)

    # Prevent duplicate
    existing = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.watchlist_id == watchlist_id,
            WatchlistItem.coin_id == payload.coin_id.lower(),
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictException(f"'{payload.coin_id}' is already in this watchlist.")

    item = WatchlistItem(
        watchlist_id=watchlist_id,
        coin_id=payload.coin_id.lower(),
        symbol=payload.symbol.upper(),
    )
    db.add(item)
    await db.flush()
    logger.info("Coin added to watchlist", extra={"coin_id": item.coin_id, "watchlist_id": str(watchlist_id)})
    return item


async def remove_coin(
    watchlist_id: uuid.UUID, item_id: uuid.UUID, user: User, db: AsyncSession
) -> None:
    wl = await _get_watchlist_or_404(watchlist_id, db, load_items=False)
    _check_ownership(wl, user)

    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.id == item_id,
            WatchlistItem.watchlist_id == watchlist_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise NotFoundException("WatchlistItem", str(item_id))

    await db.delete(item)
    logger.info("Coin removed from watchlist", extra={"item_id": str(item_id)})


# ---------------------------------------------------------------------------
# Price fetching
# ---------------------------------------------------------------------------

async def get_watchlist_prices(
    watchlist_id: uuid.UUID, user: User, db: AsyncSession
) -> WatchlistPricesResponse:
    """Fetch live CoinGecko prices for all coins in a watchlist."""
    wl = await _get_watchlist_or_404(watchlist_id, db)
    _check_ownership(wl, user)

    coin_ids = [item.coin_id for item in wl.items]
    prices = await coingecko_service.get_prices(coin_ids)

    return WatchlistPricesResponse(
        watchlist_id=wl.id,
        watchlist_name=wl.name,
        prices=prices,
    )
