"""Shapes every mandi-price provider returns.

Prices across Agmarknet are **rupees per quintal** (100 kg). That unit is fixed here rather than
carried per record, because a silent unit mix-up between quintal and kg is a factor-of-100 error
in the one number a farmer will act on.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

PRICE_UNIT = "rs_per_quintal"


@dataclass
class MarketPrice:
    market: str                   # the mandi, e.g. "Lasalgaon"
    district_slug: str | None     # canonical slug, or None when we could not resolve the name
    district_name: str            # as reported, for display
    commodity: str
    arrival_date: str             # yyyy-mm-dd
    min_price: float
    max_price: float
    modal_price: float            # the one to quote: the price most lots actually fetched
    variety: str | None = None
    grade: str | None = None


@dataclass
class PriceBoard:
    crop: str
    prices: list[MarketPrice] = field(default_factory=list)
    # "agmarknet" for a real call; anything starting with "mock" is sample data and gets badged.
    source: str = "mock-0"


class MarketError(RuntimeError):
    """Provider unreachable or refused. The API layer degrades to a labelled mock."""


class MarketService(Protocol):
    async def prices(self, crop: str, state: str = "Maharashtra") -> PriceBoard: ...
