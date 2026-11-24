"""Allowed values for the string "enum" columns. Validated at the API/schema layer."""

CROPS = ("onion", "soybean", "pomegranate")          # active crops (Tomato, Maize = future)
LANGS = ("mr", "hi", "en")
SEVERITY_LEVELS = ("healthy", "mild", "moderate", "severe", "critical")
RISK_LEVELS = ("low", "medium", "high", "critical")
CYCLE_STATUS = ("active", "harvested", "abandoned")
EVENT_TYPES = (
    "sowing", "diagnosis", "irrigation", "treatment", "note", "weather", "harvest",
    "image", "voice",
)
SOILS = ("heavy", "medium", "light")
IRRIGATION_METHODS = ("drip", "sprinkler", "flood")
