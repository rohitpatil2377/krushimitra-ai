"""OpenWeatherMap adapter.

Uses the two endpoints that work on a FREE API key:
  * /data/2.5/weather  — current conditions
  * /data/2.5/forecast — 5 days in 3-hour steps, which we roll up into days

Deliberately NOT One Call 3.0: it needs a separate paid subscription, and a farmer-facing feature
that silently stops working when a card expires is worse than one that was never there.

The key is server-only (see .env.example): the app calls this backend, never OpenWeatherMap.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import settings
from app.services.weather.base import (
    CurrentWeather,
    DayForecast,
    Forecast,
    WeatherError,
    worst_condition,
)

log = logging.getLogger(__name__)

BASE = "https://api.openweathermap.org/data/2.5"
MS_TO_KPH = 3.6

# OpenWeatherMap's `weather[0].main` -> our closed condition set.
_MAIN_TO_SLUG = {
    "clear": "clear", "clouds": "clouds", "rain": "rain", "drizzle": "drizzle",
    "thunderstorm": "thunderstorm", "snow": "snow", "mist": "mist", "haze": "haze",
    "fog": "fog", "dust": "dust", "sand": "dust", "smoke": "haze", "ash": "dust",
    "squall": "thunderstorm", "tornado": "thunderstorm",
}


def _slug(entry: dict) -> str:
    weather = (entry.get("weather") or [{}])[0]
    return _MAIN_TO_SLUG.get(str(weather.get("main", "")).lower(), "clouds")


def _rain_mm(entry: dict) -> float:
    rain = entry.get("rain") or {}
    # Current uses "1h", forecast uses "3h". Take whichever the payload carries.
    for key in ("3h", "1h"):
        if key in rain:
            try:
                return float(rain[key])
            except (TypeError, ValueError):
                return 0.0
    return 0.0


class OpenWeatherService:
    """Real forecasts. Raises WeatherError so the API layer can degrade to a labelled mock."""

    def __init__(self, api_key: str | None = None, timeout_s: float | None = None) -> None:
        self.api_key = api_key or settings.openweather_api_key
        self.timeout_s = timeout_s or settings.weather_timeout_s

    async def _get(self, client: httpx.AsyncClient, path: str, lat: float, lon: float) -> dict:
        try:
            res = await client.get(
                f"{BASE}/{path}",
                params={"lat": lat, "lon": lon, "units": "metric", "appid": self.api_key},
            )
        except httpx.HTTPError as exc:
            raise WeatherError(f"openweather unreachable: {exc}") from exc
        if res.status_code == 401:
            raise WeatherError("openweather rejected the API key (401)")
        if res.status_code != 200:
            raise WeatherError(f"openweather {path} returned {res.status_code}: {res.text[:200]}")
        return res.json()

    async def forecast(self, lat: float, lon: float) -> Forecast:
        if not self.api_key:
            raise WeatherError("OPENWEATHER_API_KEY is not set")

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            now = await self._get(client, "weather", lat, lon)
            ahead = await self._get(client, "forecast", lat, lon)

        main = now.get("main") or {}
        wind = now.get("wind") or {}
        current = CurrentWeather(
            temp_c=round(float(main.get("temp", 0.0)), 1),
            feels_like_c=round(float(main.get("feels_like", main.get("temp", 0.0))), 1),
            humidity_pct=int(main.get("humidity", 0)),
            wind_kph=round(float(wind.get("speed", 0.0)) * MS_TO_KPH, 1),
            rain_mm=round(_rain_mm(now), 1),
            condition=_slug(now),
            observed_at=datetime.now(timezone.utc).isoformat(),
        )

        # Roll the 3-hour steps up into days, in the FARM's local time — a forecast bucketed by
        # UTC would put tonight's rain on tomorrow's card for an Indian user (IST is +5:30).
        offset = timedelta(seconds=int((ahead.get("city") or {}).get("timezone", 19800)))
        buckets: dict[str, list[dict]] = defaultdict(list)
        for entry in ahead.get("list") or []:
            stamp = entry.get("dt")
            if stamp is None:
                continue
            local = datetime.fromtimestamp(int(stamp), tz=timezone.utc) + offset
            buckets[local.date().isoformat()].append(entry)

        days: list[DayForecast] = []
        for date_str in sorted(buckets)[:5]:
            entries = buckets[date_str]
            temps = [float((e.get("main") or {}).get("temp", 0.0)) for e in entries]
            humidity = [int((e.get("main") or {}).get("humidity", 0)) for e in entries]
            winds = [float((e.get("wind") or {}).get("speed", 0.0)) * MS_TO_KPH for e in entries]
            pops = [float(e.get("pop", 0.0)) for e in entries]
            days.append(DayForecast(
                date=date_str,
                temp_min_c=round(min(temps), 1),
                temp_max_c=round(max(temps), 1),
                humidity_pct=round(sum(humidity) / len(humidity)) if humidity else 0,
                rain_mm=round(sum(_rain_mm(e) for e in entries), 1),
                rain_chance_pct=round(max(pops) * 100) if pops else 0,
                wind_kph=round(max(winds), 1) if winds else 0.0,
                condition=worst_condition([_slug(e) for e in entries]),
            ))

        return Forecast(
            current=current,
            days=days,
            source="openweather",
            location_name=now.get("name") or (ahead.get("city") or {}).get("name"),
        )
