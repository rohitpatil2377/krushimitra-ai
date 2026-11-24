"""Phone-OTP auth.

**The OTP is not really sent yet.** No SMS provider is wired, so any phone plus `settings.dev_otp`
logs in and creates the farmer on first use. That is fine for a pilot with farmers you know, and
dangerous the day the app is public — so `/health` reports `auth_otp_is_real: false` and the
request response says so out loud, rather than letting a real-looking login screen imply security
it does not have. Wire an SMS/WhatsApp provider before launch.

Why phone and not email: a Maharashtra farmer has a phone number, often not an email, and the
number is also how a KVK or a dealer would reach them later.
"""
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_farmer
from app.core.config import settings
from app.core.db import get_db
from app.core.security import create_access_token
from app.models import Farmer
from app.schemas.api import FarmerOut, FarmerUpdate, OTPRequest, OTPVerify, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])

# Indian mobile numbers, with or without +91 / 0 prefix.
PHONE_RE = re.compile(r"^(?:\+?91)?[6-9]\d{9}$")


def normalise_phone(raw: str) -> str:
    """One canonical form, so the same farmer cannot end up with three accounts."""
    digits = re.sub(r"[^\d+]", "", raw or "")
    if digits.startswith("+91"):
        digits = digits[3:]
    elif digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if not PHONE_RE.match(digits):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Enter a valid 10-digit mobile number")
    return digits


@router.post("/otp/request")
def request_otp(body: OTPRequest) -> dict:
    phone = normalise_phone(body.phone)
    if settings.auth_otp_is_real:  # pragma: no cover - no provider wired yet
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "SMS provider not implemented")
    return {
        "sent": False,
        "phone": phone,
        # Never pretend an SMS went out. The app shows this instead of a fake "check your SMS".
        "otp_is_real": False,
        "dev_otp": settings.dev_otp,
        "message_mr": f"सध्या SMS पाठवला जात नाही. चाचणीसाठी OTP: {settings.dev_otp}",
    }


@router.post("/otp/verify", response_model=TokenOut)
def verify_otp(body: OTPVerify, db: Session = Depends(get_db)) -> TokenOut:
    phone = normalise_phone(body.phone)
    if body.otp != settings.dev_otp:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid OTP")

    farmer = db.scalar(select(Farmer).where(Farmer.phone == phone))
    if farmer is None:
        farmer = Farmer(phone=phone)
        db.add(farmer)
        db.commit()
        db.refresh(farmer)

    return TokenOut(access_token=create_access_token(str(farmer.id)))


@router.get("/me", response_model=FarmerOut)
def me(farmer: Farmer = Depends(get_current_farmer)) -> Farmer:
    return farmer


@router.patch("/me", response_model=FarmerOut)
def update_me(
    body: FarmerUpdate,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> Farmer:
    patch = body.model_dump(exclude_unset=True)

    # Claiming the device id attaches the photos this phone captured before anyone logged in.
    # Only ever set it when it is free: if another account already holds it, two farmers have
    # shared a handset and silently reassigning their captures would corrupt the split group.
    device_id = patch.pop("device_id", None)
    if device_id:
        taken = db.scalar(select(Farmer).where(Farmer.device_id == device_id))
        if taken is None or taken.id == farmer.id:
            farmer.device_id = device_id

    for key, value in patch.items():
        setattr(farmer, key, value)
    db.commit()
    db.refresh(farmer)
    return farmer
