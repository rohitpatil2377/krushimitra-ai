"""Pydantic request/response models for the API layer."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import CROPS, LANGS


# --- Auth ---
class OTPRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=20)


class OTPVerify(BaseModel):
    phone: str
    otp: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Vision ---
class DiagnosisOut(BaseModel):
    crop: str
    disease: str          # canonical slug
    confidence: float
    model_version: str = "mock-0"
    symptoms: str | None = None      # what the model reports seeing (English)
    alternative: str | None = None   # second-most-likely slug


class SeverityOut(BaseModel):
    level: str
    severity_pct: float
    risk_level: str
    recommended_action: str
    method: str = "vlm"              # vlm|segmentation|mock|skipped
    evidence: str | None = None


class FieldContext(BaseModel):
    """Who / where / when a photo came from — what turns a capture into a training example.

    Every field is optional so an older app build keeps working, but two of them decide whether
    the dataset is worth anything later, and neither can be repaired in hindsight:

      * `plot_id` / `farmer_id` are the SPLIT GROUP. Without one, the same plant photographed on
        five different days lands in both train and test, and the accuracy we measure is fiction.
        The grouping has to be recorded at capture time or the photos are worth a fraction of
        what they should be.
      * `sowing_date` fixes the crop's age. Purple blotch at 30 days and at 90 days call for
        different advice, and a model that never saw the stage cannot learn the difference.

    Privacy: `farmer_id` is an anonymous per-install id — never a phone number, name or IMEI.
    Coordinates are rounded to ~100 m before storage (see `capture.normalize_context`): enough to
    map disease pressure to a village, not enough to point at a household.
    """
    farmer_id: str | None = Field(default=None, max_length=64)
    plot_id: str | None = Field(default=None, max_length=64)
    district: str | None = Field(default=None, max_length=64)
    taluka: str | None = Field(default=None, max_length=64)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    sowing_date: date | None = None
    crop_stage: str | None = Field(default=None, max_length=32)
    device_model: str | None = Field(default=None, max_length=64)
    os_version: str | None = Field(default=None, max_length=32)
    app_version: str | None = Field(default=None, max_length=32)


class DiagnoseRequest(BaseModel):
    """Disease detection request: the photo as a base64 string + optional crop + field context."""
    image_base64: str
    crop: str | None = None
    # Absent on older app builds; the diagnosis is unaffected, only the dataset is poorer.
    context: FieldContext | None = None


class RichDiagnosisOut(BaseModel):
    """App-facing disease result: detection + severity + Marathi cause/treatment/prevention.

    Two fields carry the product's honesty guarantees and the app must respect both:
      * `identified` is False when the model was not confident enough, or saw no crop. There is
        then NO treatment and NO severity — the app shows "निदान निश्चित नाही" and how to retake
        the photo. Never render an empty treatment list as if it were advice.
      * `model_version` starting with "mock" means SAMPLE DATA, not analysis. The app must badge
        it. (It must not infer this from whether the backend replied — a reachable backend can
        still be serving mocks, which is exactly how the old badge misled.)
    """
    crop: str
    disease: str                      # Marathi display name
    disease_en: str | None = None
    disease_slug: str                 # canonical slug — stable key for the app and analytics
    kind: str                         # fungal|bacterial|viral|pest|abiotic|none
    confidence: float
    identified: bool                  # False => abstained; treatment/severity are absent
    severity: SeverityOut | None = None
    cause: str
    treatment: list[str] = []
    prevention: list[str] = []
    chemicals: list[str] = []         # English active ingredients (future input-seller tie-up)
    dose_note: str | None = None      # mandatory KVK dosage disclaimer when chemicals are named
    curable: bool = True              # False => no spray fixes this; say so plainly
    note: str | None = None           # short honest caveat shown above the advice
    symptoms: str | None = None       # what the model says it saw
    model_version: str = "mock-0"
    diagnosis_id: str | None = None   # feed this back via /vision/feedback to train the model


class DiagnoseFeedbackIn(BaseModel):
    """The farmer's verdict on a diagnosis — the label that makes the captured photo trainable."""
    diagnosis_id: str
    was_correct: bool
    correct_disease: str | None = None   # a slug from labels.py, when the farmer/expert knows
    note: str | None = Field(default=None, max_length=1000)


class FeedbackAck(BaseModel):
    recorded: bool
    message: str


# --- Copilot (the main endpoint) ---
class CopilotResponse(BaseModel):
    transcript: str | None = None
    reply_text: str
    reply_audio_url: str | None = None
    lang: str = "mr"
    diagnosis: DiagnosisOut | None = None
    severity: SeverityOut | None = None


# --- Crop cycles (Digital Twin) ---
# --- Farmer profile ---
class FarmerOut(BaseModel):
    id: int
    phone: str
    name: str | None = None
    village: str | None = None
    district: str | None = None
    preferred_lang: str = "mr"
    created_at: datetime

    model_config = {"from_attributes": True}


class FarmerUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    village: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=64)
    preferred_lang: str | None = Field(default=None, pattern="^(mr|hi|en)$")
    # The anonymous per-install id. Sending it on first login attaches every photo the farmer
    # captured BEFORE signing up to their account, instead of stranding it.
    device_id: str | None = Field(default=None, max_length=64)


# --- Farms (plots) ---
class FarmBase(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=64)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    area_acres: float | None = Field(default=None, gt=0, le=10000)
    soil: str | None = Field(default=None, pattern="^(heavy|medium|light)$")
    irrigation_method: str | None = Field(default=None, pattern="^(drip|sprinkler|flood)$")
    row_spacing_m: float | None = Field(default=None, gt=0, le=20)
    plant_spacing_m: float | None = Field(default=None, gt=0, le=20)
    emitter_lph: float | None = Field(default=None, gt=0, le=200)
    emitters_per_plant: int | None = Field(default=None, ge=1, le=20)


class FarmCreate(FarmBase):
    pass


class FarmUpdate(FarmBase):
    pass


class FarmOut(FarmBase):
    id: int
    farmer_id: int

    model_config = {"from_attributes": True}


# --- Crop cycles (the Digital Crop Twin) ---
class CropCycleCreate(BaseModel):
    farm_id: int
    crop: str = Field(description=f"one of {CROPS}")
    sowing_date: date | None = None
    variety: str | None = Field(default=None, max_length=80)
    notes: str | None = None


class CropCycleUpdate(BaseModel):
    variety: str | None = Field(default=None, max_length=80)
    sowing_date: date | None = None
    last_watered_date: date | None = None
    status: str | None = Field(default=None, pattern="^(active|harvested|abandoned)$")
    harvest_date: date | None = None
    yield_quintal: float | None = Field(default=None, ge=0, le=100000)
    notes: str | None = None


class StageOut(BaseModel):
    stage: str
    stage_mr: str
    days_after_sowing: int | None = None
    total_days: int | None = None
    progress_pct: int | None = None
    cycle_start_label_mr: str | None = None


class ScoreItemOut(BaseModel):
    on: str
    reason: str
    level: str
    raw_penalty: float
    age_days: int
    applied: float


class HealthScoreOut(BaseModel):
    """A score a farmer can interrogate.

    `items` itemises every point deducted, with the date and the reason, because a number that
    cannot be checked is a number that will not be trusted. An empty history scores 100 and the
    note says plainly that "nothing recorded" is not the same as "healthy".
    """
    score: int
    band: str                    # good | fair | poor | critical
    band_mr: str
    items: list[ScoreItemOut] = Field(default_factory=list)
    note: str


class CropCycleOut(BaseModel):
    id: int
    farm_id: int
    crop: str
    variety: str | None = None
    sowing_date: date | None = None
    last_watered_date: date | None = None
    status: str
    harvest_date: date | None = None
    yield_quintal: float | None = None
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CropCycleSummaryOut(CropCycleOut):
    """List-view shape: enough for a dashboard card in ONE request.

    Stage is computed in-process (no query) and the health score is the cached value, so listing
    ten cycles costs one round trip instead of ten — which matters on a 2G connection far more
    than the score being a few minutes stale.
    """
    plot_name: str | None = None
    stage: StageOut
    health_score: int | None = None
    health_band: str | None = None
    health_band_mr: str | None = None


class CropCycleDetailOut(CropCycleOut):
    """Everything a cycle screen needs in one call — a farmer on 2G should not pay for three."""
    farm: FarmOut
    stage: StageOut
    health: HealthScoreOut
    event_count: int = 0


class CropEventCreate(BaseModel):
    type: str = Field(description="sowing|diagnosis|irrigation|treatment|note|weather|harvest")
    title: str | None = Field(default=None, max_length=200)
    body: str | None = None
    data: dict | None = None
    diagnosis_id: str | None = Field(default=None, max_length=32)
    on: date | None = None


class CropEventOut(BaseModel):
    id: int
    crop_cycle_id: int
    type: str
    day_index: int | None = None
    title: str | None = None
    body: str | None = None
    data: dict | None = None
    diagnosis_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Feedback (fuels the data moat) ---
class FeedbackIn(BaseModel):
    message_id: int
    useful: bool
    correction: str | None = None


SUPPORTED_LANGS = LANGS


# --- Weather ---
class CurrentWeatherOut(BaseModel):
    temp_c: float
    feels_like_c: float
    humidity_pct: int
    wind_kph: float
    rain_mm: float
    condition: str            # closed slug (clear|clouds|rain|...) — the app translates it
    observed_at: str


class DayForecastOut(BaseModel):
    date: str                 # yyyy-mm-dd, local to the farm
    temp_min_c: float
    temp_max_c: float
    humidity_pct: int
    rain_mm: float
    rain_chance_pct: int
    wind_kph: float
    condition: str


class AdvisoryOut(BaseModel):
    """What the farmer should DO — the reason this feature exists rather than a weather widget."""
    key: str                  # stable id, for styling and analytics
    level: str                # warning | watch | info
    title: str                # Marathi
    body: str                 # Marathi
    crop: str | None = None   # None = applies whatever the crop


class WeatherOut(BaseModel):
    """Forecast + crop advisories.

    `source` carries the same honesty contract as vision's `model_version`: anything starting
    with "mock" is SAMPLE DATA and the app must badge it, regardless of the call succeeding.
    """
    location_name: str | None = None
    lat: float
    lon: float
    crop: str | None = None
    current: CurrentWeatherOut
    days: list[DayForecastOut] = Field(default_factory=list)
    advisories: list[AdvisoryOut] = Field(default_factory=list)
    source: str


# --- Irrigation ---
class IrrigationOut(BaseModel):
    """How much water, when, and why — from a FAO-56 soil water balance over the forecast.

    Unlike a chemical dose, a water NUMBER is the correct answer here: it is computed from
    physics plus published crop coefficients, and over/under-watering is recoverable. What the
    response must not do is hide the uncertainty, hence `confidence` and `notes`.

    `decision` is one of:
      * `irrigate`    — water today
      * `wait`        — not yet; `next_in_days` says when
      * `rain_coming` — it is due, but rain will cover it
      * `unsure`      — the farmer did not say when they last watered, so "today?" cannot be
                        answered. The interval and depth per turn still are.

    `source` carries the weather provider through: anything starting with "mock" means the plan
    was computed on SAMPLE weather and the app badges it.
    """
    crop: str
    decision: str
    irrigate_today: bool
    reason: str                     # Marathi

    stage: str
    stage_mr: str
    days_after_start: int | None = None

    # The working — shown in English/debug view, and what makes the number auditable.
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

    soil: str
    method: str
    notes: list[str] = Field(default_factory=list)
    confidence: str                 # good | rough
    source: str


# --- Mandi prices ---
class MarketQuoteOut(BaseModel):
    """One mandi's board, enriched with what the farmer actually nets after getting there."""
    market: str
    district_name: str
    market_mr: str | None = None      # Marathi name when known; app falls back to `market`
    district_mr: str | None = None
    commodity: str
    arrival_date: str
    age_days: int
    min_price: float            # all prices: rupees per QUINTAL (100 kg)
    max_price: float
    modal_price: float
    distance_km: float | None = None
    transport_cost: float | None = None
    net_price: float
    trend: str                  # up | down | flat | unknown
    trend_change_pct: float | None = None
    previous_price: float | None = None
    variety: str | None = None
    grade: str | None = None
    is_best: bool = False


class MarketPricesOut(BaseModel):
    """Mandi board ranked by NET realisation, not by headline price.

    A mandi paying more but 200 km away can net less once the lorry is paid, so `quotes` is
    sorted by `net_price` and the top one carries `is_best`.

    What this never does is tell a farmer to sell or to hold — tomorrow's mandi price is not
    predictable, and a confident call that costs someone their crop's value is the same failure
    as a wrong diagnosis. `notes` state what is known and send the farmer to confirm by phone.

    `source` starting with "mock" means SAMPLE DATA and the app badges it.
    """
    crop: str
    price_unit: str = "rs_per_quintal"
    lat: float
    lon: float
    transport_rate_per_qtl_km: float
    quotes: list[MarketQuoteOut] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    history_days: int = 0
    source: str
