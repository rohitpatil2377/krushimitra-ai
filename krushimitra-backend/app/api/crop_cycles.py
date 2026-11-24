"""Digital Crop Twin — one planting, from sowing to harvest, as a timeline.

This is the asset the rest of the product compounds on:
  * it answers "what is growing where, and how old is it" so the AI stops asking the farmer
    things it already knows,
  * it turns scattered photo diagnoses into a season history,
  * and every event recorded here is a labelled row in the dataset (see docs/DATASET.md).

Ownership is checked on every route through the cycle's farm. The 404 is deliberately identical
for "missing" and "not yours".
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_farmer
from app.core.db import get_db
from app.models import CropCycle, CropEvent, Farm, Farmer
from app.models.enums import CROPS, EVENT_TYPES
from app.schemas.api import (
    CropCycleCreate,
    CropCycleDetailOut,
    CropCycleOut,
    CropCycleSummaryOut,
    CropCycleUpdate,
    CropEventCreate,
    CropEventOut,
    HealthScoreOut,
    StageOut,
)
from app.services.twin import band_for, health_for, stage_of

router = APIRouter(prefix="/crop-cycles", tags=["crop-cycles"])


def _owned(db: Session, cycle_id: int, farmer: Farmer) -> CropCycle:
    cycle = db.get(CropCycle, cycle_id)
    if cycle is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle not found")
    farm = db.get(Farm, cycle.farm_id)
    if farm is None or farm.farmer_id != farmer.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle not found")
    return cycle


def _diagnosis_history(db: Session, cycle_id: int) -> list[dict]:
    """Diagnosis events shaped for the health score."""
    events = db.scalars(
        select(CropEvent)
        .where(CropEvent.crop_cycle_id == cycle_id, CropEvent.type == "diagnosis")
        .order_by(CropEvent.created_at.desc())
    ).all()
    out: list[dict] = []
    for e in events:
        data = e.data or {}
        out.append({
            "on": (data.get("on") or e.created_at.date().isoformat()),
            "severity_level": data.get("severity_level"),
            "disease_slug": data.get("disease_slug"),
        })
    return out


def _health(db: Session, cycle: CropCycle) -> HealthScoreOut:
    result = health_for(_diagnosis_history(db, cycle.id))
    return HealthScoreOut(
        score=result.score, band=result.band, band_mr=result.band_mr,
        items=[vars(i) for i in result.items], note=result.note,
    )


def _detail(db: Session, cycle: CropCycle) -> CropCycleDetailOut:
    farm = db.get(Farm, cycle.farm_id)
    health = _health(db, cycle)
    # Cache the score so a list view does not have to recompute every cycle.
    cycle.current_health_score = health.score
    db.commit()
    count = db.scalar(
        select(func.count()).select_from(CropEvent).where(CropEvent.crop_cycle_id == cycle.id)
    ) or 0
    return CropCycleDetailOut(
        **CropCycleOut.model_validate(cycle).model_dump(),
        farm=farm,
        stage=StageOut(**stage_of(cycle.crop, cycle.sowing_date)),
        health=health,
        event_count=count,
    )


@router.get("", response_model=list[CropCycleSummaryOut])
def list_cycles(
    status_filter: str | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> list[CropCycleSummaryOut]:
    q = (
        select(CropCycle, Farm.name)
        .join(Farm, Farm.id == CropCycle.farm_id)
        .where(Farm.farmer_id == farmer.id)
        .order_by(CropCycle.created_at.desc())
    )
    if status_filter:
        q = q.where(CropCycle.status == status_filter)

    out: list[CropCycleSummaryOut] = []
    for cycle, plot_name in db.execute(q).all():
        score = cycle.current_health_score
        band, band_mr = band_for(score) if score is not None else (None, None)
        out.append(CropCycleSummaryOut(
            **CropCycleOut.model_validate(cycle).model_dump(),
            plot_name=plot_name,
            stage=StageOut(**stage_of(cycle.crop, cycle.sowing_date)),
            health_score=score,
            health_band=band,
            health_band_mr=band_mr,
        ))
    return out


@router.post("", response_model=CropCycleDetailOut, status_code=status.HTTP_201_CREATED)
def create_cycle(
    body: CropCycleCreate,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> CropCycleDetailOut:
    if body.crop not in CROPS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"crop must be one of {CROPS}")
    farm = db.get(Farm, body.farm_id)
    if farm is None or farm.farmer_id != farmer.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Farm not found")
    if body.sowing_date and body.sowing_date > date.today():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "sowing_date cannot be in the future")

    cycle = CropCycle(**body.model_dump())
    db.add(cycle)
    db.commit()
    db.refresh(cycle)

    # The timeline starts with the sowing itself, so an empty cycle still reads as a story.
    if cycle.sowing_date:
        db.add(CropEvent(
            crop_cycle_id=cycle.id, type="sowing", day_index=0,
            title="लागवड", data={"on": cycle.sowing_date.isoformat()},
        ))
        db.commit()
    return _detail(db, cycle)


@router.get("/{cycle_id}", response_model=CropCycleDetailOut)
def get_cycle(
    cycle_id: int,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> CropCycleDetailOut:
    return _detail(db, _owned(db, cycle_id, farmer))


@router.patch("/{cycle_id}", response_model=CropCycleDetailOut)
def update_cycle(
    cycle_id: int,
    body: CropCycleUpdate,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> CropCycleDetailOut:
    cycle = _owned(db, cycle_id, farmer)
    patch = body.model_dump(exclude_unset=True)
    for field in ("sowing_date", "last_watered_date", "harvest_date"):
        value = patch.get(field)
        if value and value > date.today():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{field} cannot be in the future")
    for key, value in patch.items():
        setattr(cycle, key, value)

    # Harvesting closes the season; record it on the timeline rather than only flipping a flag.
    if patch.get("status") == "harvested":
        cycle.harvest_date = cycle.harvest_date or date.today()
        db.add(CropEvent(
            crop_cycle_id=cycle.id, type="harvest",
            day_index=_day_index(cycle, cycle.harvest_date),
            title="काढणी",
            data={"on": cycle.harvest_date.isoformat(), "yield_quintal": cycle.yield_quintal},
        ))
    db.commit()
    db.refresh(cycle)
    return _detail(db, cycle)


def _day_index(cycle: CropCycle, on: date | None) -> int | None:
    if cycle.sowing_date is None or on is None:
        return None
    return max(0, (on - cycle.sowing_date).days)


@router.get("/{cycle_id}/timeline", response_model=list[CropEventOut])
def timeline(
    cycle_id: int,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> list[CropEvent]:
    _owned(db, cycle_id, farmer)
    return list(db.scalars(
        select(CropEvent)
        .where(CropEvent.crop_cycle_id == cycle_id)
        .order_by(CropEvent.created_at.desc())
    ))


@router.post("/{cycle_id}/events", response_model=CropEventOut, status_code=status.HTTP_201_CREATED)
def add_event(
    cycle_id: int,
    body: CropEventCreate,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> CropEvent:
    cycle = _owned(db, cycle_id, farmer)
    if body.type not in EVENT_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"type must be one of {EVENT_TYPES}")

    on = body.on or date.today()
    data = dict(body.data or {})
    data.setdefault("on", on.isoformat())

    event = CropEvent(
        crop_cycle_id=cycle.id, type=body.type, day_index=_day_index(cycle, on),
        title=body.title, body=body.body, data=data, diagnosis_id=body.diagnosis_id,
    )
    db.add(event)

    # Watering is also a fact the irrigation plan needs; keep the two in step automatically
    # rather than making the farmer log it twice.
    if body.type == "irrigation":
        cycle.last_watered_date = on

    db.commit()
    db.refresh(event)
    return event


@router.get("/{cycle_id}/health-score", response_model=HealthScoreOut)
def health_score(
    cycle_id: int,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> HealthScoreOut:
    return _health(db, _owned(db, cycle_id, farmer))
