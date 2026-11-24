"""Farms (plots) — the facts about a piece of land, asked once.

Before this, every advisory screen re-asked the same questions: which district, what soil, drip
or flood, what spacing. A farmer on a cheap phone answers that twice and then stops using the
app. A plot stores it once; weather, irrigation and mandi prices read it.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_farmer
from app.core.db import get_db
from app.models import CropCycle, Farm, Farmer
from app.schemas.api import FarmCreate, FarmOut, FarmUpdate

router = APIRouter(prefix="/farms", tags=["farms"])


def _owned(db: Session, farm_id: int, farmer: Farmer) -> Farm:
    farm = db.get(Farm, farm_id)
    # Same 404 whether it does not exist or belongs to someone else — never confirm the
    # existence of another farmer's plot to a stranger holding a guessed id.
    if farm is None or farm.farmer_id != farmer.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Farm not found")
    return farm


@router.get("", response_model=list[FarmOut])
def list_farms(
    db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)
) -> list[Farm]:
    return list(db.scalars(select(Farm).where(Farm.farmer_id == farmer.id).order_by(Farm.id)))


@router.post("", response_model=FarmOut, status_code=status.HTTP_201_CREATED)
def create_farm(
    body: FarmCreate,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> Farm:
    farm = Farm(farmer_id=farmer.id, **body.model_dump(exclude_unset=True))
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


@router.get("/{farm_id}", response_model=FarmOut)
def get_farm(
    farm_id: int,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> Farm:
    return _owned(db, farm_id, farmer)


@router.patch("/{farm_id}", response_model=FarmOut)
def update_farm(
    farm_id: int,
    body: FarmUpdate,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> Farm:
    farm = _owned(db, farm_id, farmer)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(farm, key, value)
    db.commit()
    db.refresh(farm)
    return farm


@router.delete("/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farm(
    farm_id: int,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> None:
    farm = _owned(db, farm_id, farmer)
    # Refuse rather than cascade: a plot's cycles are the farmer's season history, and silently
    # destroying it to satisfy a mistyped tap is not recoverable.
    if db.scalar(select(CropCycle).where(CropCycle.farm_id == farm.id)) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This plot has crop cycles. Delete or archive them first.",
        )
    db.delete(farm)
    db.commit()
