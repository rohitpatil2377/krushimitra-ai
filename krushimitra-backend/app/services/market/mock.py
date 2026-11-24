"""Sample mandi prices, so the whole feature works with zero keys.

Uses REAL Maharashtra mandis and realistic price bands rather than round numbers, because the
screen's whole job is comparing markets — a mock where every mandi quotes the same rate would
never exercise the net-realisation logic and we would ship it untested.

Seeded by crop and date, so a farmer refreshing twice sees the same board.
MOCK_SOURCE starts with "mock": that prefix is the contract the app badges on.
"""
from __future__ import annotations

import random
from datetime import date

from app.services.market.base import MarketPrice, PriceBoard
from app.services.market.districts import resolve

MOCK_SOURCE = "mock-0"

# (mandi, district) — the mandis that actually set the price for each crop in Maharashtra.
_MANDIS: dict[str, tuple[tuple[str, str], ...]] = {
    "onion": (
        ("Lasalgaon", "Nashik"), ("Pimpalgaon Baswant", "Nashik"), ("Yeola", "Nashik"),
        ("Solapur", "Solapur"), ("Pune", "Pune"), ("Rahuri", "Ahilyanagar"),
        ("Dhule", "Dhule"), ("Chh. Sambhajinagar", "Chh. Sambhajinagar"),
    ),
    "soybean": (
        ("Latur", "Latur"), ("Nanded", "Nanded"), ("Akola", "Akola"),
        ("Amravati", "Amravati"), ("Washim", "Washim"), ("Jalna", "Jalna"),
        ("Hingoli", "Hingoli"), ("Nagpur", "Nagpur"),
    ),
    "pomegranate": (
        ("Sangola", "Solapur"), ("Pune", "Pune"), ("Nashik", "Nashik"),
        ("Sangli", "Sangli"), ("Rahuri", "Ahilyanagar"), ("Solapur", "Solapur"),
    ),
}

# Indicative modal price bands, rupees per quintal. Onion is genuinely this volatile.
_BANDS: dict[str, tuple[int, int]] = {
    "onion": (900, 2300),
    "soybean": (4100, 5100),
    "pomegranate": (4500, 11000),
}

_VARIETIES = {
    "onion": ("Local", "Red", "Pole"),
    "soybean": ("Local", "Yellow"),
    "pomegranate": ("Bhagwa", "Ganesh", "Arakta"),
}


class MockMarketService:
    """Never fails and never pretends to be real."""

    async def prices(self, crop: str, state: str = "Maharashtra") -> PriceBoard:
        slug = (crop or "").lower()
        mandis = _MANDIS.get(slug)
        if not mandis:
            return PriceBoard(crop=slug, prices=[], source=MOCK_SOURCE)

        today = date.today()
        lo_band, hi_band = _BANDS[slug]
        rng = random.Random(hash((slug, today.toordinal())) & 0xFFFFFFFF)
        centre = rng.uniform(lo_band + (hi_band - lo_band) * 0.25,
                             lo_band + (hi_band - lo_band) * 0.6)

        prices: list[MarketPrice] = []
        for market, district_name in mandis:
            # Real boards show a spread of roughly +/-12% between mandis on the same day.
            modal = centre * rng.uniform(0.88, 1.12)
            spread = modal * rng.uniform(0.08, 0.22)
            district = resolve(district_name)
            prices.append(MarketPrice(
                market=market,
                district_slug=district.slug if district else None,
                district_name=district.en if district else district_name,
                commodity=slug,
                arrival_date=today.isoformat(),
                min_price=round(max(lo_band * 0.6, modal - spread), -1),
                max_price=round(modal + spread, -1),
                modal_price=round(modal, -1),
                variety=rng.choice(_VARIETIES[slug]),
                grade="FAQ",
            ))

        return PriceBoard(crop=slug, prices=prices, source=MOCK_SOURCE)
