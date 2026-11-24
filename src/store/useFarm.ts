import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';

import { DEFAULT_LOCATION_ID, findLocation } from '@/constants/locations';
import type { Location } from '@/constants/locations';
import { setActivePlot, setFarmDistrict } from '@/services/field/context';
import type { GpsFix } from '@/services/location/gps';

// "My farm": district, crop, soil, irrigation method and the dates — asked once and reused by
// weather, irrigation and (later) mandi prices. Persisted, because re-entering your own soil type
// on every app start is exactly the friction that loses a farmer on a cheap phone.
//
// Dates are stored as DATES, not as "days ago": a farmer taps "आज पाणी दिले" once and the count
// stays correct tomorrow without them touching it again.

const STORAGE_KEY = 'krushimitra.farm.v2';

export type SoilType = 'heavy' | 'medium' | 'light';
export type IrrigationMethod = 'drip' | 'sprinkler' | 'flood';

export const SOIL_TYPES: SoilType[] = ['heavy', 'medium', 'light'];
export const IRRIGATION_METHODS: IrrigationMethod[] = ['drip', 'sprinkler', 'flood'];

interface FarmProfile {
  locationId: string;
  cropId: string | null;
  soil: SoilType;
  method: IrrigationMethod;
  /** Sowing / transplant / bahar date per crop — a farmer grows more than one. */
  sowingDates: Record<string, string>;
  lastWateredDate: string | null;
  rowSpacingM: number | null;
  plantSpacingM: number | null;
  emitterLph: number | null;
  emittersPerPlant: number;
  /** The farmer's own lorry rate, rupees per quintal per km — used for net mandi realisation. */
  transportRate: number;
  /** Hide mandis further than this, or null for all of them. */
  maxDistanceKm: number | null;
  /** Last GPS fix, kept so the app does not re-ask for a lock on every screen. */
  gps: (GpsFix & { at: string }) | null;
  /** Farmer's choice: use GPS, or stay on the district they picked. */
  useGps: boolean;
}

const DEFAULTS: FarmProfile = {
  locationId: DEFAULT_LOCATION_ID,
  cropId: null,
  soil: 'medium',
  method: 'drip',
  sowingDates: {},
  lastWateredDate: null,
  rowSpacingM: null,
  plantSpacingM: null,
  emitterLph: null,
  emittersPerPlant: 1,
  transportRate: 0.6,
  maxDistanceKm: null,
  gps: null,
  useGps: false,
};

interface FarmState extends FarmProfile {
  hydrated: boolean;
  location: () => Location;
  /**
   * The coordinates every advisory should actually use.
   *
   * GPS when the farmer turned it on and we have a fix; otherwise the district they picked.
   * One place decides this so weather, irrigation and mandi distances can never disagree about
   * where the farm is.
   */
  coords: () => { lat: number; lon: number; label: string; fromGps: boolean };
  setGps: (fix: GpsFix) => void;
  clearGps: () => void;
  /** Sowing date for the currently selected crop, if the farmer gave one. */
  sowingDate: () => string | null;
  /** Whole days since the last irrigation, or null if never recorded. */
  daysSinceWatering: () => number | null;
  update: (patch: Partial<FarmProfile>) => void;
  setSowingDate: (cropId: string, iso: string | null) => void;
  markWateredToday: () => void;
  hydrate: () => Promise<void>;
}

export function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function daysBetween(fromIso: string, toIso: string): number {
  const [fy, fm, fd] = fromIso.split('-').map(Number);
  const [ty, tm, td] = toIso.split('-').map(Number);
  const from = Date.UTC(fy, (fm ?? 1) - 1, fd ?? 1);
  const to = Date.UTC(ty, (tm ?? 1) - 1, td ?? 1);
  return Math.round((to - from) / 86400000);
}

/** Keep the capture context in step, so every photo is tagged with where and when it came from. */
function syncFieldContext(profile: FarmProfile): void {
  setFarmDistrict(findLocation(profile.locationId).en);
  const sowing = profile.cropId ? profile.sowingDates[profile.cropId] : undefined;
  setActivePlot(
    profile.cropId
      ? { plotId: `${profile.locationId}:${profile.cropId}`, sowingDate: sowing ?? null }
      : null,
  );
}

export const useFarm = create<FarmState>((set, get) => {
  const persist = async () => {
    const { locationId, cropId, soil, method, sowingDates, lastWateredDate,
            rowSpacingM, plantSpacingM, emitterLph, emittersPerPlant,
            transportRate, maxDistanceKm, gps, useGps } = get();
    const profile: FarmProfile = { locationId, cropId, soil, method, sowingDates,
      lastWateredDate, rowSpacingM, plantSpacingM, emitterLph, emittersPerPlant,
      transportRate, maxDistanceKm, gps, useGps };
    syncFieldContext(profile);
    try {
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
    } catch (error) {
      // Losing a preference is an annoyance, not a crash. Never block the UI on storage.
      console.warn('[farm] could not save profile:', error);
    }
  };

  return {
    ...DEFAULTS,
    hydrated: false,

    location: () => findLocation(get().locationId),

    coords: () => {
      const { gps, useGps, locationId } = get();
      if (useGps && gps) {
        return { lat: gps.lat, lon: gps.lon, label: gps.label, fromGps: true };
      }
      const d = findLocation(locationId);
      return { lat: d.lat, lon: d.lon, label: d.mr, fromGps: false };
    },

    setGps: (fix) => {
      // Snap the district to the nearest one we know, so captures and mandi distances stay
      // keyed to the same taxonomy whether the farmer used GPS or the picker.
      set({
        gps: { ...fix, at: new Date().toISOString() },
        useGps: true,
        locationId: findLocation(fix.districtId).id,
      });
      void persist();
    },

    clearGps: () => {
      set({ useGps: false });
      void persist();
    },

    sowingDate: () => {
      const { cropId, sowingDates } = get();
      return cropId ? (sowingDates[cropId] ?? null) : null;
    },

    daysSinceWatering: () => {
      const { lastWateredDate } = get();
      if (!lastWateredDate) return null;
      const days = daysBetween(lastWateredDate, todayIso());
      // A future date means the clock moved or the value is corrupt; treat it as today.
      return days < 0 ? 0 : days;
    },

    update: (patch) => {
      set(patch);
      void persist();
    },

    setSowingDate: (cropId, iso) => {
      const next = { ...get().sowingDates };
      if (iso) next[cropId] = iso;
      else delete next[cropId];
      set({ sowingDates: next });
      void persist();
    },

    markWateredToday: () => {
      set({ lastWateredDate: todayIso() });
      void persist();
    },

    hydrate: async () => {
      try {
        const raw = await AsyncStorage.getItem(STORAGE_KEY);
        const saved = raw ? (JSON.parse(raw) as Partial<FarmProfile>) : {};
        const profile: FarmProfile = {
          ...DEFAULTS,
          ...saved,
          locationId: findLocation(saved.locationId).id,
          sowingDates: saved.sowingDates ?? {},
        };
        set(profile);
        syncFieldContext(profile);
      } catch (error) {
        console.warn('[farm] could not load profile:', error);
        syncFieldContext({ ...DEFAULTS });
      } finally {
        set({ hydrated: true });
      }
    },
  };
});
