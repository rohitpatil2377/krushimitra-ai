"""Net realisation and the Marathi guidance — the part that makes this more than a price table.

A price table answers "what is the rate". The farmer's actual question is "which market do I take
the tractor to", and the two answers differ: a mandi paying Rs 200/quintal more, 200 km away, nets
LESS once the lorry is paid. So every quote carries distance, transport cost and a net price, and
the board is ranked by net.

What this module deliberately does NOT do is tell a farmer to sell or to hold. We cannot predict
tomorrow's mandi price, and a confident "sell now" that costs someone their crop's value is the
same failure as a wrong disease diagnosis. The notes state what is known - the spread, the trend
against days we actually hold, how old the data is - and always send the farmer to confirm by
phone before loading a vehicle.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.services.market.base import MarketPrice, PriceBoard
from app.services.market.districts import resolve, road_km
from app.services.market.history import Trend, load, trend_for
from app.services.market.names import market_mr

_DEV_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")

# Data older than this is reported with a warning: mandi rates move day to day.
STALE_AFTER_DAYS = 2
# A spread smaller than this is not worth a journey.
NOTABLE_SPREAD_RS = 100.0


def _n(value: float | int, decimals: int = 0) -> str:
    return f"{value:.{decimals}f}".translate(_DEV_DIGITS)


@dataclass
class MarketQuote:
    market: str
    district_name: str
    # Marathi names where we know the place; None falls back to the English name in the app.
    market_mr: str | None
    district_mr: str | None
    commodity: str
    arrival_date: str
    age_days: int
    min_price: float
    max_price: float
    modal_price: float
    distance_km: float | None
    transport_cost: float | None      # rupees per quintal
    net_price: float                  # modal minus transport
    trend: str                        # up | down | flat | unknown
    trend_change_pct: float | None
    previous_price: float | None
    variety: str | None = None
    grade: str | None = None
    is_best: bool = False


def _age_days(arrival: str) -> int:
    try:
        then = datetime.strptime(arrival, "%Y-%m-%d").date()
    except ValueError:
        return 0
    return max(0, (date.today() - then).days)


def build_quotes(
    board: PriceBoard,
    lat: float,
    lon: float,
    *,
    transport_rate: float,
    max_distance_km: float | None = None,
) -> list[MarketQuote]:
    """Enrich each price with distance, transport and trend, then rank by NET realisation."""
    history = load(board.crop)
    quotes: list[MarketQuote] = []

    for price in board.prices:
        district = resolve(price.district_slug or price.district_name)
        distance = road_km(lat, lon, district)
        if max_distance_km is not None and distance is not None and distance > max_distance_km:
            continue

        transport = round(distance * transport_rate, 0) if distance is not None else None
        trend: Trend = trend_for(history, price.market, price.modal_price)

        quotes.append(MarketQuote(
            market=price.market,
            district_name=price.district_name,
            market_mr=market_mr(price.market),
            district_mr=district.mr if district else None,
            commodity=price.commodity,
            arrival_date=price.arrival_date,
            age_days=_age_days(price.arrival_date),
            min_price=price.min_price,
            max_price=price.max_price,
            modal_price=price.modal_price,
            distance_km=distance,
            transport_cost=transport,
            # Unknown distance => quote the gross price rather than inventing a haulage cost.
            net_price=round(price.modal_price - (transport or 0.0), 0),
            trend=trend.direction,
            trend_change_pct=trend.change_pct,
            previous_price=trend.previous_price,
            variety=price.variety,
            grade=price.grade,
        ))

    quotes.sort(key=lambda q: q.net_price, reverse=True)
    if quotes:
        quotes[0].is_best = True
    return quotes


def build_notes(quotes: list[MarketQuote], crop: str, transport_rate: float) -> list[str]:
    """Marathi guidance. States what is known; never predicts a price."""
    if not quotes:
        return [
            "या पिकासाठी आजचे भाव मिळाले नाहीत. बाजार समिती बंद असू शकते, किंवा आजची नोंद "
            "अजून प्रसिद्ध झालेली नाही. उद्या पुन्हा पाहा."
        ]

    out: list[str] = []
    best = quotes[0]

    def name(q: MarketQuote) -> str:
        return q.market_mr or q.market

    if best.transport_cost is not None:
        out.append(
            f"वाहतूक वजा करून सर्वात चांगला भाव {name(best)} येथे — सुमारे "
            f"₹{_n(best.net_price)} प्रति क्विंटल ({_n(best.distance_km or 0)} किमी, "
            f"वाहतूक ₹{_n(best.transport_cost)})."
        )
    else:
        out.append(
            f"आजचा सर्वात जास्त भाव {name(best)} येथे — सुमारे ₹{_n(best.modal_price)} प्रति क्विंटल."
        )

    # The whole point of ranking by net: the highest-paying mandi is often not the best one.
    by_gross = max(quotes, key=lambda q: q.modal_price)
    if by_gross.market != best.market:
        gross_gap = by_gross.modal_price - best.modal_price
        net_gap = best.net_price - by_gross.net_price
        out.append(
            f"{name(by_gross)} मध्ये भाव ₹{_n(gross_gap)} जास्त दिसतो, पण "
            f"{_n(by_gross.distance_km or 0)} किमी वाहतुकीचा खर्च वजा केल्यावर {name(best)} "
            f"मध्येच ₹{_n(net_gap)} जास्त मिळतात."
        )

    spread = best.net_price - min(q.net_price for q in quotes)
    if spread >= NOTABLE_SPREAD_RS:
        out.append(
            f"आजच्या बाजारांमध्ये निव्वळ भावात ₹{_n(spread)} प्रति क्विंटल फरक आहे — "
            "कुठे विकायचे हे ठरवल्याने खरोखर फरक पडतो."
        )

    known = [q for q in quotes if q.trend in ("up", "down") and q.trend_change_pct is not None]
    if known:
        q = max(known, key=lambda x: abs(x.trend_change_pct or 0))
        word = "वाढला" if q.trend == "up" else "घटला"
        out.append(
            f"{name(q)} मध्ये मागच्या नोंदीच्या तुलनेत भाव {_n(abs(q.trend_change_pct or 0), 1)}% "
            f"{word} आहे. हा कल पुढेही राहील असे सांगता येत नाही."
        )
    else:
        out.append(
            "भावाचा कल सांगण्यासाठी पुरेशी जुनी माहिती अजून नाही. आम्ही रोजचे भाव साठवत आहोत — "
            "काही दिवसांत कल दिसू लागेल."
        )

    oldest = max(q.age_days for q in quotes)
    if oldest > STALE_AFTER_DAYS:
        out.append(
            f"हे भाव सुमारे {_n(oldest)} दिवस जुने आहेत. बाजार समिती रोज नोंद प्रसिद्ध करत "
            "नसल्यास असे होते."
        )

    out.append(
        f"वाहतूक खर्च ₹{_n(transport_rate, 2)} प्रति क्विंटल प्रति किमी या दराने धरला आहे. "
        "तुमचा दर वेगळा असेल तर प्रत्यक्ष हिशोब बदलेल."
    )
    out.append(
        "भाव प्रतवारी, आकार आणि आवकेनुसार बदलतो. गाडी भरण्यापूर्वी बाजार समितीत फोन करून "
        "आजचा भाव आणि आवक विचारून खात्री करा."
    )
    return out
