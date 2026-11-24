"""Our own price history — because the source API has none.

data.gov.in serves only the CURRENT day: there is nothing to query for last week, and no way to
backfill. So every board we fetch is appended here, and a trend becomes available once we hold two
distinct days for a market. Before that the honest answer is "unknown", not a direction inferred
from one data point.

This is the same moat logic as the photo captures: the data nobody can hand us later starts
accumulating from the first farmer.

Storage: data/market/<crop>.jsonl, one JSON object per (date, market). Appends are deduplicated,
so refreshing the screen all day does not inflate the file or skew a trend.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.services.market.base import PriceBoard

log = logging.getLogger(__name__)

# Below this the day-to-day wobble of a mandi board is noise, not a trend.
FLAT_BAND_PCT = 2.0


@dataclass(frozen=True)
class Trend:
    direction: str            # up | down | flat | unknown
    change_pct: float | None  # vs the previous day we hold
    days_of_history: int
    previous_price: float | None = None


def _path(crop: str) -> Path:
    return Path(settings.market_history_dir) / f"{crop.lower()}.jsonl"


def load(crop: str) -> dict[str, dict[str, float]]:
    """{market: {date: modal_price}} from whatever we have on disk."""
    path = _path(crop)
    if not path.exists():
        return {}
    out: dict[str, dict[str, float]] = {}
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    out.setdefault(row["market"], {})[row["date"]] = float(row["modal"])
                except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                    continue  # a half-written line must not take the whole history down
    except OSError as exc:
        log.warning("[market] could not read history for %s: %s", crop, exc)
    return out


def record(board: PriceBoard) -> int:
    """Append today's board. Returns rows written. Never raises — a farmer is waiting on this."""
    if not settings.market_history_enabled or not board.prices:
        return 0
    # Sample prices must never contaminate the real series we will later chart or train on.
    if board.source.startswith("mock"):
        return 0

    existing = load(board.crop)
    path = _path(board.crop)
    written = 0
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            for price in board.prices:
                if existing.get(price.market, {}).get(price.arrival_date) is not None:
                    continue  # already have this market for this day
                fh.write(json.dumps({
                    "date": price.arrival_date,
                    "market": price.market,
                    "district": price.district_slug,
                    "modal": price.modal_price,
                    "min": price.min_price,
                    "max": price.max_price,
                    "variety": price.variety,
                }, ensure_ascii=False) + "\n")
                written += 1
    except OSError as exc:
        log.warning("[market] could not append history for %s: %s", board.crop, exc)
    return written


def trend_for(history: dict[str, dict[str, float]], market: str, today_price: float) -> Trend:
    """Direction for one market, from the most recent earlier day we hold."""
    series = history.get(market) or {}
    earlier = sorted(d for d in series if series[d] > 0)
    if not earlier:
        return Trend("unknown", None, 0)

    # The most recent day that is not the one we are comparing.
    previous_date = earlier[-1]
    previous = series[previous_date]
    if previous <= 0:
        return Trend("unknown", None, len(earlier))

    change = (today_price - previous) / previous * 100
    if abs(change) < FLAT_BAND_PCT:
        direction = "flat"
    else:
        direction = "up" if change > 0 else "down"
    return Trend(direction, round(change, 1), len(earlier), previous)


def stats() -> dict:
    """How much price history we have accumulated — the moat, as a number."""
    root = Path(settings.market_history_dir)
    if not root.exists():
        return {"crops": 0, "rows": 0, "days": 0}
    rows = 0
    days: set[str] = set()
    crops = 0
    for path in root.glob("*.jsonl"):
        crops += 1
        try:
            with path.open(encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    rows += 1
                    try:
                        days.add(json.loads(line)["date"])
                    except (json.JSONDecodeError, KeyError):
                        continue
        except OSError:
            continue
    return {"crops": crops, "rows": rows, "days": len(days)}
