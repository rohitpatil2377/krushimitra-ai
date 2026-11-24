"""Persist every diagnosed photo + its prediction + the farmer's correction.

This is the data moat (docs/DATASET.md), and it has to exist from the first farmer — a photo not
saved on day one is a training example lost forever. Public plant-disease sets are lab-condition
images; models trained on them collapse on real phone photos. Field photos with farmer-confirmed
labels are the only thing that fixes that, and they are the asset no competitor can copy.

Layout (local disk now; app/core/s3.py takes over in production):

    data/captures/2026/11/13/20261113-a1b2c3d4e5f6.jpg           the photo
    data/captures/2026/11/13/20261113-a1b2c3d4e5f6.json          what the model predicted
    data/captures/2026/11/13/20261113-a1b2c3d4e5f6.feedback.json what the farmer said

The date is encoded in the id so feedback can find its record without an index or a scan.
Capture is strictly best-effort: a disk problem must never cost the farmer their diagnosis.
"""
from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config import settings

log = logging.getLogger(__name__)

# A diagnosis id is a date stamp plus random hex. The strict pattern matters: the id arrives from
# the client on the feedback endpoint and is used to build a filesystem path, so anything looser
# would be a path-traversal hole.
ID_RE = re.compile(r"^\d{8}-[0-9a-f]{12}$")

_EXT_BY_MAGIC: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG", ".png"),
)


def _ext(image: bytes) -> str:
    for magic, ext in _EXT_BY_MAGIC:
        if image.startswith(magic):
            return ext
    if image[:4] == b"RIFF" and image[8:12] == b"WEBP":
        return ".webp"
    return ".bin"


def new_id(now: datetime | None = None) -> str:
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%d")
    return f"{stamp}-{uuid4().hex[:12]}"


# ~110 m at this latitude. Enough to map disease pressure onto a village and join it to weather;
# not enough to point at a particular household. Precision we never store cannot later leak.
COORD_DP = 3


def normalize_context(ctx: Mapping[str, Any] | None, captured_on: date | None = None) -> dict:
    """Flatten the client's field context into the shape the stored record keeps.

    Three jobs the caller should not have to think about:
      * derive `days_after_sowing`, so a photo's crop stage is usable without re-parsing dates
        across a dataset years from now;
      * round coordinates to ~100 m (privacy — see `FieldContext`);
      * decide `split_group`, the key an honest train/test split has to group by. Prefer the plot:
        two plots of one farmer are genuinely different fields, while one plot photographed
        weekly is the same plant and must never straddle the split.

    Returns `{"context": {...}, "split_group": str | None, "split_group_source": str | None}`.
    `split_group` is None when the app sent neither id — the record is still a usable photo, just
    not safely splittable, which `stats()` counts so the gap stays visible instead of silent.
    """
    data = dict(ctx or {})
    out: dict[str, Any] = {}

    for key in (
        "farmer_id", "plot_id", "district", "taluka",
        "crop_stage", "device_model", "os_version", "app_version",
    ):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            out[key] = value.strip()

    for key in ("lat", "lon"):
        value = data.get(key)
        if isinstance(value, (int, float)):
            out[key] = round(float(value), COORD_DP)

    sowing = data.get("sowing_date")
    if isinstance(sowing, str) and sowing:
        try:
            sowing = date.fromisoformat(sowing)
        except ValueError:
            sowing = None
    if isinstance(sowing, datetime):
        sowing = sowing.date()
    if isinstance(sowing, date):
        out["sowing_date"] = sowing.isoformat()
        age = ((captured_on or datetime.now(timezone.utc).date()) - sowing).days
        # A negative age means the phone clock is wrong or the date was mistyped. Keep the raw
        # sowing date, drop the derived number rather than train on a nonsense stage.
        if age >= 0:
            out["days_after_sowing"] = age

    if out.get("plot_id"):
        group, source = f"plot:{out['plot_id']}", "plot"
    elif out.get("farmer_id"):
        group, source = f"farmer:{out['farmer_id']}", "farmer"
    else:
        group, source = None, None

    return {"context": out, "split_group": group, "split_group_source": source}


def _dir_for(diagnosis_id: str) -> Path | None:
    """data/captures/YYYY/MM/DD for an id, or None if the id is malformed."""
    if not ID_RE.match(diagnosis_id):
        return None
    stamp = diagnosis_id[:8]
    return Path(settings.capture_dir) / stamp[:4] / stamp[4:6] / stamp[6:8]


def save_diagnosis(image: bytes, meta: dict) -> str | None:
    """Write the photo + prediction. Returns the diagnosis id, or None if capture is off/failed."""
    if not settings.capture_enabled or not image:
        return None

    diagnosis_id = new_id()
    folder = _dir_for(diagnosis_id)
    if folder is None:  # unreachable for a generated id; keeps the type checker honest
        return None

    try:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{diagnosis_id}{_ext(image)}").write_bytes(image)
        record = {
            "diagnosis_id": diagnosis_id,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "image_bytes": len(image),
            **meta,
        }
        (folder / f"{diagnosis_id}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return diagnosis_id
    except OSError as exc:
        # Never let storage trouble break a diagnosis the farmer is waiting on.
        log.warning("[capture] could not save %s: %s", diagnosis_id, exc)
        return None


def save_feedback(
    diagnosis_id: str,
    was_correct: bool,
    correct_disease: str | None = None,
    note: str | None = None,
) -> bool:
    """Record the farmer's verdict on a diagnosis. False if the id is unknown or malformed."""
    folder = _dir_for(diagnosis_id)
    if folder is None or not (folder / f"{diagnosis_id}.json").exists():
        return False

    payload = {
        "diagnosis_id": diagnosis_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "was_correct": was_correct,
        "correct_disease": correct_disease,
        "note": note,
    }
    try:
        (folder / f"{diagnosis_id}.feedback.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True
    except OSError as exc:
        log.warning("[capture] could not save feedback for %s: %s", diagnosis_id, exc)
        return False


_EMPTY_STATS = {
    "captured": 0,
    "with_feedback": 0,
    "corrections": 0,
    "splittable": 0,
    "not_splittable": 0,
    "distinct_plots": 0,
    "distinct_farmers": 0,
    "with_location": 0,
    "with_sowing_date": 0,
}


def stats() -> dict:
    """Dataset counters — the moat as a number, plus whether it is actually trainable.

    `not_splittable` is the one to watch. Those records have neither a plot nor a farmer id, so
    they cannot be held out as a group; a model measured on them scores itself on plants it has
    already seen. The count is reported rather than hidden so the gap gets fixed while the data
    is still small.
    """
    root = Path(settings.capture_dir)
    if not root.exists():
        return dict(_EMPTY_STATS)

    records = [p for p in root.rglob("*.json") if not p.name.endswith(".feedback.json")]
    feedback = list(root.rglob("*.feedback.json"))

    corrections = 0
    for path in feedback:
        try:
            if json.loads(path.read_text(encoding="utf-8")).get("was_correct") is False:
                corrections += 1
        except (OSError, json.JSONDecodeError):
            continue

    plots: set[str] = set()
    farmers: set[str] = set()
    splittable = with_location = with_sowing = 0
    for path in records:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        ctx = record.get("context") or {}
        if record.get("split_group"):
            splittable += 1
        if ctx.get("plot_id"):
            plots.add(ctx["plot_id"])
        if ctx.get("farmer_id"):
            farmers.add(ctx["farmer_id"])
        if ctx.get("district") or ctx.get("lat") is not None:
            with_location += 1
        if ctx.get("sowing_date"):
            with_sowing += 1

    return {
        "captured": len(records),
        "with_feedback": len(feedback),
        "corrections": corrections,
        "splittable": splittable,
        "not_splittable": len(records) - splittable,
        "distinct_plots": len(plots),
        "distinct_farmers": len(farmers),
        "with_location": with_location,
        "with_sowing_date": with_sowing,
    }
