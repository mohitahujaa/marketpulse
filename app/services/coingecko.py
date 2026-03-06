"""
CoinGecko API integration service.

Key production patterns demonstrated:
- Async HTTP client (httpx)
- Configurable timeout
- Retry with exponential backoff
- Structured error logging
- Typed return values
"""
import asyncio

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalAPIException
from app.core.logging import get_logger
from app.schemas.watchlist import CoinPrice

logger = get_logger("coingecko")


class CoinGeckoService:
    """
    Thin async wrapper around the CoinGecko public API.
    Handles retries, timeouts, and error normalization.
    """

    BASE_URL = settings.COINGECKO_BASE_URL
    TIMEOUT = settings.COINGECKO_TIMEOUT_SECONDS
    MAX_RETRIES = settings.COINGECKO_MAX_RETRIES
    BACKOFF = settings.COINGECKO_RETRY_BACKOFF

    async def _get(self, endpoint: str, params: dict | None = None) -> dict | list:
        """
        Internal GET with retry + exponential backoff.

        Retries on:
        - Network timeouts
        - HTTP 429 (rate limited by CoinGecko)
        - HTTP 5xx (server errors)
        """
        url = f"{self.BASE_URL}{endpoint}"
        last_exc: Exception | None = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                    logger.info(
                        "CoinGecko request",
                        extra={"url": url, "attempt": attempt, "params": params},
                    )
                    response = await client.get(url, params=params)

                    if response.status_code == 429:
                        wait = self.BACKOFF ** attempt
                        logger.warning(
                            "CoinGecko rate limit hit, backing off",
                            extra={"wait_seconds": wait, "attempt": attempt},
                        )
                        await asyncio.sleep(wait)
                        continue

                    if response.status_code >= 500:
                        raise httpx.HTTPStatusError(
                            f"Server error {response.status_code}",
                            request=response.request,
                            response=response,
                        )

                    response.raise_for_status()
                    logger.info("CoinGecko success", extra={"url": url, "attempt": attempt})
                    return response.json()

            except httpx.TimeoutException as exc:
                wait = self.BACKOFF ** attempt
                logger.warning(
                    "CoinGecko timeout, retrying",
                    extra={"attempt": attempt, "wait_seconds": wait},
                )
                last_exc = exc
                await asyncio.sleep(wait)

            except httpx.HTTPStatusError as exc:
                wait = self.BACKOFF ** attempt
                logger.warning(
                    "CoinGecko HTTP error, retrying",
                    extra={"status": exc.response.status_code, "attempt": attempt},
                )
                last_exc = exc
                await asyncio.sleep(wait)

            except httpx.RequestError as exc:
                last_exc = exc
                break  # Network-level error — don't retry indefinitely

        logger.error(
            "CoinGecko all retries exhausted",
            extra={"url": url, "error": str(last_exc)},
        )
        raise ExternalAPIException("CoinGecko", str(last_exc))

    async def get_prices(self, coin_ids: list[str]) -> list[CoinPrice]:
        """
        Fetch current USD prices for a list of CoinGecko coin IDs.

        Args:
            coin_ids: e.g. ["bitcoin", "ethereum", "solana"]

        Returns:
            List of CoinPrice objects with price, market cap, and 24h change.
        """
        if not coin_ids:
            return []

        ids_param = ",".join(coin_ids)
        data = await self._get(
            "/coins/markets",
            params={
                "vs_currency": "usd",
                "ids": ids_param,
                "order": "market_cap_desc",
                "per_page": len(coin_ids),
                "page": 1,
                "sparkline": False,
                "price_change_percentage": "24h",
            },
        )

        prices = []
        for coin in data:
            prices.append(
                CoinPrice(
                    coin_id=coin["id"],
                    symbol=coin["symbol"].upper(),
                    name=coin["name"],
                    current_price_usd=coin.get("current_price", 0.0),
                    market_cap_usd=coin.get("market_cap"),
                    price_change_24h_pct=coin.get("price_change_percentage_24h"),
                    last_updated=coin.get("last_updated", ""),
                )
            )
        return prices

    async def search_coins(self, query: str) -> list[dict]:
        """Search CoinGecko for coins matching a query string."""
        data = await self._get("/search", params={"query": query})
        return [
            {"id": c["id"], "name": c["name"], "symbol": c["symbol"].upper()}
            for c in data.get("coins", [])[:10]  # return top 10 matches
        ]


# Singleton instance — reuse across requests
coingecko_service = CoinGeckoService()
