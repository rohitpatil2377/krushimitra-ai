"""Shared FastAPI dependencies."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_access_token
from app.models import Farmer

_bearer = HTTPBearer(auto_error=True)


def get_current_farmer(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Farmer:
    try:
        farmer_id = decode_access_token(creds.credentials)
    except Exception as exc:  # invalid/expired token
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc

    farmer = db.get(Farmer, int(farmer_id))
    if farmer is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown farmer")
    return farmer
