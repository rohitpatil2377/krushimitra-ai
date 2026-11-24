import * as Location from 'expo-location';

import { LOCATIONS, findLocation } from '@/constants/locations';
import type { Location as District } from '@/constants/locations';

// GPS location, with the district list as the fallback — not a replacement for it.
//
// Why both: GPS is more accurate and saves the farmer a tap, but it needs a permission a farmer
// may well deny, a fix that can take 20+ seconds under cloud or indoors, and a radio that costs
// battery on a cheap phone. The district picker always works, offline and instantly. So we ask
// for GPS, use it when we get it, and silently keep the district when we don't.
//
// Accuracy is deliberately `Balanced` (~100 m), not `Highest`. Weather, mandi distance and ET0
// do not change within 100 m, and the low setting gets a fix far faster off cell towers and
// wi-fi instead of waiting on satellites.

export interface GpsFix {
  lat: number;
  lon: number;
  /** Human-readable place from reverse geocoding, or the nearest district we know. */
  label: string;
  /** District slug matched from our own list — keeps mandi/capture tagging consistent. */
  districtId: string;
  accuracyM?: number;
}

export type GpsFailure =
  | 'denied'          // farmer said no
  | 'disabled'        // location services off on the device
  | 'timeout'         // no fix in time
  | 'error';

export class GpsError extends Error {
  constructor(public reason: GpsFailure, message?: string) {
    super(message ?? reason);
  }
}

/** Nearest district in our list, so a GPS fix still maps onto the data we key things by. */
function nearestDistrict(lat: number, lon: number): District {
  let best = LOCATIONS[0];
  let bestD = Number.POSITIVE_INFINITY;
  for (const d of LOCATIONS) {
    // Squared euclidean on degrees is enough to rank candidates within one state.
    const dx = d.lat - lat;
    const dy = (d.lon - lon) * Math.cos((lat * Math.PI) / 180);
    const dist = dx * dx + dy * dy;
    if (dist < bestD) {
      bestD = dist;
      best = d;
    }
  }
  return best;
}

export async function getCurrentFix(): Promise<GpsFix> {
  let permission;
  try {
    permission = await Location.requestForegroundPermissionsAsync();
  } catch (error) {
    throw new GpsError('error', String(error));
  }
  if (!permission.granted) {
    throw new GpsError('denied');
  }

  try {
    if (!(await Location.hasServicesEnabledAsync())) {
      throw new GpsError('disabled');
    }
  } catch (error) {
    if (error instanceof GpsError) throw error;
    // Some devices throw here rather than answering; fall through and let the fix attempt decide.
  }

  let position;
  try {
    position = await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.Balanced,
    });
  } catch (error) {
    throw new GpsError('timeout', String(error));
  }

  const { latitude, longitude, accuracy } = position.coords;
  const district = nearestDistrict(latitude, longitude);

  // Reverse geocoding is a nicety: it gives the farmer their own village name instead of the
  // district town. It needs network on Android, so a failure must not lose the fix.
  let label = district.mr;
  try {
    const places = await Location.reverseGeocodeAsync({ latitude, longitude });
    const place = places[0];
    const nice = place?.subregion ?? place?.city ?? place?.district ?? place?.region;
    if (nice) label = nice;
  } catch {
    // keep the district name
  }

  return {
    lat: latitude,
    lon: longitude,
    label,
    districtId: district.id,
    accuracyM: accuracy ?? undefined,
  };
}

export { findLocation };
