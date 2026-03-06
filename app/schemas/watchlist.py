"""
Watchlist schemas — CRUD request/response validation.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Watchlist schemas
# ---------------------------------------------------------------------------

class WatchlistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)


class WatchlistUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)


class WatchlistItemSchema(BaseModel):
    id: UUID
    coin_id: str
    symbol: str
    added_at: datetime

    model_config = {"from_attributes": True}


class WatchlistResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    items: list[WatchlistItemSchema] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Watchlist item schemas
# ---------------------------------------------------------------------------

class AddCoinRequest(BaseModel):
    """Add a coin to a watchlist by its CoinGecko ID."""
    coin_id: str = Field(..., min_length=1, max_length=100, description="CoinGecko coin ID, e.g. 'bitcoin'")
    symbol: str = Field(..., min_length=1, max_length=20, description="Display symbol, e.g. 'BTC'")


# ---------------------------------------------------------------------------
# Market data schemas (from CoinGecko)
# ---------------------------------------------------------------------------

class CoinPrice(BaseModel):
    coin_id: str
    symbol: str
    name: str
    current_price_usd: float
    market_cap_usd: float | None
    price_change_24h_pct: float | None
    last_updated: str


class WatchlistPricesResponse(BaseModel):
    watchlist_id: UUID
    watchlist_name: str
    prices: list[CoinPrice]
