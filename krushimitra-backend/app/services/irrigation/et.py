"""Reference evapotranspiration (ET0) — how much water the atmosphere pulls out of a crop.

Uses the **Hargreaves-Samani** equation, not full Penman-Monteith, and that is a deliberate
choice rather than a shortcut: Penman-Monteith needs solar radiation, 2 m wind speed and actual
vapour pressure. The free OpenWeatherMap tier gives us none of those reliably. FAO-56 (Annex 4,
"Procedures for missing climatic data") names Hargreaves as the recommended fallback when only
temperature is available, which is exactly our situation.

So the honest position is: ET0 here is an ESTIMATE, typically within 10-20% of Penman-Monteith on
daily values. The app says so, and tells the farmer to confirm with the oldest soil-moisture
sensor there is - squeeze a handful of soil from the root zone.

Reference: FAO Irrigation and Drainage Paper 56, Allen et al. (1998).
"""
from __future__ import annotations

import math
from datetime import date

# Solar constant, MJ m-2 min-1 (FAO-56 eq. 28)
G_SC = 0.0820
# MJ m-2 day-1 -> mm/day of equivalent evaporation (FAO-56 table 1: 1 mm = 2.45 MJ m-2)
MJ_TO_MM = 0.408


def extraterrestrial_radiation_mm(latitude_deg: float, day: date) -> float:
    """Ra: radiation arriving at the top of the atmosphere, in mm/day equivalent.

    Depends only on latitude and day of year, so it is exact — no weather data needed.
    FAO-56 equations 21-25.
    """
    j = day.timetuple().tm_yday
    phi = math.radians(latitude_deg)

    dr = 1 + 0.033 * math.cos(2 * math.pi * j / 365)            # inverse relative distance
    delta = 0.409 * math.sin(2 * math.pi * j / 365 - 1.39)      # solar declination

    # Sunset hour angle. The clamp matters near the poles, where |tan(phi)tan(delta)| > 1 means
    # the sun never sets or never rises; Maharashtra never hits it, but an unclamped acos would
    # raise instead of degrading.
    x = -math.tan(phi) * math.tan(delta)
    omega_s = math.acos(max(-1.0, min(1.0, x)))

    ra_mj = (
        (24 * 60 / math.pi) * G_SC * dr
        * (omega_s * math.sin(phi) * math.sin(delta)
           + math.cos(phi) * math.cos(delta) * math.sin(omega_s))
    )
    return max(0.0, ra_mj * MJ_TO_MM)


def et0_hargreaves(
    temp_min_c: float, temp_max_c: float, latitude_deg: float, day: date
) -> float:
    """ET0 in mm/day (FAO-56 eq. 52).

    The (Tmax - Tmin) term stands in for radiation: a wide daily swing means clear skies and high
    evaporative demand, a narrow one means cloud. That is why a forecast's min AND max both
    matter here and why we never average them away.
    """
    if temp_max_c < temp_min_c:
        temp_min_c, temp_max_c = temp_max_c, temp_min_c
    t_mean = (temp_min_c + temp_max_c) / 2
    ra = extraterrestrial_radiation_mm(latitude_deg, day)
    et0 = 0.0023 * ra * (t_mean + 17.8) * math.sqrt(max(0.0, temp_max_c - temp_min_c))
    # A daily ET0 above ~12 mm does not occur in Maharashtra; clamping keeps one bad forecast
    # reading from producing an irrigation recommendation that floods a field.
    return round(max(0.0, min(et0, 12.0)), 2)
