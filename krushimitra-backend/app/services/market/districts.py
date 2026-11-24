"""Maharashtra district coordinates, name aliases, and distance.

Needed because Agmarknet reports a market's DISTRICT, not its coordinates, and the useful
question is not "what is the price" but "what do I net after getting the crop there". Distance is
district-to-district, which is coarse — but a 180 km haul and a 20 km one are the whole decision,
and that difference survives the approximation.

Aliases matter more than they look: the API still returns pre-rename spellings ("Nasik",
"Ahmadnagar", "Aurangabad", "Osmanabad"), and an unmatched name would silently drop a market from
the farmer's list. Must stay in step with src/constants/locations.ts in the app.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

# Typical road distance between two markets inside the same district. Straight-line distance
# would be ~0 and would make an in-district mandi look free to reach.
INTRA_DISTRICT_KM = 15.0
# Roads are not straight lines. Great-circle x this ~ road distance in the Deccan.
ROAD_FACTOR = 1.3


@dataclass(frozen=True)
class District:
    slug: str
    mr: str
    en: str
    lat: float
    lon: float


DISTRICTS: tuple[District, ...] = (
    District("ahilyanagar", "अहिल्यानगर", "Ahilyanagar", 19.0948, 74.7480),
    District("akola", "अकोला", "Akola", 20.7002, 77.0082),
    District("amravati", "अमरावती", "Amravati", 20.9374, 77.7796),
    District("beed", "बीड", "Beed", 18.9891, 75.7601),
    District("bhandara", "भंडारा", "Bhandara", 21.1666, 79.6500),
    District("buldhana", "बुलढाणा", "Buldhana", 20.5292, 76.1842),
    District("chandrapur", "चंद्रपूर", "Chandrapur", 19.9615, 79.2961),
    District("chh_sambhajinagar", "छत्रपती संभाजीनगर", "Chh. Sambhajinagar", 19.8762, 75.3433),
    District("dharashiv", "धाराशिव", "Dharashiv", 18.1860, 76.0419),
    District("dhule", "धुळे", "Dhule", 20.9042, 74.7749),
    District("gadchiroli", "गडचिरोली", "Gadchiroli", 20.1809, 80.0036),
    District("gondia", "गोंदिया", "Gondia", 21.4624, 80.1961),
    District("hingoli", "हिंगोली", "Hingoli", 19.7173, 77.1490),
    District("jalgaon", "जळगाव", "Jalgaon", 21.0077, 75.5626),
    District("jalna", "जालना", "Jalna", 19.8347, 75.8816),
    District("kolhapur", "कोल्हापूर", "Kolhapur", 16.7050, 74.2433),
    District("latur", "लातूर", "Latur", 18.4088, 76.5604),
    District("mumbai", "मुंबई", "Mumbai", 19.0760, 72.8777),
    District("nagpur", "नागपूर", "Nagpur", 21.1458, 79.0882),
    District("nanded", "नांदेड", "Nanded", 19.1383, 77.3210),
    District("nandurbar", "नंदुरबार", "Nandurbar", 21.3667, 74.2400),
    District("nashik", "नाशिक", "Nashik", 19.9975, 73.7898),
    District("palghar", "पालघर", "Palghar", 19.6967, 72.7655),
    District("parbhani", "परभणी", "Parbhani", 19.2704, 76.7601),
    District("pune", "पुणे", "Pune", 18.5204, 73.8567),
    District("raigad", "रायगड", "Raigad", 18.6414, 72.8722),
    District("ratnagiri", "रत्नागिरी", "Ratnagiri", 16.9902, 73.3120),
    District("sangli", "सांगली", "Sangli", 16.8524, 74.5815),
    District("satara", "सातारा", "Satara", 17.6805, 74.0183),
    District("sindhudurg", "सिंधुदुर्ग", "Sindhudurg", 16.1300, 73.6800),
    District("solapur", "सोलापूर", "Solapur", 17.6599, 75.9064),
    District("thane", "ठाणे", "Thane", 19.2183, 72.9781),
    District("wardha", "वर्धा", "Wardha", 20.7453, 78.6022),
    District("washim", "वाशिम", "Washim", 20.1118, 77.1333),
    District("yavatmal", "यवतमाळ", "Yavatmal", 20.3888, 78.1204),
)

BY_SLUG = {d.slug: d for d in DISTRICTS}

# Spellings the API actually emits, including the pre-2023 district names.
_ALIASES = {
    "ahmednagar": "ahilyanagar", "ahmadnagar": "ahilyanagar", "ahilya nagar": "ahilyanagar",
    "aurangabad": "chh_sambhajinagar", "chhatrapati sambhajinagar": "chh_sambhajinagar",
    "sambhajinagar": "chh_sambhajinagar",
    "osmanabad": "dharashiv", "usmanabad": "dharashiv",
    "nasik": "nashik",
    "buldana": "buldhana", "buldhana ": "buldhana",
    "mumbai suburban": "mumbai", "mumbai city": "mumbai", "greater mumbai": "mumbai",
    "raigarh": "raigad", "raigad(mh)": "raigad",
    "sindhudurgh": "sindhudurg",
    "gondiya": "gondia",
    "yeotmal": "yavatmal", "yavatmal ": "yavatmal",
    "chandrapur(chanda)": "chandrapur",
    "thane ": "thane", "palghar ": "palghar",
}


def resolve(name: str | None) -> District | None:
    """District for whatever spelling the API sent, or None if we genuinely do not know it."""
    if not name:
        return None
    key = re.sub(r"\s+", " ", name.strip().lower())
    key = key.replace(".", "").replace("-", " ")
    if key in BY_SLUG:
        return BY_SLUG[key]
    if key in _ALIASES:
        return BY_SLUG[_ALIASES[key]]
    # "Chh. Sambhajinagar" -> "chh sambhajinagar"; also handles stray suffixes like "(MH)".
    key = re.sub(r"\(.*?\)", "", key).strip()
    if key in _ALIASES:
        return BY_SLUG[_ALIASES[key]]
    for d in DISTRICTS:
        if d.en.lower().replace(".", "") == key or d.mr == name.strip():
            return d
    return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def road_km(lat: float, lon: float, district: District | None) -> float | None:
    """Rough road distance from a farm to a market's district town. None if the district is unknown."""
    if district is None:
        return None
    straight = haversine_km(lat, lon, district.lat, district.lon)
    if straight < 5:
        return INTRA_DISTRICT_KM
    return round(straight * ROAD_FACTOR, 1)
