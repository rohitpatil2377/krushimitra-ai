"""Weather endpoints.

Shape mirrors /vision: pick a provider, degrade to a LABELLED mock on failure, and let the
response say which one actually answered. The advisories are built here from whatever forecast
we ended up with, so sample weather still produces real-looking (and clearly badged) advice.
"""
import logging

from fastapi import APIRouter, Query

from app.core.config import settings
from app.schemas.api import (
    AdvisoryOut,
    CurrentWeatherOut,
    DayForecastOut,
    WeatherOut,
)
from app.services.weather import MockWeatherService, get_weather_service
from app.services.weather.advice import build_advisories

log = logging.getLogger(__name__)
router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/forecast", response_model=WeatherOut)
async def forecast(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    crop: str | None = Query(None, description="onion | soybean | pomegranate"),
) -> WeatherOut:
    """5-day forecast for a farm, plus what it means for the crop growing on it."""
    try:
        data = await get_weather_service().forecast(lat, lon)
    except Exception as exc:
        # A farmer on a weak network gets sample weather rather than an error screen — but the
        # source says "mock-fallback", so the app badges it instead of passing it off as real.
        log.warning("[weather] %s failed, serving mock: %s", settings.active_weather_provider, exc)
        data = await MockWeatherService().forecast(lat, lon)
        data.source = "mock-fallback"

    advisories = build_advisories(data, crop)

    return WeatherOut(
        location_name=data.location_name,
        lat=lat,
        lon=lon,
        crop=crop,
        current=CurrentWeatherOut(**vars(data.current)),
        days=[DayForecastOut(**vars(d)) for d in data.days],
        advisories=[AdvisoryOut(**vars(a)) for a in advisories],
        source=data.source,
    )
