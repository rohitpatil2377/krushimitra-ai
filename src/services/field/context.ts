import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { Platform } from 'react-native';

// Field context — who / where / when a photo came from.
//
// This is the part of a capture that cannot be backfilled. A photo stored without a grouping key
// can never be held out honestly: the same plant photographed across five visits would land in
// both train and test, and the accuracy we measure would be measuring the model against plants it
// has already seen. So the id is created on first launch, before there is anything to group.
//
// `farmerId` is an anonymous per-install random id. It is NOT a phone number, a name or a device
// identifier, it never leaves our own backend, and it exists only to group photos.

const FARMER_ID_KEY = 'krushimitra.farmer_id';

export interface FieldContext {
  farmer_id?: string | null;
  plot_id?: string | null;
  district?: string | null;
  taluka?: string | null;
  lat?: number | null;
  lon?: number | null;
  sowing_date?: string | null;   // ISO yyyy-mm-dd
  crop_stage?: string | null;
  device_model?: string | null;
  os_version?: string | null;
  app_version?: string | null;
}

function randomId(): string {
  let out = '';
  while (out.length < 32) {
    out += Math.floor(Math.random() * 0xffffffff).toString(16).padStart(8, '0');
  }
  return out.slice(0, 32);
}

let cachedFarmerId: string | null = null;

/** Stable anonymous id for this install. Falls back to a session-only id if storage is unusable. */
export async function getFarmerId(): Promise<string> {
  if (cachedFarmerId) return cachedFarmerId;
  try {
    const stored = await AsyncStorage.getItem(FARMER_ID_KEY);
    if (stored) {
      cachedFarmerId = stored;
      return stored;
    }
    const fresh = randomId();
    await AsyncStorage.setItem(FARMER_ID_KEY, fresh);
    cachedFarmerId = fresh;
    return fresh;
  } catch {
    // Storage denied/full: still return something so this diagnosis groups with the rest of the
    // session, rather than dropping the grouping key entirely.
    cachedFarmerId = cachedFarmerId ?? randomId();
    return cachedFarmerId;
  }
}

function deviceModel(): string | null {
  // Android exposes the model through RN's platform constants — no extra native module needed.
  // Worth recording: accuracy on a 6,000-rupee camera is not accuracy on a flagship.
  const c = Platform.constants as { Model?: string; Brand?: string } | undefined;
  if (!c?.Model) return null;
  return c.Brand ? `${c.Brand} ${c.Model}` : c.Model;
}

// Set by the crop twin once it exists (sowing -> harvest timeline). Until then these stay null and
// the backend groups by farmer instead of by plot — coarser, but still honestly splittable.
let activePlot: { plotId: string; sowingDate?: string | null } | null = null;

export function setActivePlot(plot: { plotId: string; sowingDate?: string | null } | null): void {
  activePlot = plot;
}

// Set from the farm store when the farmer picks their district (for weather). Disease pressure is
// regional, so the district is what makes the captured photos mappable later.
let farmDistrict: string | null = null;

export function setFarmDistrict(district: string | null): void {
  farmDistrict = district;
}

/** Everything we know about where this photo came from. Never throws. */
export async function getFieldContext(): Promise<FieldContext> {
  const farmerId = await getFarmerId();
  return {
    farmer_id: farmerId,
    plot_id: activePlot?.plotId ?? null,
    sowing_date: activePlot?.sowingDate ?? null,
    district: farmDistrict,
    device_model: deviceModel(),
    os_version: String(Platform.Version ?? ''),
    app_version: Constants.expoConfig?.version ?? null,
  };
}
