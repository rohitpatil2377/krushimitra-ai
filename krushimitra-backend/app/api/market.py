"""Mandi price endpoints.

Composition: provider -> our own price history (trend) -> net realisation -> Marathi notes.

Same degradation contract as the rest: a provider failure serves a LABELLED mock rather than an
error screen, and `source` tells the app whether to badge it.
"""
import logging

from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.schemas.api import MarketPricesOut, MarketQuoteOut
from app.services.market import MockMarketService, get_market_service
from app.services.market.advice import build_notes, build_quotes
from app.services.market.base import PRICE_UNIT
from app.services.market.history import record, stats

log = logging.getLogger(__name__)
router = APIRouter(prefix="/market", tags=["market"])

SUPPORTED_CROPS = ("onion", "soybean", "pomegranate")


@router.get("/prices", response_model=MarketPricesOut)
async def prices(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    crop: str = Query(..., description=" | ".join(SUPPORTED_CROPS)),
    max_distance_km: float | None = Query(
        None, gt=0, le=2000, description="Hide mandis further than this"
    ),
    transport_rate: float | None = Query(
        None, ge=0, le=20, description="Rupees per quintal per km; farmer's own lorry rate"
    ),
    state: str = Query("Maharashtra"),
) -> MarketPricesOut:
    slug = (crop or "").lower()
    if slug not in SUPPORTED_CROPS:
        raise HTTPException(
            status_code=422,
            detail=f"unsupported crop '{crop}' — supported: " + ", ".join(SUPPORTED_CROPS),
        )

    try:
        board = await get_market_service().prices(slug, state=state)
    except Exception as exc:
        log.warning("[market] %s failed, serving mock: %s", settings.active_market_provider, exc)
        board = await MockMarketService().prices(slug, state=state)
        board.source = "mock-fallback"

    # Accumulate the series the source API cannot give us. Mock boards are skipped inside
    # record(), so sample data never contaminates the real history.
    record(board)

    rate = settings.transport_rate_per_qtl_km if transport_rate is None else transport_rate
    quotes = build_quotes(board, lat, lon, transport_rate=rate, max_distance_km=max_distance_km)

    return MarketPricesOut(
        crop=slug,
        price_unit=PRICE_UNIT,
        lat=lat,
        lon=lon,
        transport_rate_per_qtl_km=rate,
        quotes=[MarketQuoteOut(**vars(q)) for q in quotes],
        notes=build_notes(quotes, slug, rate),
        history_days=stats()["days"],
        source=board.source,
    )


@router.get("/history", response_model=dict, tags=["meta"])
async def history() -> dict:
    """How much price history we have accumulated — the moat the source API cannot sell us."""
    return {"provider": settings.active_market_provider, **stats()}
