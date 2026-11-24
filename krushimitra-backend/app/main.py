"""KrushiMitra AI backend — FastAPI entrypoint."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth, copilot, crop_cycles, farms, irrigation, market, recommend, vision, weather,
)
from app.core.config import settings
from app.core.db import create_all

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Create missing tables so a fresh clone works with no setup step."""
    create_all()
    yield

app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)


# The Expo app calls this from devices; lock down origins before launch.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(copilot.router)
app.include_router(vision.router)
app.include_router(farms.router)
app.include_router(crop_cycles.router)
app.include_router(recommend.router)
app.include_router(weather.router)
app.include_router(irrigation.router)
app.include_router(market.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.env,
        "use_mocks": settings.use_mocks,
        "copilot_provider": settings.active_copilot_provider,
        "copilot_is_real": settings.active_copilot_provider != "mock",
        "voice_live": settings.voice_live,
        # The app badges sample data off model_version, but a human debugging "is the AI real?"
        # should be able to answer it from /health alone.
        "vision_provider": settings.active_vision_provider,
        "vision_is_real": settings.active_vision_provider != "mock",
        "vision_min_confidence": settings.vision_min_confidence,
        "weather_provider": settings.active_weather_provider,
        "weather_is_real": settings.weather_live,
        # "is the login real?" — answered the same way as the vision badge, never guessed.
        "auth_otp_is_real": settings.auth_otp_is_real,
        "market_provider": settings.active_market_provider,
        "market_is_real": settings.market_live,
    }
