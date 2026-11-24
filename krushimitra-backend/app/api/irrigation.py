"""Irrigation advice endpoint.

Composition: weather forecast -> FAO-56 water balance -> Marathi plan. The forecast comes from
the same provider the /weather screen uses (degrading to a labelled mock), so a farmer never
gets an error page, and `source` tells the app whether the plan rests on real weather.

Unsupported crop => 422, not a guess. Inventing a crop coefficient would produce a confident
number with nothing behind it, which is the failure mode this whole project is built against.
"""
import logging
from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.schemas.api import IrrigationOut
from app.services.irrigation import CROP_PARAMS, build_plan
from app.services.weather import MockWeatherService, get_weather_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/irrigation", tags=["irrigation"])

MAX_DAYS_SINCE_WATERING = 60


@router.get("/advice", response_model=IrrigationOut)
async def advice(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    crop: str = Query(..., description="onion | soybean | pomegranate"),
    sowing_date: date | None = Query(
        None, description="Sowing/transplant date, or bahar date for pomegranate"
    ),
    last_watered_days_ago: int | None = Query(
        None, ge=0, le=MAX_DAYS_SINCE_WATERING,
        description="Days since the last irrigation. Without it, 'water today?' is unanswerable.",
    ),
    soil: str = Query("medium", description="heavy | medium | light"),
    method: str = Query("drip", description="drip | sprinkler | flood"),
    row_spacing_m: float | None = Query(None, gt=0, le=20),
    plant_spacing_m: float | None = Query(None, gt=0, le=20),
    emitter_lph: float | None = Query(None, gt=0, le=200),
    emitters_per_plant: int = Query(1, ge=1, le=20),
) -> IrrigationOut:
    if (crop or "").lower() not in CROP_PARAMS:
        raise HTTPException(
            status_code=422,
            detail=f"no irrigation parameters for crop '{crop}' — supported: "
                   + ", ".join(sorted(CROP_PARAMS)),
        )

    try:
        forecast = await get_weather_service().forecast(lat, lon)
    except Exception as exc:
        log.warning("[irrigation] %s failed, serving mock: %s", settings.active_weather_provider, exc)
        forecast = await MockWeatherService().forecast(lat, lon)
        forecast.source = "mock-fallback"

    days_after_start = None
    if sowing_date is not None:
        delta = (date.today() - sowing_date).days
        # A future sowing date means a mistyped year or a wrong phone clock. Treat the crop stage
        # as unknown rather than computing a negative age.
        days_after_start = delta if delta >= 0 else None

    plan = build_plan(
        forecast,
        lat,
        crop,
        days_after_start=days_after_start,
        last_watered_days_ago=last_watered_days_ago,
        soil=soil,
        method=method,
        row_spacing_m=row_spacing_m,
        plant_spacing_m=plant_spacing_m,
        emitter_lph=emitter_lph,
        emitters_per_plant=emitters_per_plant,
    )
    if plan is None:
        raise HTTPException(status_code=503, detail="no forecast available to plan irrigation")

    return IrrigationOut(**vars(plan))
