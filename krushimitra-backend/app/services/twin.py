"""Digital Crop Twin — the season as a timeline, and a health score you can audit.

Two things live here:

  * **Stage**, reused from the irrigation FAO-56 tables rather than reinvented. One definition of
    "what stage is this crop in" means the twin, the irrigation plan and the weather advisory can
    never disagree about the same field on the same day.

  * **Health score**, deliberately a transparent formula and not a model. A number a farmer
    cannot interrogate is a number they will not trust, so every point deducted is itemised in
    `breakdown` with the date and the reason. When there is enough field data to train something
    better, the breakdown is also the label.

Scoring rules, and why:
  * Only DIAGNOSED problems deduct. An abstained diagnosis ("not sure") carries no severity, so
    it must not quietly lower the score — that would punish the farmer for our uncertainty.
  * Penalties DECAY over ~30 days. A severe blotch six weeks ago that was treated is not the same
    field as one found yesterday, and a score that never recovers gives a farmer no reason to act.
  * `curable=False` problems decay slower: a virus or a wilt does not go away because time passed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.services.irrigation.params import CROP_PARAMS, STAGE_NAMES_MR, stage_for
from app.services.knowledge import lookup

# How much each severity level costs a freshly-found problem.
SEVERITY_PENALTY = {
    "healthy": 0.0,
    "mild": 8.0,
    "moderate": 20.0,
    "severe": 35.0,
    "critical": 50.0,
}
# A treated problem fades from the score over this many days.
RECOVERY_DAYS = 30
# Things no spray fixes fade far more slowly — they are still in the field.
INCURABLE_RECOVERY_DAYS = 120

HEALTH_BANDS = (
    (85, "good", "चांगली"),
    (65, "fair", "ठीक"),
    (40, "poor", "काळजीची"),
    (0, "critical", "गंभीर"),
)


@dataclass
class ScoreItem:
    on: str             # yyyy-mm-dd
    reason: str         # disease slug or event type
    level: str
    raw_penalty: float
    age_days: int
    applied: float      # after decay


@dataclass
class HealthResult:
    score: int
    band: str
    band_mr: str
    items: list[ScoreItem]
    note: str


def band_for(score: int) -> tuple[str, str]:
    for threshold, key, mr in HEALTH_BANDS:
        if score >= threshold:
            return key, mr
    return "critical", "गंभीर"


def health_for(events: list[dict], today: date | None = None) -> HealthResult:
    """Score a cycle from its diagnosis events.

    `events` are dicts with at least `on` (date), `severity_level`, `disease_slug`.
    An empty history scores 100 and says so — "no problems recorded" is not the same claim as
    "this crop is healthy", and the note keeps that distinction honest.
    """
    today = today or date.today()
    score = 100.0
    items: list[ScoreItem] = []

    for ev in events:
        level = (ev.get("severity_level") or "").lower()
        penalty = SEVERITY_PENALTY.get(level)
        if not penalty:
            continue  # abstained or healthy — nothing to deduct

        on = ev.get("on")
        if isinstance(on, str):
            try:
                on = date.fromisoformat(on)
            except ValueError:
                continue
        if not isinstance(on, date):
            continue

        age = max(0, (today - on).days)
        slug = ev.get("disease_slug") or ""
        window = INCURABLE_RECOVERY_DAYS if not lookup(slug).curable else RECOVERY_DAYS
        decay = max(0.0, 1.0 - age / window)
        applied = round(penalty * decay, 1)
        if applied <= 0:
            continue

        score -= applied
        items.append(ScoreItem(
            on=on.isoformat(), reason=slug or "diagnosis", level=level,
            raw_penalty=penalty, age_days=age, applied=applied,
        ))

    final = int(max(0.0, min(100.0, round(score))))
    key, mr = band_for(final)

    if not items:
        note = (
            "अजून कोणतीही अडचण नोंदवलेली नाही. याचा अर्थ पीक निरोगी आहे असा नाही — "
            "फोटो काढून तपासणी केल्यावरच खरी स्थिती कळेल."
        )
    else:
        note = (
            f"{len(items)} नोंदवलेल्या अडचणींवरून हा गुण काढला आहे. जुन्या अडचणींचा परिणाम "
            "हळूहळू कमी होतो; उपचार न होणाऱ्या रोगांचा जास्त काळ राहतो."
        )

    return HealthResult(score=final, band=key, band_mr=mr, items=items, note=note)


def stage_of(crop: str, sowing_date: date | None, today: date | None = None) -> dict:
    """Growth stage of a cycle, using the same FAO-56 table the irrigation plan uses."""
    params = CROP_PARAMS.get((crop or "").lower())
    if params is None:
        return {"stage": "unknown", "stage_mr": STAGE_NAMES_MR["unknown"],
                "days_after_sowing": None, "total_days": None, "progress_pct": None}

    days = None
    if sowing_date is not None:
        delta = ((today or date.today()) - sowing_date).days
        days = delta if delta >= 0 else None

    stage, _kc, _root = stage_for(params, days)
    total = sum(params.stages)
    progress = None
    if days is not None and total:
        progress = int(max(0, min(100, round(100 * days / total))))

    return {
        "stage": stage,
        "stage_mr": STAGE_NAMES_MR.get(stage, STAGE_NAMES_MR["unknown"]),
        "days_after_sowing": days,
        "total_days": total,
        "progress_pct": progress,
        "cycle_start_label_mr": params.cycle_start_mr,
    }
