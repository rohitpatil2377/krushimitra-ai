"""Marathi names for the mandis that matter to onion, soybean and pomegranate growers.

Agmarknet reports market names in English transliteration ("Pimpalgaon Baswant"). In a
Marathi-first app a farmer should read "पिंपळगाव बसवंत", so known mandis are translated and
anything unrecognised falls back to the English name UNCHANGED — never transliterated by rule,
because a wrong auto-transliteration of a place name reads as nonsense and costs trust.

Covers the APMCs that actually set the price for these three crops across Nashik, Ahilyanagar,
Pune, Solapur, Marathwada and Vidarbha. Add to it as the real API reveals spellings we miss.
"""
from __future__ import annotations

import re

MARKET_MR: dict[str, str] = {
    # --- Nashik belt: the onion price makers ---
    "lasalgaon": "लासलगाव",
    "pimpalgaon baswant": "पिंपळगाव बसवंत",
    "pimpalgaon": "पिंपळगाव",
    "yeola": "येवला",
    "niphad": "निफाड",
    "chandvad": "चांदवड",
    "satana": "सटाणा",
    "kalvan": "कळवण",
    "manmad": "मनमाड",
    "sinnar": "सिन्नर",
    "deola": "देवळा",
    "umrane": "उमराणे",
    "nashik": "नाशिक",
    "malegaon": "मालेगाव",
    # --- Ahilyanagar / Pune ---
    "rahuri": "राहुरी",
    "newasa": "नेवासा",
    "shrirampur": "श्रीरामपूर",
    "kopargaon": "कोपरगाव",
    "parner": "पारनेर",
    "shevgaon": "शेवगाव",
    "karjat": "कर्जत",
    "pune": "पुणे",
    "indapur": "इंदापूर",
    "baramati": "बारामती",
    "junnar": "जुन्नर",
    "khed": "खेड",
    "manchar": "मंचर",
    # --- Solapur / western Maharashtra: pomegranate ---
    "sangola": "सांगोला",
    "pandharpur": "पंढरपूर",
    "mangalwedha": "मंगळवेढा",
    "barshi": "बार्शी",
    "akluj": "अकलूज",
    "karmala": "करमाळा",
    "solapur": "सोलापूर",
    "sangli": "सांगली",
    "tasgaon": "तासगाव",
    "islampur": "इस्लामपूर",
    "satara": "सातारा",
    "phaltan": "फलटण",
    "wai": "वाई",
    "karad": "कराड",
    "kolhapur": "कोल्हापूर",
    # --- Marathwada: soybean ---
    "latur": "लातूर",
    "ausa": "औसा",
    "udgir": "उदगीर",
    "ahmedpur": "अहमदपूर",
    "nanded": "नांदेड",
    "parbhani": "परभणी",
    "jalna": "जालना",
    "beed": "बीड",
    "georai": "गेवराई",
    "parli": "परळी",
    "hingoli": "हिंगोली",
    "kalamnuri": "कळमनुरी",
    "basmat": "बसमत",
    "dharashiv": "धाराशिव",
    "osmanabad": "धाराशिव",
    "chh. sambhajinagar": "छत्रपती संभाजीनगर",
    "aurangabad": "छत्रपती संभाजीनगर",
    "vaijapur": "वैजापूर",
    # --- Vidarbha: soybean ---
    "akola": "अकोला",
    "amravati": "अमरावती",
    "washim": "वाशिम",
    "risod": "रिसोड",
    "karanja": "कारंजा",
    "daryapur": "दर्यापूर",
    "achalpur": "अचलपूर",
    "chikhli": "चिखली",
    "khamgaon": "खामगाव",
    "mehekar": "मेहकर",
    "deulgaon raja": "देऊळगाव राजा",
    "shegaon": "शेगाव",
    "buldhana": "बुलढाणा",
    "hinganghat": "हिंगणघाट",
    "wardha": "वर्धा",
    "arvi": "आर्वी",
    "pulgaon": "पुलगाव",
    "yavatmal": "यवतमाळ",
    "pusad": "पुसद",
    "darwha": "दारव्हा",
    "ner": "नेर",
    "umarkhed": "उमरखेड",
    "nagpur": "नागपूर",
    "jalgaon": "जळगाव",
    "dhule": "धुळे",
    "nandurbar": "नंदुरबार",
}


def market_mr(name: str | None) -> str | None:
    """Marathi name if we know this mandi, else None so the caller keeps the English one."""
    if not name:
        return None
    key = re.sub(r"\s+", " ", name.strip().lower())
    if key in MARKET_MR:
        return MARKET_MR[key]
    # Agmarknet appends qualifiers: "Yeola(Andersul)", "Khed(Chandvad)".
    stripped = re.sub(r"\(.*?\)", "", key).strip()
    return MARKET_MR.get(stripped)
