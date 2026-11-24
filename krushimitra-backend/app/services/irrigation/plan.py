"""The irrigation decision: water today or not, how much, and when next.

A soil-water-balance model (FAO-56 chapter 8), kept deliberately simple because the inputs are
a 5-day forecast and whatever the farmer can tell us — not a sensor network:

    ETc = Kc x ET0                      how much the crop drinks per day
    deficit += ETc - effective rain     how dry the root zone has become
    RAW = AWC x root depth x p          how dry it may get before yield suffers
    irrigate when deficit >= RAW        and apply `deficit / efficiency`

Unlike the chemical dosage policy, giving a water NUMBER is correct here. Dose depends on a
formulation percentage printed on a bottle we cannot see; irrigation depth is computed from
physics and published FAO coefficients, and the failure mode is recoverable. What we must not do
is hide the uncertainty, so every plan carries a confidence and the hand-feel check that real
extension officers teach.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from app.services.irrigation.et import et0_hargreaves
from app.services.irrigation.params import (
    CROP_PARAMS,
    DEFAULT_METHOD,
    DEFAULT_SOIL,
    METHODS,
    SOILS,
    STAGE_LOCATIVE_MR,
    STAGE_NAMES_MR,
    stage_for,
)
from app.services.weather.base import Forecast

# 1 mm over 1 hectare = 10 m3; 1 acre = 0.4047 ha.
MM_TO_M3_PER_ACRE = 4.047
# Canopy interception and evaporation take the first ~2 mm; of the rest, some runs off.
RAIN_INTERCEPTION_MM = 2.0
RAIN_INFILTRATION_FRACTION = 0.85
MAX_LOOKAHEAD_DAYS = 14

# Drip is not a small flood. Its whole advantage is replacing what the crop drank yesterday,
# little and often, keeping the root zone near field capacity instead of swinging between
# saturated and depleted. So for drip the interval comes from the soil's holding capacity in
# DAYS, not from waiting for the FAO depletion trigger — on a light soil in summer, waiting for
# 50 mm of depletion would mean a 10-day gap that no pomegranate grower would accept.
# Flood and sprinkler keep the classic deficit-refill logic, which is how they are actually run.
DRIP_INTERVAL_DAYS = {"light": 1, "medium": 2, "heavy": 2}

_DEV_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")


def _n(value: float | int, decimals: int = 0) -> str:
    """Devanagari digits for Marathi prose, matching knowledge.py and the weather advisories."""
    return f"{value:.{decimals}f}".translate(_DEV_DIGITS)


def effective_rain_mm(rain_mm: float) -> float:
    return round(max(0.0, rain_mm - RAIN_INTERCEPTION_MM) * RAIN_INFILTRATION_FRACTION, 2)


@dataclass
class IrrigationPlan:
    decision: str                 # irrigate | wait | rain_coming | unsure
    irrigate_today: bool
    reason: str                   # Marathi
    crop: str
    stage: str
    stage_mr: str
    days_after_start: int | None

    kc: float
    et0_mm: float
    etc_mm: float
    root_depth_m: float
    awc_mm_per_m: float
    raw_mm: float
    deficit_mm: float
    depletion_pct: int

    net_mm: float
    gross_mm: float
    litres_per_plant: float | None = None
    m3_per_acre: float | None = None
    run_hours: float | None = None

    next_in_days: int | None = None
    next_date: str | None = None
    rain_next_3d_mm: float = 0.0

    method: str = DEFAULT_METHOD
    soil: str = DEFAULT_SOIL
    notes: list[str] = field(default_factory=list)
    # "good" when the farmer gave a cycle date and a last-watered day; "rough" otherwise.
    confidence: str = "rough"
    # Carries the weather provider through, so sample weather produces a badged plan.
    source: str = "mock-0"


def _daily_et(forecast: Forecast, lat: float) -> list[tuple[date, float, float]]:
    """(day, ET0 mm, effective rain mm) for each forecast day."""
    out: list[tuple[date, float, float]] = []
    for day in forecast.days:
        try:
            d = datetime.strptime(day.date, "%Y-%m-%d").date()
        except ValueError:
            continue
        out.append((d, et0_hargreaves(day.temp_min_c, day.temp_max_c, lat, d),
                    effective_rain_mm(day.rain_mm)))
    return out


def build_plan(
    forecast: Forecast,
    lat: float,
    crop: str,
    *,
    days_after_start: int | None = None,
    last_watered_days_ago: int | None = None,
    soil: str = DEFAULT_SOIL,
    method: str = DEFAULT_METHOD,
    row_spacing_m: float | None = None,
    plant_spacing_m: float | None = None,
    emitter_lph: float | None = None,
    emitters_per_plant: int = 1,
) -> IrrigationPlan | None:
    """None when we have no parameters for this crop — better than inventing a coefficient."""
    params = CROP_PARAMS.get((crop or "").lower())
    series = _daily_et(forecast, lat)
    if params is None or not series:
        return None

    soil_p = SOILS.get(soil, SOILS[DEFAULT_SOIL])
    method_p = METHODS.get(method, METHODS[DEFAULT_METHOD])

    stage, kc, root_m = stage_for(params, days_after_start)
    _, et0_today, pe_today = series[0]
    etc_today = round(kc * et0_today, 2)

    # How much water the root zone holds, and how much of it the crop may spend before it hurts.
    taw_mm = soil_p.awc_mm_per_m * root_m
    raw_mm = round(taw_mm * params.depletion_fraction, 1)

    # --- where the soil is now ---------------------------------------------------------------
    # With no last-watered day we cannot know the current deficit, so we answer the question we
    # CAN answer (the interval and the depth per turn) and say the other is unknown.
    if last_watered_days_ago is None:
        deficit = 0.0
    else:
        # Past days are charged at today's ETc: the forecast has no history, and over the few
        # days since an irrigation the demand barely moves. Rain since then is NOT known to us,
        # which is why the notes tell the farmer to count a rain day as the last watering.
        deficit = max(0.0, min(taw_mm, etc_today * max(0, last_watered_days_ago)))

    depletion_pct = int(round(100 * deficit / taw_mm)) if taw_mm else 0
    rain_3d = round(sum(pe for _, _, pe in series[:3]), 1)

    # --- forward projection: when does the deficit cross the trigger? -------------------------
    projected = deficit
    next_in_days: int | None = None
    for offset in range(MAX_LOOKAHEAD_DAYS):
        if offset < len(series):
            _, et0_day, pe_day = series[offset]
        else:
            _, et0_day, pe_day = series[-1][0], series[-1][1], 0.0  # beyond forecast: assume dry
        projected = max(0.0, min(taw_mm, projected + kc * et0_day - pe_day))
        if projected >= raw_mm:
            # Crossing the trigger during day `offset` means water is needed the NEXT morning,
            # so the farmer-facing count is offset + 1 days from today.
            next_in_days = offset + 1
            break

    # --- how much, and when: the strategy depends on the METHOD ------------------------------
    high_frequency = method_p.slug == "drip"
    rain_2d = round(sum(pe for _, _, pe in series[:2]), 1)

    if high_frequency:
        target_interval = DRIP_INTERVAL_DAYS.get(soil_p.slug, 2)
        days_since = last_watered_days_ago
        # Replace what the crop has drunk since the last turn, never more than the root zone
        # can hold on to.
        span = max(target_interval, days_since if days_since is not None else target_interval)
        net_mm = round(min(etc_today * span, raw_mm), 1)
        needs_water = days_since is not None and days_since >= target_interval
        due_in = (
            None if days_since is None
            else max(0, target_interval - days_since)
        )
    else:
        target_interval = None
        net_mm = round(max(raw_mm * 0.5, deficit if deficit > 0 else raw_mm), 1)
        needs_water = deficit >= raw_mm
        due_in = next_in_days

    gross_mm = round(net_mm / method_p.efficiency, 1)

    # --- the decision -------------------------------------------------------------------------
    if last_watered_days_ago is None:
        decision = "unsure"
        interval = target_interval if high_frequency else (next_in_days or 1)
        where = STAGE_LOCATIVE_MR.get(stage)
        subject = f"{where} असलेल्या पिकाला" if where else "या पिकाला"
        reason = (
            f"शेवटचे पाणी कधी दिले हे सांगितले नाही, म्हणून 'आज पाणी द्यावे का' हे नक्की सांगता येत नाही. "
            f"या हवामानात {subject} दर {_n(max(1, interval))} दिवसांनी "
            f"सुमारे {_n(gross_mm)} मिमी पाणी लागते."
        )
    elif needs_water and rain_2d >= net_mm * 0.8:
        decision = "rain_coming"
        reason = (
            f"पाणी देण्याची वेळ झाली आहे, पण पुढील दोन दिवसांत सुमारे {_n(rain_2d)} मिमी पाऊस "
            f"अपेक्षित आहे — तो पिकाची गरज भरून काढेल. आज पाणी देऊ नका; पाऊस झाला नाही तरच द्या."
        )
    elif needs_water:
        decision = "irrigate"
        if high_frequency:
            reason = (
                f"आज पाणी द्या. शेवटच्या पाण्यानंतर {_n(last_watered_days_ago)} दिवस झाले आहेत आणि "
                f"पीक रोज सुमारे {_n(etc_today, 1)} मिमी पाणी वापरत आहे."
            )
        else:
            reason = (
                f"आज पाणी द्या. मुळाच्या भागातील ओलावा सुमारे {_n(depletion_pct)}% कमी झाला आहे, आणि "
                f"या पिकाला {_n(params.depletion_fraction * 100)}% पेक्षा जास्त घट सहन होत नाही."
            )
    else:
        decision = "wait"
        rain_covers_it = due_in is None and rain_3d > 0
        if due_in is None:
            when = "पुढील काही दिवसांत"
        elif due_in <= 1:
            when = "उद्या"
        else:
            when = f"अंदाजे {_n(due_in)} दिवसांनी"

        if rain_covers_it:
            # Not "water in a few days" — the rain is doing the watering. Say that instead of
            # filling the usual slot with a vague phrase.
            reason = (
                f"आज पाणी देण्याची गरज नाही. पुढील तीन दिवसांत सुमारे {_n(rain_3d)} मिमी पाऊस "
                "पिकाची गरज भागवत आहे. पाऊस थांबल्यावर मातीचा ओलावा हाताने तपासा आणि मग ठरवा."
            )
        elif high_frequency:
            reason = (
                f"आज पाणी देण्याची गरज नाही. या जमिनीत ठिबकने दर {_n(target_interval)} दिवसांनी "
                f"पाणी पुरेसे आहे — पुढील पाणी {when}."
            )
        else:
            reason = (
                f"आज पाणी देण्याची गरज नाही — ओलावा सुमारे {_n(depletion_pct)}% कमी झाला आहे, "
                f"मर्यादा {_n(params.depletion_fraction * 100)}% आहे. पुढील पाणी {when}."
            )

    next_in_days = due_in if high_frequency else next_in_days

    next_date = (
        (series[0][0] + timedelta(days=next_in_days)).isoformat()
        if next_in_days is not None else None
    )

    # --- practical units ----------------------------------------------------------------------
    litres_per_plant = None
    run_hours = None
    if row_spacing_m and plant_spacing_m:
        area_per_plant = row_spacing_m * plant_spacing_m
        litres_per_plant = round(gross_mm * area_per_plant, 1)   # 1 mm over 1 m2 = 1 litre
        if emitter_lph and emitters_per_plant > 0:
            run_hours = round(litres_per_plant / (emitter_lph * emitters_per_plant), 1)

    notes = _notes(
        params=params, stage=stage, root_m=root_m, method=method_p.slug,
        last_watered_days_ago=last_watered_days_ago, days_after_start=days_after_start,
    )

    # A run time this long means the system cannot deliver the day's demand in one session.
    # Saying so is more useful than printing "14 तास" and leaving the farmer to wonder.
    if run_hours is not None and run_hours > 6:
        notes.insert(0, (
            f"या हिशोबाने ठिबक सुमारे {_n(run_hours)} तास चालवावे लागेल — म्हणजे संचाची क्षमता "
            "कमी पडते. सकाळ-संध्याकाळ दोन वेळा पाणी द्या, किंवा जास्त क्षमतेचे (उदा. ८ लिटर/तास) "
            "ड्रिपर वापरा."
        ))

    return IrrigationPlan(
        decision=decision,
        irrigate_today=(decision == "irrigate"),
        reason=reason,
        crop=params.slug,
        stage=stage,
        stage_mr=STAGE_NAMES_MR[stage],
        days_after_start=days_after_start,
        kc=round(kc, 2),
        et0_mm=et0_today,
        etc_mm=etc_today,
        root_depth_m=round(root_m, 2),
        awc_mm_per_m=soil_p.awc_mm_per_m,
        raw_mm=raw_mm,
        deficit_mm=round(deficit, 1),
        depletion_pct=depletion_pct,
        net_mm=net_mm,
        gross_mm=gross_mm,
        litres_per_plant=litres_per_plant,
        m3_per_acre=round(gross_mm * MM_TO_M3_PER_ACRE, 1),
        run_hours=run_hours,
        next_in_days=next_in_days,
        next_date=next_date,
        rain_next_3d_mm=rain_3d,
        method=method_p.slug,
        soil=soil_p.slug,
        notes=notes,
        confidence=(
            "good" if days_after_start is not None and last_watered_days_ago is not None
            else "rough"
        ),
        source=forecast.source,
    )


def _notes(*, params, stage, root_m, method, last_watered_days_ago, days_after_start) -> list[str]:
    """The caveats and the crop-stage coaching — what an extension officer would add out loud."""
    out: list[str] = []

    # Always: the oldest soil moisture sensor there is.
    out.append(
        "खात्री करण्यासाठी मुळाच्या भागातील मूठभर माती घेऊन दाबा — घट्ट गोळा झाला तर ओलावा "
        "पुरेसा आहे; भुरभुरीत पडली तर पाणी द्या."
    )

    if params.slug == "onion":
        out.append(
            f"कांद्याची मुळे फक्त सुमारे {_n(root_m * 100)} सेंमी खोल जातात. एकदम भरपूर पाणी "
            "देण्यापेक्षा थोडे-थोडे पण वारंवार द्या — जास्त पाणी दिले तर ते मुळांच्या खाली "
            "निघून जाते आणि मानकुज वाढते."
        )
        if stage == "late":
            out.append(
                "काढणीच्या १०–१५ दिवस आधी पाणी पूर्णपणे बंद करा. ओल्या मातीतून काढलेला कांदा "
                "साठवणीत सडतो."
            )
    elif params.slug == "soybean" and stage == "mid":
        out.append(
            "शेंगा भरण्याचा हा काळ आहे — याच अवस्थेत पाण्याचा ताण पडला तर उत्पादनात सर्वात "
            "मोठी घट होते. या काळात पाणी चुकवू नका."
        )
    elif params.slug == "pomegranate":
        out.append(
            "ओलावा एकसारखा ठेवा. कोरड्या दिवसांनंतर अचानक भरपूर पाणी दिले की फळे तडकतात."
        )

    if method == "drip":
        out.append(
            "ठिबकने रोज किंवा दिवसाआड थोडे पाणी देणे सर्वोत्तम — मुळांजवळ ओलावा एकसारखा राहतो "
            "आणि खत पाण्यातून देता येते. एकदम भरपूर पाणी सोडल्यास ठिबकचा फायदाच जातो."
        )

    if method == "flood":
        out.append(
            "मोकळ्या पाण्यात सुमारे ४५% पाणी वाया जाते. ठिबकने तेच पीक जवळपास निम्म्या पाण्यात निघते."
        )

    if last_watered_days_ago is not None:
        out.append(
            "शेवटच्या पाण्यानंतर पाऊस पडला असेल, तर 'शेवटचे पाणी' म्हणून त्या पावसाचा दिवस धरा."
        )
    if days_after_start is None:
        out.append(
            f"{params.cycle_start_mr} सांगितली तर पिकाच्या अवस्थेनुसार नेमका हिशोब मिळेल."
        )

    out.append(
        "हा हिशोब तापमानावरून काढलेला अंदाज आहे (सौर किरणोत्सर्ग प्रत्यक्ष मोजलेला नाही), "
        "म्हणून प्रत्यक्ष गरज सुमारे २०% कमी-जास्त असू शकते."
    )
    return out
