"""Crop, soil and method parameters for the water balance — FAO-56 single crop coefficient.

Every number here is a published value, not a guess, and each carries its source. They are the
difference between "water your onions" and "give 14 mm today, about 2.1 litres per plant".

Three things in this file do most of the work:

  * **Kc** (crop coefficient) scales reference ET0 to this crop at this growth stage.
  * **Root depth**, which decides how much water the soil can actually hold for the plant.
  * **p**, the fraction of that water the crop can lose before it suffers. Onion's p is 0.30
    against soybean's 0.50 — onion is shallow-rooted and genuinely sensitive, so it needs LITTLE
    water OFTEN. Getting this wrong is the single most common irrigation mistake in onion.

Sources: FAO-56 Tables 12 (Kc), 22 (root depth, p) and 11 (stage lengths), adjusted to
Maharashtra crop durations (FAO's stage lengths are regional and its onion figures assume a
150-day Mediterranean crop; rabi onion here runs ~120 days from transplant).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CropParams:
    slug: str
    # Stage lengths in days: initial, development, mid-season, late-season.
    stages: tuple[int, int, int, int]
    kc_ini: float
    kc_mid: float
    kc_end: float
    root_min_m: float          # at emergence / start of cycle
    root_max_m: float          # at full development
    depletion_fraction: float  # p — how dry it may get before yield is hit
    perennial: bool = False
    # What the "cycle start" date means to the farmer, so the app asks the right question.
    cycle_start_mr: str = "लागवडीची तारीख"


CROP_PARAMS: dict[str, CropParams] = {
    # Onion, dry. p=0.30 and a shallow root zone => frequent, light irrigation. FAO-56 lists
    # Kc_mid 1.05 and a 0.3-0.6 m root depth; stage lengths shortened to a 120-day rabi crop.
    "onion": CropParams(
        slug="onion",
        stages=(15, 25, 55, 25),
        kc_ini=0.70, kc_mid=1.05, kc_end=0.75,
        root_min_m=0.15, root_max_m=0.45,
        depletion_fraction=0.30,
        cycle_start_mr="लागवडीची (पुनर्लागवडीची) तारीख",
    ),
    # Soybean. Deep rooting and a tolerant p, but pod-fill moisture stress is where the yield
    # goes. FAO-56: Kc_mid 1.15, root 0.6-1.3 m, p 0.50. ~100-day kharif crop here.
    "soybean": CropParams(
        slug="soybean",
        stages=(15, 20, 45, 20),
        kc_ini=0.40, kc_mid=1.15, kc_end=0.50,
        root_min_m=0.20, root_max_m=0.90,
        depletion_fraction=0.50,
        cycle_start_mr="पेरणीची तारीख",
    ),
    # Pomegranate: perennial, so the "cycle" is the bahar. Measured Kc for drip-irrigated
    # pomegranate in the Solapur belt sits around 0.45 early to 0.70 at full fruit load.
    "pomegranate": CropParams(
        slug="pomegranate",
        stages=(30, 45, 75, 30),
        kc_ini=0.45, kc_mid=0.70, kc_end=0.60,
        root_min_m=0.40, root_max_m=1.00,
        depletion_fraction=0.50,
        perennial=True,
        cycle_start_mr="बहार धरल्याची तारीख",
    ),
}

STAGE_NAMES_MR = {
    "initial": "सुरुवातीची अवस्था",
    "development": "वाढीची अवस्था",
    "mid": "जोमाची अवस्था",
    "late": "पक्वतेची अवस्था",
    "unknown": "अवस्था माहीत नाही",
}

# Locative ("in the X stage"). Kept as whole phrases rather than built by appending a suffix:
# Marathi declines the noun ("अवस्था" -> "अवस्थेत"), so string concatenation produces nonsense.
# "unknown" has no locative form on purpose — the caller drops the clause instead.
STAGE_LOCATIVE_MR = {
    "initial": "सुरुवातीच्या अवस्थेत",
    "development": "वाढीच्या अवस्थेत",
    "mid": "जोमाच्या अवस्थेत",
    "late": "पक्वतेच्या अवस्थेत",
}


@dataclass(frozen=True)
class SoilParams:
    slug: str
    mr: str
    # Total available water, mm per metre of root depth (FAO-56 Table 19).
    awc_mm_per_m: float


SOILS: dict[str, SoilParams] = {
    "heavy": SoilParams("heavy", "काळी भारी जमीन", 180.0),
    "medium": SoilParams("medium", "मध्यम काळी जमीन", 150.0),
    "light": SoilParams("light", "हलकी / मुरमाड जमीन", 100.0),
}
DEFAULT_SOIL = "medium"


@dataclass(frozen=True)
class MethodParams:
    slug: str
    mr: str
    efficiency: float   # fraction of applied water that reaches the root zone


METHODS: dict[str, MethodParams] = {
    "drip": MethodParams("drip", "ठिबक सिंचन", 0.90),
    "sprinkler": MethodParams("sprinkler", "तुषार सिंचन", 0.75),
    "flood": MethodParams("flood", "मोकळे पाणी / पाट", 0.55),
}
DEFAULT_METHOD = "drip"


def stage_for(params: CropParams, days_after_start: int | None) -> tuple[str, float, float]:
    """(stage key, Kc, root depth in m) for a crop this many days into its cycle.

    Kc is interpolated across the development and late stages exactly as FAO-56 prescribes,
    rather than stepped — a crop does not jump from Kc 0.40 to 1.15 overnight.

    With no cycle date we return the mid-season values and the caller flags the answer as a
    rough estimate. That is better than refusing: mid-season is the conservative middle of the
    range, and the app asks for the date to sharpen it.
    """
    ini, dev, mid, late = params.stages
    if days_after_start is None:
        return "unknown", params.kc_mid, params.root_max_m

    d = max(0, days_after_start)
    total = ini + dev + mid + late
    root_span = params.root_max_m - params.root_min_m

    if d <= ini:
        return "initial", params.kc_ini, params.root_min_m
    if d <= ini + dev:
        frac = (d - ini) / dev if dev else 1.0
        return (
            "development",
            params.kc_ini + frac * (params.kc_mid - params.kc_ini),
            params.root_min_m + frac * root_span,
        )
    if d <= ini + dev + mid:
        return "mid", params.kc_mid, params.root_max_m
    if d <= total:
        frac = (d - ini - dev - mid) / late if late else 1.0
        return (
            "late",
            params.kc_mid + frac * (params.kc_end - params.kc_mid),
            params.root_max_m,
        )

    # Past harvest. For a perennial the next bahar has effectively begun; for an annual the
    # farmer's date is stale, so hold at the end value rather than extrapolating off a cliff.
    if params.perennial:
        return "initial", params.kc_ini, params.root_max_m
    return "late", params.kc_end, params.root_max_m
