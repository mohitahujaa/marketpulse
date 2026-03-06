"""
Tests for watchlist CRUD endpoints.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.schemas.watchlist import CoinPrice


@pytest.mark.asyncio
class TestWatchlistCRUD:
    async def test_create_watchlist(self, client: AsyncClient, user_token: str):
        response = await client.post(
            "/api/v1/watchlists",
            json={"name": "My Crypto", "description": "Top picks"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["name"] == "My Crypto"
        assert data["items"] == []

    async def test_list_watchlists(self, client: AsyncClient, user_token: str):
        await client.post(
            "/api/v1/watchlists",
            json={"name": "List 1"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        response = await client.get(
            "/api/v1/watchlists",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        assert len(response.json()["data"]) == 1

    async def test_update_watchlist(self, client: AsyncClient, user_token: str):
        create_resp = await client.post(
            "/api/v1/watchlists",
            json={"name": "Original"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        wl_id = create_resp.json()["data"]["id"]

        response = await client.patch(
            f"/api/v1/watchlists/{wl_id}",
            json={"name": "Updated"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Updated"

    async def test_delete_watchlist(self, client: AsyncClient, user_token: str):
        create_resp = await client.post(
            "/api/v1/watchlists",
            json={"name": "ToDelete"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        wl_id = create_resp.json()["data"]["id"]

        response = await client.delete(
            f"/api/v1/watchlists/{wl_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200

        # Verify it's gone
        get_resp = await client.get(
            f"/api/v1/watchlists/{wl_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert get_resp.status_code == 404

    async def test_cannot_access_other_user_watchlist(
        self, client: AsyncClient, user_token: str
    ):
        # Create watchlist as user1
        create_resp = await client.post(
            "/api/v1/watchlists",
            json={"name": "Private"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        wl_id = create_resp.json()["data"]["id"]

        # Register and login as user2
        await client.post("/api/v1/auth/register", json={
            "email": "user2@test.com", "username": "user2", "password": "Password1"
        })
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "user2@test.com", "password": "Password1"
        })
        token2 = login_resp.json()["data"]["access_token"]

        response = await client.get(
            f"/api/v1/watchlists/{wl_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestWatchlistCoins:
    async def _create_watchlist(self, client, token) -> str:
        resp = await client.post(
            "/api/v1/watchlists",
            json={"name": "Coins Test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        return resp.json()["data"]["id"]

    async def test_add_coin(self, client: AsyncClient, user_token: str):
        wl_id = await self._create_watchlist(client, user_token)
        response = await client.post(
            f"/api/v1/watchlists/{wl_id}/coins",
            json={"coin_id": "bitcoin", "symbol": "BTC"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 201
        assert response.json()["data"]["coin_id"] == "bitcoin"

    async def test_add_duplicate_coin(self, client: AsyncClient, user_token: str):
        wl_id = await self._create_watchlist(client, user_token)
        await client.post(
            f"/api/v1/watchlists/{wl_id}/coins",
            json={"coin_id": "bitcoin", "symbol": "BTC"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        response = await client.post(
            f"/api/v1/watchlists/{wl_id}/coins",
            json={"coin_id": "bitcoin", "symbol": "BTC"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 409

    async def test_get_prices_mocked(self, client: AsyncClient, user_token: str):
        wl_id = await self._create_watchlist(client, user_token)
        await client.post(
            f"/api/v1/watchlists/{wl_id}/coins",
            json={"coin_id": "bitcoin", "symbol": "BTC"},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        mock_price = CoinPrice(
            coin_id="bitcoin",
            symbol="BTC",
            name="Bitcoin",
            current_price_usd=65000.0,
            market_cap_usd=1_200_000_000_000.0,
            price_change_24h_pct=2.5,
            last_updated="2024-01-01T00:00:00Z",
        )

        with patch(
            "app.services.coingecko.CoinGeckoService.get_prices",
            new_callable=AsyncMock,
            return_value=[mock_price],
        ):
            response = await client.get(
                f"/api/v1/watchlists/{wl_id}/prices",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        assert response.status_code == 200
        prices = response.json()["data"]["prices"]
        assert len(prices) == 1
        assert prices[0]["current_price_usd"] == 65000.0
