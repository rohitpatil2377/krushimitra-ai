"""Mandi prices: data.gov.in/Agmarknet behind a swappable interface, with net-realisation ranking."""
from app.core.config import settings
from app.services.market.base import (
    PRICE_UNIT,
    MarketError,
    MarketPrice,
    MarketService,
    PriceBoard,
)
from app.services.market.mock import MOCK_SOURCE, MockMarketService

__all__ = [
    "MOCK_SOURCE",
    "PRICE_UNIT",
    "MarketError",
    "MarketPrice",
    "MarketService",
    "MockMarketService",
    "PriceBoard",
    "get_market_service",
]


def get_market_service() -> MarketService:
    if settings.market_live:
        from app.services.market.agmarknet import AgmarknetService

        return AgmarknetService()
    return MockMarketService()
