"""Turn a forecast into what a farmer should actually DO — the point of the weather feature.

A temperature number is a commodity; every app has it. The value is the sentence after it.
So the rules here are deliberately specific to the three Phase-1 crops and to Maharashtra's real
disease pressure, and every threshold carries the agronomy that justifies it.

Two policies carry over from the vision module and are not optional:
  * NO DOSAGES. These advisories name cultural actions and what to go and look at. The moment a
    chemical is involved the farmer is sent to the diagnose flow or to their KVK.
  * NO INVENTED CERTAINTY. Weather predicts *conditions favourable to* a disease, never the
    disease itself. The wording says "look for these signs", not "you have this".

The Marathi lives here rather than in the app for the same reason the disease advice does: it is
agronomic content, not UI chrome, and it must read the same whichever client asks for it.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.weather.base import Forecast

# Field-practical thresholds (not comfort thresholds).
RAIN_WASHES_SPRAY_MM = 2.0      # ~2 mm on a sprayed leaf is enough to take the deposit off
RAIN_LIKELY_PCT = 60
DRY_ENOUGH_PCT = 30
DRY_ENOUGH_MM = 1.0
WIND_DRIFT_KPH = 20.0           # above this a fine spray drifts off the target row
HEAT_STRESS_C = 38.0
SPRAY_WINDOW_DAYS = 2


# Numbers inside Marathi prose use Devanagari digits, matching knowledge.py and the app's Marathi
# strings. (The forecast cards keep Latin digits — Marathi print separates prose from data tables
# the same way.)
_DEV_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")


def _n(value: float | int, decimals: int = 0) -> str:
    return f"{value:.{decimals}f}".translate(_DEV_DIGITS)


@dataclass(frozen=True)
class Advisory:
    key: str          # stable id — the app can style or suppress by key, and analytics can count it
    level: str        # warning | watch | info
    title: str        # Marathi
    body: str         # Marathi
    crop: str | None = None


_LEVEL_ORDER = {"warning": 0, "watch": 1, "info": 2}
MAX_ADVISORIES = 5  # a farmer reads three things; twelve warnings is the same as none


def _head(forecast: Forecast, days: int) -> list:
    return forecast.days[:days]


def _rain_coming(forecast: Forecast, days: int = SPRAY_WINDOW_DAYS) -> tuple[bool, float]:
    """(is rain expected in the window, total mm)."""
    window = _head(forecast, days)
    total = sum(d.rain_mm for d in window)
    likely = any(
        d.rain_mm >= RAIN_WASHES_SPRAY_MM or d.rain_chance_pct >= RAIN_LIKELY_PCT for d in window
    )
    return likely, total


def _dry_run_days(forecast: Forecast) -> int:
    """Leading consecutive forecast days with effectively no rain."""
    count = 0
    for day in forecast.days:
        if day.rain_mm < DRY_ENOUGH_MM and day.rain_chance_pct < DRY_ENOUGH_PCT:
            count += 1
        else:
            break
    return count


def _humid_warm_run(forecast: Forecast, min_h: int, lo_t: float, hi_t: float) -> int:
    """Consecutive leading days whose humidity and temperature both sit in the risk band."""
    count = 0
    for day in forecast.days:
        mid_t = (day.temp_min_c + day.temp_max_c) / 2
        if day.humidity_pct >= min_h and lo_t <= mid_t <= hi_t:
            count += 1
        else:
            break
    return count


# --- Universal: the spray window ------------------------------------------------------------
# Worth more rupees to a farmer than any forecast number. A spray washed off by rain three hours
# later is the whole bottle wasted plus the labour plus a lost week of disease control.

def _spray_advisories(forecast: Forecast) -> list[Advisory]:
    out: list[Advisory] = []
    rain_soon, rain_mm = _rain_coming(forecast)
    current = forecast.current
    window = _head(forecast, SPRAY_WINDOW_DAYS)
    max_wind = max([current.wind_kph] + [d.wind_kph for d in window], default=0.0)
    max_temp = max([d.temp_max_c for d in window], default=current.temp_c)

    if rain_soon:
        out.append(Advisory(
            key="no_spray_rain",
            level="warning",
            title="आज फवारणी करू नका",
            body=(
                f"पुढील {_n(SPRAY_WINDOW_DAYS)} दिवसांत सुमारे {_n(rain_mm)} मिमी पाऊस अपेक्षित आहे. "
                "आत्ता फवारणी केल्यास औषध पानांवरून धुऊन जाईल — औषध, मजुरी आणि वेळ तिन्ही वाया जातील. "
                "पाऊस थांबून पाने पूर्ण सुकल्यावरच फवारणी करा."
            ),
        ))
    elif max_wind < WIND_DRIFT_KPH:
        out.append(Advisory(
            key="spray_window_ok",
            level="info",
            title="फवारणीसाठी योग्य दिवस",
            body=(
                f"पुढील {_n(SPRAY_WINDOW_DAYS)} दिवस कोरडे आहेत आणि वारा कमी आहे. "
                "फवारणी सकाळी लवकर किंवा संध्याकाळी करा — दुपारच्या उन्हात औषध पानावर बसण्याआधीच उडून जाते."
            ),
        ))

    if max_wind >= WIND_DRIFT_KPH:
        out.append(Advisory(
            key="wind_drift",
            level="watch",
            title="वारा जास्त आहे",
            body=(
                f"ताशी सुमारे {_n(max_wind)} किमी वेगाने वारा आहे. या वाऱ्यात फवारलेले औषध उडून "
                "शेजारच्या शेतात जाते आणि पिकावर नीट बसत नाही. वारा कमी होईपर्यंत थांबा."
            ),
        ))

    if max_temp >= HEAT_STRESS_C:
        out.append(Advisory(
            key="heat_stress",
            level="watch",
            title="कडक उन्हाचा इशारा",
            body=(
                f"कमाल तापमान {_n(max_temp)}°C पर्यंत जाईल. दुपारी १२ ते ४ या वेळेत फवारणी किंवा "
                "पाणी देणे टाळा. पाणी पहाटे किंवा सूर्यास्तानंतर द्या, म्हणजे बाष्पीभवनाने वाया जाणार नाही."
            ),
        ))
    return out


# --- Onion ------------------------------------------------------------------------------------

def _onion_advisories(forecast: Forecast) -> list[Advisory]:
    out: list[Advisory] = []
    _, rain_mm = _rain_coming(forecast, days=3)
    humid_run = _humid_warm_run(forecast, min_h=80, lo_t=15, hi_t=30)
    dry_run = _dry_run_days(forecast)
    first = forecast.days[0] if forecast.days else None

    # Alternaria porri and Stemphylium vescarium both need warm, humid, leaf-wet conditions.
    if humid_run >= 1:
        h = forecast.days[0].humidity_pct
        t = (forecast.days[0].temp_min_c + forecast.days[0].temp_max_c) / 2
        out.append(Advisory(
            key="onion_blotch_risk", level="warning", crop="onion",
            title="कांदा: करपा पसरण्यासाठी पोषक हवामान",
            body=(
                f"आर्द्रता {_n(h)}% आणि तापमान सुमारे {_n(t)}°C — जांभळा करपा (Alternaria) आणि "
                "स्टेम्फिलियम करप्यासाठी हे अगदी अनुकूल हवामान आहे. पानांवर लांबट तपकिरी-जांभळे "
                "डाग दिसतात का आजच पाहा. पाणी ठिबकने द्या, पानांवर फवारू नका — ओली पाने म्हणजे रोगाला आमंत्रण."
            ),
        ))

    if first and first.temp_min_c <= 15 and first.humidity_pct >= 85:
        out.append(Advisory(
            key="onion_downy_mildew", level="watch", crop="onion",
            title="कांदा: केवडा होण्याची शक्यता",
            body=(
                f"किमान तापमान {_n(first.temp_min_c)}°C व आर्द्रता {_n(first.humidity_pct)}% — थंड आणि "
                "दमट हवामान केवड्याला (डाऊनी मिल्ड्यू) पोषक असते. पानांवर फिकट पिवळसर पट्टे आणि "
                "त्यावर जांभळट बुरशीचा थर दिसतो का पाहा."
            ),
        ))

    # Thrips tabaci builds up in hot dry spells, and its feeding scars are the wound through
    # which purple blotch enters — so a dry spell is an early warning for a wet-weather disease.
    if dry_run >= 3 and first and first.temp_max_c >= 33 and first.humidity_pct <= 55:
        out.append(Advisory(
            key="onion_thrips_surge", level="watch", crop="onion",
            title="कांदा: फुलकिडे वाढण्याची शक्यता",
            body=(
                f"सुमारे {_n(dry_run)} दिवस कोरडे व उष्ण हवामान राहील. अशा हवामानात फुलकिडे (थ्रिप्स) "
                "झपाट्याने वाढतात. पातीच्या बेचक्यात पांढरे-चंदेरी ओरखडे दिसतात का पाहा. "
                "फुलकिड्यांनी केलेल्या जखमांमधूनच पुढे करपा शिरतो, म्हणून आताच लक्ष द्या."
            ),
        ))

    if rain_mm >= 10:
        out.append(Advisory(
            key="onion_harvest_rain", level="watch", crop="onion",
            title="कांदा: काढणीच्या काळात पाऊस",
            body=(
                f"पुढील ३ दिवसांत सुमारे {_n(rain_mm)} मिमी पाऊस अपेक्षित आहे. काढणी जवळ आली असल्यास "
                "१०–१५ दिवस आधीच पाणी बंद करा. ओल्या मातीतून काढलेला कांदा साठवणीत सडतो — "
                "नुकसान शेतात नाही, चाळीत होते."
            ),
        ))
    return out


# --- Soybean ----------------------------------------------------------------------------------

def _soybean_advisories(forecast: Forecast) -> list[Advisory]:
    out: list[Advisory] = []
    _, rain_3d = _rain_coming(forecast, days=3)
    rust_run = _humid_warm_run(forecast, min_h=85, lo_t=18, hi_t=28)
    dry_run = _dry_run_days(forecast)
    first = forecast.days[0] if forecast.days else None

    if rain_3d >= 60:
        out.append(Advisory(
            key="soybean_waterlog", level="warning", crop="soybean",
            title="सोयाबीन: पाणी साचण्याचा धोका",
            body=(
                f"पुढील ३ दिवसांत सुमारे {_n(rain_3d)} मिमी पाऊस अपेक्षित आहे. सरी आणि चर मोकळे "
                "आहेत ना ते आजच पाहा. सोयाबीनच्या मुळाशी ४८ तासांपेक्षा जास्त पाणी साचले की "
                "मुळकुज होते आणि पाने पिवळी पडून झाड वाळते."
            ),
        ))

    if rust_run >= 2:
        out.append(Advisory(
            key="soybean_rust", level="warning", crop="soybean",
            title="सोयाबीन: तांबेरा पसरण्याचा धोका",
            body=(
                f"सलग {_n(rust_run)} दिवस ८५%+ आर्द्रता आणि १८–२८°C तापमान राहणार आहे — तांबेरा "
                "(रस्ट) पसरण्यासाठी नेमके हेच हवामान लागते. खालच्या पानांच्या मागच्या बाजूला "
                "बारीक तपकिरी-तांबूस ठिपके दिसतात का पाहा. दिसल्यास लगेच फोटो काढून निदान करा."
            ),
        ))

    if dry_run >= 5 and first and first.temp_max_c >= 33:
        out.append(Advisory(
            key="soybean_dry_spell", level="watch", crop="soybean",
            title="सोयाबीन: पाण्याचा ताण",
            body=(
                f"सुमारे {_n(dry_run)} दिवस पाऊस नाही आणि तापमान {_n(first.temp_max_c)}°C पर्यंत जाईल. "
                "फुलोरा आणि शेंगा भरण्याच्या अवस्थेत पाण्याचा ताण पडला तर उत्पादनात सर्वात मोठी "
                "घट होते. शक्य असल्यास एक संरक्षित पाणी द्या."
            ),
        ))
    return out


# --- Pomegranate --------------------------------------------------------------------------------

def _pomegranate_advisories(forecast: Forecast) -> list[Advisory]:
    out: list[Advisory] = []
    _, rain_2d = _rain_coming(forecast, days=2)
    first = forecast.days[0] if forecast.days else None
    humid = first.humidity_pct if first else 0

    # Telya (Xanthomonas axonopodis pv. punicae) is the defining problem of the Solapur-Sangli-
    # Nashik belt. It is splash- and contact-spread, so rain is not a risk factor, it is the vector.
    if rain_2d >= 5 or humid >= 85:
        out.append(Advisory(
            key="pomegranate_telya", level="warning", crop="pomegranate",
            title="डाळिंब: तेल्या पसरण्याचा मोठा धोका",
            body=(
                f"पाऊस ({_n(rain_2d)} मिमी) आणि {_n(humid)}% आर्द्रता — तेल्या (बॅक्टेरियल ब्लाइट) "
                "सर्वात वेगाने याच हवामानात पसरतो. पानांवर व फळांवर तेलकट काळपट डाग दिसतात का "
                "आजच पाहा. बाग ओली असताना झाडांमधून फिरू नका — रोग हातांनी आणि कपड्यांनीच "
                "एका झाडावरून दुसऱ्यावर जातो."
            ),
        ))

    dry_run = _dry_run_days(forecast)
    later_rain = sum(d.rain_mm for d in forecast.days[dry_run:dry_run + 2])
    if dry_run >= 3 and later_rain >= 10:
        out.append(Advisory(
            key="pomegranate_cracking", level="warning", crop="pomegranate",
            title="डाळिंब: फळ तडकण्याचा धोका",
            body=(
                f"सुमारे {_n(dry_run)} कोरड्या दिवसांनंतर {_n(later_rain)} मिमी पाऊस येत आहे. "
                "जमिनीतील ओलावा अचानक वाढला की फळाची साल ताण सहन करू शकत नाही आणि फळे तडकतात. "
                "आतापासून ठिबकने थोडे-थोडे पाणी देत राहा, म्हणजे ओलावा एकसारखा राहील."
            ),
        ))

    if first and humid >= 80 and first.rain_mm >= 2:
        out.append(Advisory(
            key="pomegranate_anthracnose", level="watch", crop="pomegranate",
            title="डाळिंब: अँथ्रॅक्नोज शक्यता",
            body=(
                "दमट व पावसाळी हवामानात फळांवर खोलगट काळे डाग येतात. गळलेली फळे, पाने आणि "
                "वाळलेल्या फांद्या बागेबाहेर काढून जाळा — रोगाचा साठा तिथेच राहतो."
            ),
        ))

    if first and first.temp_max_c >= 40:
        out.append(Advisory(
            key="pomegranate_sunscald", level="watch", crop="pomegranate",
            title="डाळिंब: फळ भाजण्याचा धोका",
            body=(
                f"तापमान {_n(first.temp_max_c)}°C पर्यंत जाईल. उघड्या बाजूच्या फळांवर उन्हाचे "
                "तपकिरी चट्टे पडतात आणि ते फळ बाजारात जात नाही. फळांना पानांची सावली मिळेल असे "
                "पाहा आणि पाण्याचा ताण पडू देऊ नका."
            ),
        ))
    return out


_BY_CROP = {
    "onion": _onion_advisories,
    "soybean": _soybean_advisories,
    "pomegranate": _pomegranate_advisories,
}


def build_advisories(forecast: Forecast, crop: str | None = None) -> list[Advisory]:
    """Spray-window advice always; crop-specific disease pressure when we know the crop."""
    if not forecast.days:
        return []

    out = _spray_advisories(forecast)
    builder = _BY_CROP.get((crop or "").lower())
    if builder:
        out += builder(forecast)

    out.sort(key=lambda a: _LEVEL_ORDER.get(a.level, 9))
    return out[:MAX_ADVISORIES]
