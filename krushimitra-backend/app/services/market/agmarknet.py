"""data.gov.in / Agmarknet adapter for daily mandi prices.

Resource `9ef84268-d588-465a-a308-a864a43d0070` ("Current Daily Price of Various Commodities from
Various Markets"). Two things about this API shaped the code:

1. **The filter parameter spelling is not documented consistently.** Third-party clients variously
   use `filters[state]`, `filters[state.keyword]` and `filters[State]`, and the only way to know is
   to call it. So we try each form in turn and keep the one that returns rows, instead of guessing
   one and shipping a feature that silently returns nothing.

2. **It serves only the current day.** There is no history to query, which is why trends come from
   our own accumulated snapshots (`history.py`) and why a brand-new install honestly reports
   "trend unknown" rather than inventing a direction.

Also: Agmarknet's commodity spellings are its own — soybean is listed as **"Soyabean"**. We try a
list of candidate names per crop for the same reason as the filter keys.
"""
from __future__ import annotations

import logging
from datetime import date, datetime

import httpx

from app.core.config import settings
from app.services.market.base import MarketError, MarketPrice, PriceBoard
from app.services.market.districts import resolve

log = logging.getLogger(__name__)

RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
BASE = "https://api.data.gov.in/resource"
PAGE_LIMIT = 1000

# Agmarknet's own spellings, most likely first.
COMMODITY_NAMES: dict[str, tuple[str, ...]] = {
    "onion": ("Onion",),
    "soybean": ("Soyabean", "Soybean", "Soyabeen"),
    "pomegranate": ("Pomegranate", "Pomegranate(Anar)"),
}

# Filter key styles seen in the wild; tried in order until one returns rows.
_FILTER_STYLES = ("{field}", "{field}.keyword", "{field_title}")


def _filter_params(style: str, **fields: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for field, value in fields.items():
        key = style.format(field=field, field_title=field.title())
        out[f"filters[{key}]"] = value
    return out


def _parse_date(raw: str | None) -> str:
    """Agmarknet sends dd/mm/yyyy; some mirrors send yyyy-mm-dd. Accept both, else today."""
    if raw:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(raw.strip(), fmt).date().isoformat()
            except ValueError:
                continue
    return date.today().isoformat()


def _price(raw: object) -> float | None:
    try:
        value = float(str(raw).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    # Agmarknet uses 0 for "not reported". A zero price is missing data, not a free crop.
    return value if value > 0 else None


class AgmarknetService:
    def __init__(self, api_key: str | None = None, timeout_s: float | None = None) -> None:
        self.api_key = api_key or settings.datagov_api_key
        self.timeout_s = timeout_s or settings.market_timeout_s

    async def _fetch(self, client: httpx.AsyncClient, params: dict[str, str]) -> list[dict]:
        try:
            res = await client.get(f"{BASE}/{RESOURCE_ID}", params=params)
        except httpx.HTTPError as exc:
            raise MarketError(f"data.gov.in unreachable: {exc}") from exc
        if res.status_code in (401, 403):
            raise MarketError(f"data.gov.in rejected the API key ({res.status_code})")
        if res.status_code != 200:
            raise MarketError(f"data.gov.in returned {res.status_code}: {res.text[:200]}")
        try:
            payload = res.json()
        except ValueError as exc:
            raise MarketError("data.gov.in returned a non-JSON body") from exc
        records = payload.get("records")
        return records if isinstance(records, list) else []

    async def prices(self, crop: str, state: str = "Maharashtra") -> PriceBoard:
        if not self.api_key:
            raise MarketError("DATAGOV_API_KEY is not set")

        slug = (crop or "").lower()
        candidates = COMMODITY_NAMES.get(slug)
        if not candidates:
            raise MarketError(f"no Agmarknet commodity name mapped for crop '{crop}'")

        base_params = {
            "api-key": self.api_key,
            "format": "json",
            "limit": str(PAGE_LIMIT),
        }

        records: list[dict] = []
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            for style in _FILTER_STYLES:
                for commodity in candidates:
                    params = {
                        **base_params,
                        **_filter_params(style, state=state, commodity=commodity),
                    }
                    found = await self._fetch(client, params)
                    if found:
                        log.info(
                            "[market] agmarknet matched filter style %r commodity %r (%d rows)",
                            style, commodity, len(found),
                        )
                        records = found
                        break
                if records:
                    break

        prices: list[MarketPrice] = []
        for row in records:
            modal = _price(row.get("modal_price"))
            lo = _price(row.get("min_price"))
            hi = _price(row.get("max_price"))
            # Without a usable price the row tells the farmer nothing — drop it rather than
            # render a market with a blank or zero rate.
            if modal is None and lo is None and hi is None:
                continue
            modal = modal or hi or lo
            district_name = str(row.get("district") or "").strip()
            district = resolve(district_name)
            prices.append(MarketPrice(
                market=str(row.get("market") or "").strip() or district_name or "—",
                district_slug=district.slug if district else None,
                district_name=district.en if district else district_name,
                commodity=str(row.get("commodity") or crop).strip(),
                arrival_date=_parse_date(row.get("arrival_date")),
                min_price=lo or modal,
                max_price=hi or modal,
                modal_price=modal,
                variety=(str(row.get("variety")).strip() or None) if row.get("variety") else None,
                grade=(str(row.get("grade")).strip() or None) if row.get("grade") else None,
            ))

        return PriceBoard(crop=slug, prices=prices, source="agmarknet")
