"""
API v1 router — assembles all endpoint modules under /api/v1
"""
from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, market, watchlists

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(watchlists.router)
api_router.include_router(market.router)
api_router.include_router(admin.router)
