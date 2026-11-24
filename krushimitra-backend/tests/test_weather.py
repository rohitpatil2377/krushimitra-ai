"""Weather + crop advisory tests.

The forecast numbers are a commodity; the advisories are the product. So most of these build a
forecast by hand and assert that the right agronomic rule fires — the thresholds are the thing
worth regression-testing, not httpx.
"""
from datetime import date, timedelta


from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.weather.advice import MAX_ADVISORIES, build_advisories  # noqa: E402
from app.services.weather.base import CurrentWeather, DayForecast, Forecast  # noqa: E402
from app.services.weather.mock import MockWeatherService  # noqa: E402

client = TestClient(app)


def _day(offset, *, tmin=20.0, tmax=30.0, humidity=60, rain=0.0, chance=10, wind=8.0,
         condition="clear"):
    return DayForecast(
        date=(date.today() + timedelta(days=offset)).isoformat(),
        temp_min_c=tmin, temp_max_c=tmax, humidity_pct=humidity,
        rain_mm=rain, rain_chance_pct=chance, wind_kph=wind, condition=condition,
    )


def _forecast(days, *, temp=27.0, humidity=60, wind=8.0):
    return Forecast(
        current=CurrentWeather(
            temp_c=temp, feels_like_c=temp, humidity_pct=humidity, wind_kph=wind,
            rain_mm=0.0, condition="clear", observed_at="2026-11-13T06:00:00+00:00",
        ),
        days=days, source="test",
    )


def _keys(advisories):
    return {a.key for a in advisories}


# --- the spray window: the single most valuable thing we can tell a farmer -------------------

def test_rain_coming_means_do_not_spray():
    f = _forecast([_day(0, rain=12.0, chance=80, condition="rain"), _day(1, rain=5.0, chance=70)])
    keys = _keys(build_advisories(f))
    assert "no_spray_rain" in keys
    assert "spray_window_ok" not in keys


def test_dry_and_calm_is_a_good_spray_window():
    f = _forecast([_day(0), _day(1), _day(2)])
    advisories = build_advisories(f)
    assert "spray_window_ok" in _keys(advisories)
    assert "no_spray_rain" not in _keys(advisories)


def test_high_wind_warns_about_drift():
    f = _forecast([_day(0, wind=26.0), _day(1, wind=24.0)], wind=26.0)
    assert "wind_drift" in _keys(build_advisories(f))


def test_extreme_heat_is_flagged():
    f = _forecast([_day(0, tmax=41.0), _day(1, tmax=40.0)])
    assert "heat_stress" in _keys(build_advisories(f))


# --- crop-specific disease pressure ----------------------------------------------------------

def test_onion_humid_warm_raises_blotch_risk():
    f = _forecast([_day(i, humidity=88, tmin=18, tmax=28) for i in range(3)])
    assert "onion_blotch_risk" in _keys(build_advisories(f, "onion"))


def test_onion_hot_dry_spell_warns_about_thrips():
    """Thrips build up in dry heat, and their feeding wounds are how blotch gets in later."""
    f = _forecast([_day(i, humidity=45, tmin=20, tmax=36, chance=5) for i in range(5)])
    assert "onion_thrips_surge" in _keys(build_advisories(f, "onion"))


def test_pomegranate_rain_raises_telya():
    f = _forecast([_day(0, rain=18.0, chance=85, humidity=88, condition="rain"), _day(1, rain=6.0, chance=70)])
    assert "pomegranate_telya" in _keys(build_advisories(f, "pomegranate"))


def test_pomegranate_dry_then_rain_warns_about_cracking():
    days = [_day(i, tmax=37.0, humidity=40) for i in range(3)] + [
        _day(3, rain=20.0, chance=80, condition="rain"), _day(4, rain=8.0, chance=70)
    ]
    assert "pomegranate_cracking" in _keys(build_advisories(_forecast(days), "pomegranate"))


def test_soybean_heavy_rain_warns_about_waterlogging():
    days = [_day(i, rain=25.0, chance=85, humidity=90, condition="rain") for i in range(3)]
    assert "soybean_waterlog" in _keys(build_advisories(_forecast(days), "soybean"))


def test_soybean_humid_warm_run_raises_rust():
    f = _forecast([_day(i, humidity=90, tmin=20, tmax=27) for i in range(3)])
    assert "soybean_rust" in _keys(build_advisories(f, "soybean"))


# --- framing rules ----------------------------------------------------------------------------

def test_no_crop_gives_only_universal_advice():
    f = _forecast([_day(i, humidity=90, tmin=20, tmax=27) for i in range(3)])
    assert all(a.crop is None for a in build_advisories(f, None))


def test_warnings_come_first_and_the_list_is_capped():
    days = [_day(i, rain=30.0, chance=90, humidity=92, tmin=20, tmax=41, wind=28.0) for i in range(5)]
    advisories = build_advisories(_forecast(days, wind=28.0), "pomegranate")
    assert len(advisories) <= MAX_ADVISORIES
    assert advisories[0].level == "warning"
    levels = [a.level for a in advisories]
    assert levels == sorted(levels, key=lambda lv: {"warning": 0, "watch": 1, "info": 2}[lv])


def test_advisories_never_state_a_dose():
    """The locked dosage policy applies here too — weather advice must not name quantities."""
    days = [_day(i, rain=20.0, chance=85, humidity=90, tmin=19, tmax=27) for i in range(5)]
    for crop in ("onion", "soybean", "pomegranate", None):
        for a in build_advisories(_forecast(days), crop):
            text = f"{a.title} {a.body}"
            for banned in ("ग्रॅम", "मिली", "लिटर प्रति", "प्रति लिटर", "ml", "gram"):
                assert banned not in text, f"{a.key} names a dose: {banned}"


def test_empty_forecast_gives_no_advice():
    assert build_advisories(_forecast([]), "onion") == []


# --- endpoint ----------------------------------------------------------------------------------

def test_forecast_endpoint_is_badged_as_sample_data():
    r = client.get("/weather/forecast", params={"lat": 19.99, "lon": 73.78, "crop": "onion"})
    assert r.status_code == 200
    body = r.json()
    assert body["source"].startswith("mock")      # no key configured => sample data, and it says so
    assert len(body["days"]) == 5
    assert body["current"]["condition"]
    assert isinstance(body["advisories"], list)


def test_forecast_endpoint_rejects_bad_coordinates():
    assert client.get("/weather/forecast", params={"lat": 999, "lon": 73.78}).status_code == 422


def test_mock_is_stable_for_the_same_farm_on_the_same_day():
    """Pull-to-refresh must not reshuffle the forecast."""
    import asyncio

    a = asyncio.run(MockWeatherService().forecast(19.99, 73.78))
    b = asyncio.run(MockWeatherService().forecast(19.99, 73.78))
    c = asyncio.run(MockWeatherService().forecast(17.68, 75.91))
    assert [vars(d) for d in a.days] == [vars(d) for d in b.days]
    assert [vars(d) for d in a.days] != [vars(d) for d in c.days]
