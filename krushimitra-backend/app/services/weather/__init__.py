"""Weather service selection — one place decides who is actually serving a forecast.

Same rule as vision: presence of the key is the opt-in, and `GET /health` reports which provider
answered so "is this real?" is never guessed from whether the request succeeded.
"""
from __future__ import annotations

from app.core.config import settings
from app.services.weather.base import (
    CurrentWeather,
    DayForecast,
    Forecast,
    WeatherError,
    WeatherService,
)
from app.services.weather.mock import MOCK_SOURCE, MockWeatherService

__all__ = [
    "CurrentWeather",
    "DayForecast",
    "Forecast",
    "MOCK_SOURCE",
    "MockWeatherService",
    "WeatherError",
    "WeatherService",
    "get_weather_service",
]


def get_weather_service() -> WeatherService:
    if settings.weather_live:
        from app.services.weather.openweather import OpenWeatherService

        return OpenWeatherService()
    return MockWeatherService()
