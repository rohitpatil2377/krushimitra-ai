"""Shapes every weather provider returns, real or mock.

Deliberately small and provider-neutral: the app renders these fields and the advisory engine
reads them, so swapping OpenWeatherMap for IMD/Open-Meteo later touches one adapter, not the UI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


# Condition slugs are a closed set, so the app can translate them instead of displaying whatever
# English string a provider happened to send. Unmapped conditions fall back to "clouds".
CONDITIONS = (
    "clear", "clouds", "rain", "drizzle", "thunderstorm", "mist", "haze", "fog", "dust", "snow",
)

# Conditions that soak a sprayed leaf, in the order we would rather report them for a whole day:
# one thunderstorm matters more to a farmer than five clear hours.
_CONDITION_RANK = {
    "thunderstorm": 5, "rain": 4, "drizzle": 3, "snow": 3,
    "fog": 2, "mist": 2, "haze": 1, "dust": 1, "clouds": 1, "clear": 0,
}


def worst_condition(conditions: list[str]) -> str:
    """The condition a farmer needs to plan around, not the most frequent one."""
    usable = [c for c in conditions if c in _CONDITION_RANK]
    if not usable:
        return "clouds"
    return max(usable, key=lambda c: _CONDITION_RANK[c])


@dataclass
class CurrentWeather:
    temp_c: float
    feels_like_c: float
    humidity_pct: int
    wind_kph: float
    rain_mm: float
    condition: str
    observed_at: str          # ISO 8601, UTC


@dataclass
class DayForecast:
    date: str                 # yyyy-mm-dd, local to the farm
    temp_min_c: float
    temp_max_c: float
    humidity_pct: int
    rain_mm: float
    rain_chance_pct: int
    wind_kph: float
    condition: str


@dataclass
class Forecast:
    current: CurrentWeather
    days: list[DayForecast] = field(default_factory=list)
    # "openweather" for a real call; anything starting with "mock" is sample data and the app
    # badges it. Same rule as vision's model_version — never inferred from reachability.
    source: str = "mock-0"
    location_name: str | None = None


class WeatherError(RuntimeError):
    """Provider unreachable or refused. The API layer degrades to the mock, labelled as such."""


class WeatherService(Protocol):
    async def forecast(self, lat: float, lon: float) -> Forecast: ...
