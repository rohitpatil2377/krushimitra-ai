"""Irrigation tests.

Three layers worth guarding:
  * the physics (ET0 against published Maharashtra ranges — a silent sign error here would
    produce confident nonsense),
  * the FAO-56 coefficients and the method-dependent strategy,
  * the honesty rules: no last-watered day means "unsure", not a guess, and an unsupported crop
    is a 422 rather than an invented coefficient.
"""
from datetime import date, timedelta


from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.irrigation import (  # noqa: E402
    CROP_PARAMS,
    METHODS,
    SOILS,
    build_plan,
    effective_rain_mm,
    et0_hargreaves,
    extraterrestrial_radiation_mm,
    stage_for,
)
from app.services.weather.base import CurrentWeather, DayForecast, Forecast  # noqa: E402

client = TestClient(app)
NASHIK = (19.9975, 73.7898)


def _forecast(tmin=15.0, tmax=30.0, rain=0.0, chance=5, source="test", days=5):
    items = [
        DayForecast(
            date=(date.today() + timedelta(days=i)).isoformat(),
            temp_min_c=tmin, temp_max_c=tmax, humidity_pct=50,
            rain_mm=rain, rain_chance_pct=chance, wind_kph=8.0, condition="clear",
        )
        for i in range(days)
    ]
    return Forecast(
        current=CurrentWeather(
            temp_c=(tmin + tmax) / 2, feels_like_c=tmax, humidity_pct=50, wind_kph=8.0,
            rain_mm=0.0, condition="clear", observed_at="2026-11-16T06:00:00+00:00",
        ),
        days=items, source=source,
    )


# --- the physics -------------------------------------------------------------------------------

def test_et0_is_in_the_published_maharashtra_range():
    """Nashik ET0 runs ~3-4 mm/day in November and ~7-8 in May. A sign or unit error shows here."""
    nov = et0_hargreaves(15, 30, 19.99, date(2026, 11, 16))
    may = et0_hargreaves(24, 40, 19.99, date(2026, 5, 10))
    monsoon = et0_hargreaves(22, 28, 19.99, date(2026, 7, 20))
    assert 3.0 <= nov <= 5.0, nov
    assert 6.0 <= may <= 9.0, may
    assert monsoon < nov, "overcast monsoon days must demand less water than clear November ones"


def test_et0_rises_with_a_wider_daily_swing():
    """The Tmax-Tmin term is standing in for solar radiation; clear skies must mean more ET."""
    narrow = et0_hargreaves(24, 28, 19.99, date(2026, 3, 1))
    wide = et0_hargreaves(18, 38, 19.99, date(2026, 3, 1))
    assert wide > narrow


def test_extraterrestrial_radiation_peaks_near_the_summer_solstice():
    may = extraterrestrial_radiation_mm(19.99, date(2026, 5, 10))
    dec = extraterrestrial_radiation_mm(19.99, date(2026, 12, 21))
    assert may > dec


def test_et0_survives_a_reversed_or_flat_temperature_reading():
    assert et0_hargreaves(30, 15, 19.99, date(2026, 11, 16)) > 0   # swapped min/max
    assert et0_hargreaves(25, 25, 19.99, date(2026, 11, 16)) == 0  # no swing => no ET term


def test_effective_rain_discounts_interception_and_runoff():
    assert effective_rain_mm(0.0) == 0.0
    assert effective_rain_mm(1.5) == 0.0          # wets the canopy only
    assert effective_rain_mm(12.0) < 12.0         # some runs off


# --- FAO-56 coefficients -----------------------------------------------------------------------

def test_kc_follows_the_fao_curve_shape():
    onion = CROP_PARAMS["onion"]
    _, kc_ini, _ = stage_for(onion, 5)
    _, kc_dev, _ = stage_for(onion, 30)
    _, kc_mid, _ = stage_for(onion, 60)
    assert kc_ini < kc_dev < kc_mid
    assert kc_mid == onion.kc_mid


def test_roots_deepen_with_the_crop():
    soybean = CROP_PARAMS["soybean"]
    _, _, early = stage_for(soybean, 5)
    _, _, late = stage_for(soybean, 60)
    assert early < late == soybean.root_max_m


def test_onion_is_more_drought_sensitive_than_soybean():
    """p=0.30 vs 0.50 is why onion needs little and often. Regression guard on the tables."""
    assert CROP_PARAMS["onion"].depletion_fraction < CROP_PARAMS["soybean"].depletion_fraction
    assert CROP_PARAMS["onion"].root_max_m < CROP_PARAMS["soybean"].root_max_m


def test_unknown_stage_falls_back_to_mid_season():
    stage, kc, _ = stage_for(CROP_PARAMS["onion"], None)
    assert stage == "unknown"
    assert kc == CROP_PARAMS["onion"].kc_mid


def test_soil_and_method_tables_are_ordered_sensibly():
    assert SOILS["heavy"].awc_mm_per_m > SOILS["medium"].awc_mm_per_m > SOILS["light"].awc_mm_per_m
    assert METHODS["drip"].efficiency > METHODS["sprinkler"].efficiency > METHODS["flood"].efficiency


# --- the plan ----------------------------------------------------------------------------------

def test_flood_wastes_more_water_than_drip_for_the_same_need():
    common = dict(forecast=_forecast(), lat=NASHIK[0], crop="onion",
                  days_after_start=60, last_watered_days_ago=5, soil="medium")
    drip = build_plan(**common, method="drip")
    flood = build_plan(**common, method="flood")
    assert flood.gross_mm > drip.gross_mm
    assert flood.net_mm / 0.55 == flood.gross_mm or abs(flood.net_mm / 0.55 - flood.gross_mm) < 0.2


def test_drip_uses_a_short_interval_not_the_depletion_trigger():
    """Drip's point is little and often; waiting for 50 mm of depletion defeats it."""
    plan = build_plan(forecast=_forecast(24, 40), lat=17.66, crop="pomegranate",
                      days_after_start=100, last_watered_days_ago=2,
                      soil="light", method="drip")
    assert plan.decision == "irrigate"
    assert plan.net_mm < plan.raw_mm, "drip must not dump a full root-zone refill"


def test_no_last_watered_day_means_unsure_not_a_guess():
    plan = build_plan(forecast=_forecast(), lat=NASHIK[0], crop="onion",
                      days_after_start=60, soil="medium", method="drip")
    assert plan.decision == "unsure"
    assert plan.irrigate_today is False
    assert plan.confidence == "rough"
    # It must still answer what it CAN: the depth per turn.
    assert plan.gross_mm > 0


def test_confidence_is_good_only_with_both_dates():
    full = build_plan(forecast=_forecast(), lat=NASHIK[0], crop="onion", days_after_start=60,
                      last_watered_days_ago=3, soil="medium", method="drip")
    assert full.confidence == "good"


def test_rain_defers_a_due_irrigation():
    plan = build_plan(forecast=_forecast(22, 29, rain=25.0, chance=85), lat=NASHIK[0],
                      crop="onion", days_after_start=60, last_watered_days_ago=10,
                      soil="medium", method="flood")
    assert plan.decision in ("rain_coming", "wait")
    assert plan.irrigate_today is False


def test_litres_per_plant_needs_spacing_and_scales_with_it():
    base = dict(forecast=_forecast(24, 40), lat=17.66, crop="pomegranate",
                days_after_start=100, last_watered_days_ago=2, soil="light", method="drip")
    assert build_plan(**base).litres_per_plant is None
    wide = build_plan(**base, row_spacing_m=4.5, plant_spacing_m=3.0)
    narrow = build_plan(**base, row_spacing_m=3.0, plant_spacing_m=2.0)
    assert wide.litres_per_plant > narrow.litres_per_plant


def test_run_hours_needs_an_emitter_rate():
    base = dict(forecast=_forecast(24, 40), lat=17.66, crop="pomegranate",
                days_after_start=100, last_watered_days_ago=2, soil="light", method="drip",
                row_spacing_m=4.5, plant_spacing_m=3.0)
    assert build_plan(**base).run_hours is None
    assert build_plan(**base, emitter_lph=8.0, emitters_per_plant=2).run_hours > 0


def test_unsupported_crop_returns_no_plan():
    assert build_plan(forecast=_forecast(), lat=NASHIK[0], crop="wheat") is None


def test_no_forecast_returns_no_plan():
    empty = _forecast(days=0)
    assert build_plan(forecast=empty, lat=NASHIK[0], crop="onion") is None


def test_plan_carries_the_weather_source_through():
    """A plan computed on sample weather must be badgeable as sample."""
    plan = build_plan(forecast=_forecast(source="mock-0"), lat=NASHIK[0], crop="onion",
                      days_after_start=60, last_watered_days_ago=3)
    assert plan.source.startswith("mock")


def test_notes_never_state_a_chemical_dose():
    """The locked dosage policy: water quantities are fine here, chemical ones never are."""
    plan = build_plan(forecast=_forecast(), lat=NASHIK[0], crop="onion", days_after_start=110,
                      last_watered_days_ago=4, soil="medium", method="flood")
    joined = " ".join(plan.notes) + plan.reason
    for banned in ("ग्रॅम", "मिली ", "कीटकनाशक", "बुरशीनाशक"):
        assert banned not in joined, f"irrigation advice must not drift into spraying: {banned}"


def test_every_plan_tells_the_farmer_to_check_the_soil_by_hand():
    """No sensor, so the hand-feel check is the honest cross-check and must always be present."""
    for crop in CROP_PARAMS:
        plan = build_plan(forecast=_forecast(), lat=NASHIK[0], crop=crop,
                          days_after_start=60, last_watered_days_ago=3)
        assert any("मूठभर माती" in n for n in plan.notes), crop


# --- endpoint ----------------------------------------------------------------------------------

def test_endpoint_returns_a_plan_badged_as_sample_data():
    r = client.get("/irrigation/advice", params={
        "lat": NASHIK[0], "lon": NASHIK[1], "crop": "onion",
        "sowing_date": (date.today() - timedelta(days=60)).isoformat(),
        "last_watered_days_ago": 4, "soil": "medium", "method": "drip",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["source"].startswith("mock")
    assert body["decision"] in ("irrigate", "wait", "rain_coming", "unsure")
    assert body["reason"] and body["notes"]
    assert body["days_after_start"] == 60
    assert body["gross_mm"] > 0


def test_endpoint_rejects_an_unsupported_crop():
    r = client.get("/irrigation/advice", params={
        "lat": NASHIK[0], "lon": NASHIK[1], "crop": "wheat",
    })
    assert r.status_code == 422
    assert "onion" in r.json()["detail"]


def test_endpoint_ignores_a_future_sowing_date():
    """A mistyped year must not become a negative crop age."""
    r = client.get("/irrigation/advice", params={
        "lat": NASHIK[0], "lon": NASHIK[1], "crop": "onion",
        "sowing_date": (date.today() + timedelta(days=30)).isoformat(),
    })
    assert r.status_code == 200
    assert r.json()["days_after_start"] is None


def test_endpoint_rejects_absurd_inputs():
    base = {"lat": NASHIK[0], "lon": NASHIK[1], "crop": "onion"}
    assert client.get("/irrigation/advice", params={**base, "last_watered_days_ago": -1}).status_code == 422
    assert client.get("/irrigation/advice", params={**base, "last_watered_days_ago": 999}).status_code == 422
    assert client.get("/irrigation/advice", params={**base, "emitter_lph": 0}).status_code == 422
