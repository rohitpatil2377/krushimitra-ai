"""Mandi price tests.

The thing worth guarding is not that an HTTP call works — it is that the board is ranked by what
the farmer NETS, that a trend is never invented from one data point, and that the notes never
turn into a sell/hold prediction we cannot make.
"""
import json
from datetime import date, timedelta


from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services.market.advice import build_notes, build_quotes  # noqa: E402
from app.services.market.agmarknet import (  # noqa: E402
    COMMODITY_NAMES,
    _filter_params,
    _parse_date,
    _price,
)
from app.services.market.base import MarketPrice, PriceBoard  # noqa: E402
from app.services.market.districts import INTRA_DISTRICT_KM, resolve, road_km  # noqa: E402
from app.services.market.history import load, record, trend_for  # noqa: E402
from app.services.market.names import market_mr  # noqa: E402

client = TestClient(app)
NASHIK = (19.9975, 73.7898)


def _price_row(market, district, modal, **kw):
    d = resolve(district)
    return MarketPrice(
        market=market,
        district_slug=d.slug if d else None,
        district_name=d.en if d else district,
        commodity=kw.get("commodity", "onion"),
        arrival_date=kw.get("arrival_date", date.today().isoformat()),
        min_price=kw.get("min_price", modal - 100),
        max_price=kw.get("max_price", modal + 100),
        modal_price=modal,
        variety=kw.get("variety"),
        grade=kw.get("grade"),
    )


# --- districts and distance --------------------------------------------------------------------

def test_pre_rename_district_names_still_resolve():
    """The API still emits old spellings; an unmatched name would silently drop a mandi."""
    for raw, slug in [
        ("Nasik", "nashik"), ("Ahmednagar", "ahilyanagar"), ("Ahmadnagar", "ahilyanagar"),
        ("Aurangabad", "chh_sambhajinagar"), ("Osmanabad", "dharashiv"),
        ("Buldana", "buldhana"), ("Mumbai Suburban", "mumbai"),
        ("Chandrapur(Chanda)", "chandrapur"),
    ]:
        got = resolve(raw)
        assert got is not None and got.slug == slug, raw


def test_unknown_district_is_none_not_a_guess():
    assert resolve("Narnia") is None
    assert resolve(None) is None
    assert resolve("") is None


def test_in_district_mandi_is_not_free_to_reach():
    """Straight-line distance to your own district town is ~0, which would imply free transport."""
    assert road_km(*NASHIK, resolve("Nashik")) == INTRA_DISTRICT_KM


def test_distance_grows_with_real_separation():
    near = road_km(*NASHIK, resolve("Ahilyanagar"))
    far = road_km(*NASHIK, resolve("Nagpur"))
    assert near is not None and far is not None and far > near > INTRA_DISTRICT_KM


def test_unknown_district_has_no_distance():
    assert road_km(*NASHIK, None) is None


# --- mandi names -------------------------------------------------------------------------------

def test_known_mandis_get_marathi_names():
    assert market_mr("Lasalgaon") == "लासलगाव"
    assert market_mr("pimpalgaon baswant") == "पिंपळगाव बसवंत"


def test_agmarknet_qualifiers_are_stripped_before_lookup():
    assert market_mr("Yeola(Andersul)") == "येवला"


def test_unknown_mandi_is_left_in_english_not_transliterated():
    """A wrong auto-transliteration of a place name reads as nonsense and costs trust."""
    assert market_mr("Somewhere New") is None


# --- net realisation: the whole point of the screen --------------------------------------------

def test_board_is_ranked_by_net_not_by_headline_price():
    """A mandi paying more, far away, can net less once the lorry is paid."""
    board = PriceBoard(crop="onion", prices=[
        _price_row("Yeola", "Nashik", 1500),          # 15 km
        _price_row("Nagpur", "Nagpur", 1800),         # ~700 km
    ], source="test")
    quotes = build_quotes(board, *NASHIK, transport_rate=0.6)
    assert quotes[0].market == "Yeola"
    assert quotes[0].is_best is True
    # The far mandi's headline is higher but its net is lower.
    far = next(q for q in quotes if q.market == "Nagpur")
    assert far.modal_price > quotes[0].modal_price
    assert far.net_price < quotes[0].net_price


def test_the_note_explains_why_the_cheaper_looking_mandi_wins():
    board = PriceBoard(crop="onion", prices=[
        _price_row("Yeola", "Nashik", 1500),
        _price_row("Nagpur", "Nagpur", 1800),
    ], source="test")
    quotes = build_quotes(board, *NASHIK, transport_rate=0.6)
    joined = " ".join(build_notes(quotes, "onion", 0.6))
    assert "येवला" in joined and "नागपूर" in joined
    assert "वाहतुकीचा खर्च" in joined


def test_transport_rate_changes_the_ranking():
    board = PriceBoard(crop="onion", prices=[
        _price_row("Yeola", "Nashik", 1500),
        _price_row("Pune", "Pune", 1700),
    ], source="test")
    free = build_quotes(board, *NASHIK, transport_rate=0.0)
    costly = build_quotes(board, *NASHIK, transport_rate=1.5)
    assert free[0].market == "Pune"      # with no haulage cost, take the higher price
    assert costly[0].market == "Yeola"   # once haulage is dear, stay local


def test_max_distance_hides_unreachable_mandis():
    board = PriceBoard(crop="onion", prices=[
        _price_row("Yeola", "Nashik", 1500),
        _price_row("Nagpur", "Nagpur", 1800),
    ], source="test")
    quotes = build_quotes(board, *NASHIK, transport_rate=0.6, max_distance_km=100)
    assert [q.market for q in quotes] == ["Yeola"]


def test_unknown_distance_quotes_gross_rather_than_inventing_haulage():
    board = PriceBoard(crop="onion", prices=[_price_row("Mystery", "Narnia", 1500)], source="test")
    q = build_quotes(board, *NASHIK, transport_rate=0.6)[0]
    assert q.distance_km is None
    assert q.transport_cost is None
    assert q.net_price == q.modal_price


def test_stale_prices_are_called_out():
    old = (date.today() - timedelta(days=5)).isoformat()
    board = PriceBoard(crop="onion", prices=[
        _price_row("Yeola", "Nashik", 1500, arrival_date=old),
    ], source="test")
    quotes = build_quotes(board, *NASHIK, transport_rate=0.6)
    assert quotes[0].age_days == 5
    assert any("दिवस जुने" in n for n in build_notes(quotes, "onion", 0.6))


# --- trend: never from one data point ----------------------------------------------------------

def test_trend_is_unknown_without_history():
    assert trend_for({}, "Yeola", 1500).direction == "unknown"


def test_trend_reads_up_down_and_flat():
    history = {"Yeola": {"2026-11-14": 1000.0}}
    assert trend_for(history, "Yeola", 1200).direction == "up"
    assert trend_for(history, "Yeola", 800).direction == "down"
    assert trend_for(history, "Yeola", 1010).direction == "flat"   # 1% is noise, not a trend


def test_notes_say_the_trend_is_unknown_rather_than_guessing():
    board = PriceBoard(crop="onion", prices=[_price_row("Yeola", "Nashik", 1500)], source="test")
    quotes = build_quotes(board, *NASHIK, transport_rate=0.6)
    assert any("कल सांगण्यासाठी पुरेशी जुनी माहिती" in n for n in build_notes(quotes, "onion", 0.6))


def test_notes_never_predict_a_future_price():
    """We cannot forecast a mandi. A confident sell/hold call is the same failure as a wrong
    diagnosis, so the wording must stay factual."""
    board = PriceBoard(crop="onion", prices=[
        _price_row("Yeola", "Nashik", 1500),
        _price_row("Pune", "Pune", 1700),
    ], source="test")
    joined = " ".join(build_notes(build_quotes(board, *NASHIK, transport_rate=0.6), "onion", 0.6))
    for banned in ("भाव वाढेल", "भाव घटेल", "आता विका", "थांबा आणि विका", "विकू नका"):
        assert banned not in joined, f"must not predict: {banned}"
    # and it must always send them to confirm before loading a vehicle
    assert "फोन करून" in joined


# --- history ------------------------------------------------------------------------------------

def test_sample_prices_never_enter_the_real_history(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "market_history_dir", str(tmp_path))
    board = PriceBoard(crop="onion", prices=[_price_row("Yeola", "Nashik", 1500)], source="mock-0")
    assert record(board) == 0
    assert load("onion") == {}


def test_history_appends_and_deduplicates(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "market_history_dir", str(tmp_path))
    board = PriceBoard(crop="onion", prices=[
        _price_row("Yeola", "Nashik", 1500),
        _price_row("Pune", "Pune", 1700),
    ], source="agmarknet")
    assert record(board) == 2
    assert record(board) == 0, "refreshing the screen must not inflate the series"
    history = load("onion")
    assert set(history) == {"Yeola", "Pune"}


def test_history_survives_a_corrupt_line(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "market_history_dir", str(tmp_path))
    path = tmp_path / "onion.jsonl"
    path.write_text(
        json.dumps({"date": "2026-11-14", "market": "Yeola", "modal": 1400}) + "\n"
        + "{ this is not json\n"
        + json.dumps({"date": "2026-11-15", "market": "Yeola", "modal": 1500}) + "\n",
        encoding="utf-8",
    )
    assert sorted(load("onion")["Yeola"]) == ["2026-11-14", "2026-11-15"]


def test_trend_becomes_available_once_history_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "market_history_dir", str(tmp_path))
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    record(PriceBoard(crop="onion", prices=[
        _price_row("Yeola", "Nashik", 1200, arrival_date=yesterday),
    ], source="agmarknet"))
    board = PriceBoard(crop="onion", prices=[_price_row("Yeola", "Nashik", 1500)], source="test")
    q = build_quotes(board, *NASHIK, transport_rate=0.6)[0]
    assert q.trend == "up"
    assert q.trend_change_pct == 25.0
    assert q.previous_price == 1200


# --- Agmarknet payload handling ----------------------------------------------------------------

def test_commodity_names_use_agmarknets_own_spellings():
    """Agmarknet lists soybean as 'Soyabean'. Guessing 'Soybean' alone returns nothing."""
    assert COMMODITY_NAMES["soybean"][0] == "Soyabean"
    assert "Soybean" in COMMODITY_NAMES["soybean"]


def test_filter_key_styles_cover_the_documented_variants():
    """The parameter spelling is inconsistent across clients, so we try each form."""
    assert _filter_params("{field}", state="Maharashtra") == {"filters[state]": "Maharashtra"}
    assert _filter_params("{field}.keyword", state="X") == {"filters[state.keyword]": "X"}
    assert _filter_params("{field_title}", state="X") == {"filters[State]": "X"}


def test_arrival_date_parses_agmarknets_formats():
    assert _parse_date("16/11/2026") == "2026-11-16"
    assert _parse_date("2026-11-16") == "2026-11-16"
    assert _parse_date("16-11-2026") == "2026-11-16"
    assert _parse_date("rubbish") == date.today().isoformat()
    assert _parse_date(None) == date.today().isoformat()


def test_zero_price_is_missing_data_not_a_free_crop():
    assert _price(0) is None
    assert _price("0") is None
    assert _price("") is None
    assert _price(None) is None
    assert _price("1,450") == 1450.0


# --- endpoint ----------------------------------------------------------------------------------

def test_endpoint_returns_a_ranked_board_badged_as_sample():
    r = client.get("/market/prices", params={"lat": NASHIK[0], "lon": NASHIK[1], "crop": "onion"})
    assert r.status_code == 200
    body = r.json()
    assert body["source"].startswith("mock")
    assert body["price_unit"] == "rs_per_quintal"
    assert body["quotes"] and body["notes"]
    nets = [q["net_price"] for q in body["quotes"]]
    assert nets == sorted(nets, reverse=True)
    assert body["quotes"][0]["is_best"] is True


def test_endpoint_rejects_an_unsupported_crop():
    r = client.get("/market/prices", params={"lat": NASHIK[0], "lon": NASHIK[1], "crop": "wheat"})
    assert r.status_code == 422
    assert "onion" in r.json()["detail"]


def test_endpoint_honours_a_farmers_own_transport_rate():
    params = {"lat": NASHIK[0], "lon": NASHIK[1], "crop": "onion", "transport_rate": 2.5}
    body = client.get("/market/prices", params=params).json()
    assert body["transport_rate_per_qtl_km"] == 2.5
    far = [q for q in body["quotes"] if (q["distance_km"] or 0) > 200]
    for q in far:
        assert q["transport_cost"] > q["distance_km"] * 2.0
