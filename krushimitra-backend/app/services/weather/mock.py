"""Sample weather, so the whole feature works with zero keys.

Seasonally plausible for Maharashtra rather than random, because a mock that always says 25°C and
sunny would never exercise the advisory rules and we would ship them untested. The values are
seeded from the location and the date, so the same farm sees a stable forecast within a day
instead of numbers that jump on every pull-to-refresh.

MOCK_SOURCE starts with "mock" — that prefix is the contract the app badges on. Never change it
to something that reads like a real provider.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone

from app.services.weather.base import CurrentWeather, DayForecast, Forecast

MOCK_SOURCE = "mock-0"

# (temp_min, temp_max, humidity, rain_chance, condition) by month — Deccan plateau, roughly.
_SEASON = {
    1:  (12, 29, 45, 5,  "clear"),      2:  (14, 32, 40, 5,  "clear"),
    3:  (18, 36, 35, 5,  "clear"),      4:  (22, 39, 30, 10, "haze"),
    5:  (24, 40, 35, 20, "haze"),       6:  (23, 32, 75, 65, "rain"),
    7:  (22, 29, 86, 80, "rain"),       8:  (22, 28, 88, 80, "rain"),
    9:  (21, 30, 82, 60, "rain"),       10: (19, 32, 65, 30, "clouds"),
    11: (15, 30, 55, 15, "clouds"),     12: (12, 28, 48, 5,  "clear"),
}


class MockWeatherService:
    """Never fails and never pretends to be real."""

    async def forecast(self, lat: float, lon: float) -> Forecast:
        today = date.today()
        # Same farm + same day => same numbers. Different farm => different weather.
        seed = int(round(lat * 100)) * 100000 + int(round(lon * 100)) + today.toordinal()
        rng = random.Random(seed)

        t_min, t_max, humidity, rain_chance, condition = _SEASON[today.month]

        current = CurrentWeather(
            temp_c=round(rng.uniform(t_min + 4, t_max - 2), 1),
            feels_like_c=round(rng.uniform(t_min + 5, t_max), 1),
            humidity_pct=max(20, min(98, humidity + rng.randint(-8, 8))),
            wind_kph=round(rng.uniform(4, 16), 1),
            rain_mm=round(rng.uniform(0, 6), 1) if rain_chance > 50 else 0.0,
            condition=condition,
            observed_at=datetime.now(timezone.utc).isoformat(),
        )

        days: list[DayForecast] = []
        for offset in range(5):
            chance = max(0, min(100, rain_chance + rng.randint(-15, 15)))
            wet = chance >= 50
            days.append(DayForecast(
                date=(today + timedelta(days=offset)).isoformat(),
                temp_min_c=round(t_min + rng.uniform(-2, 2), 1),
                temp_max_c=round(t_max + rng.uniform(-3, 2), 1),
                humidity_pct=max(20, min(98, humidity + rng.randint(-10, 10))),
                rain_mm=round(rng.uniform(2, 28), 1) if wet else round(rng.uniform(0, 1), 1),
                rain_chance_pct=chance,
                wind_kph=round(rng.uniform(4, 18), 1),
                condition=condition if wet else ("clouds" if chance > 25 else "clear"),
            ))

        return Forecast(current=current, days=days, source=MOCK_SOURCE, location_name=None)
