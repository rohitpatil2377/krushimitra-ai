// Central place to read environment variables + resolve the backend URL.
// Expo replaces `process.env.EXPO_PUBLIC_*` with the real value at build time.
// Only low-risk keys live here; secrets (Anthropic, Bhashini, OpenWeather, data.gov.in) stay on
// the backend — see krushimitra-backend/.env.example.

import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';

export const config = {
  supabaseUrl: process.env.EXPO_PUBLIC_SUPABASE_URL ?? '',
  supabaseAnonKey: process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY ?? '',
  openWeatherKey: process.env.EXPO_PUBLIC_OPENWEATHER_API_KEY ?? '',
  dataGovInKey: process.env.EXPO_PUBLIC_DATA_GOV_IN_API_KEY ?? '',
};

export const isSupabaseConfigured = Boolean(config.supabaseUrl && config.supabaseAnonKey);

const STORAGE_KEY = 'krushimitra.api_url';
const BACKEND_PORT = 8000;

/**
 * The backend URL we start from.
 *
 * In Expo Go we auto-discover it: the phone reached Metro at some IP
 * (Constants.expoConfig.hostUri, e.g. "192.168.1.5:8081") and the backend runs on that same
 * machine at port 8000, so we reuse the host.
 *
 * In a STANDALONE build (APK) there is no Metro host, so `hostUri` is undefined and this falls
 * back to EXPO_PUBLIC_API_URL baked in at build time — or to '' , in which case every service
 * uses its mock and the app badges everything "नमुना माहिती". That is why `setApiUrl` exists:
 * a dev/demo APK must be re-pointable at a new laptop IP without a fresh cloud build.
 */
function deriveApiUrl(): string {
  const explicit = process.env.EXPO_PUBLIC_API_URL;
  if (explicit) return explicit.replace(/\/$/, '');

  const hostUri = Constants.expoConfig?.hostUri; // "<ip>:<port>" when running in Expo Go
  const host = hostUri?.split(':')[0];
  return host ? `http://${host}:${BACKEND_PORT}` : '';
}

export const builtInApiUrl = deriveApiUrl();

// `let`, not `const`, on purpose. ES module bindings are live, and services read these inside
// their functions (see src/services/api.ts), so changing them here re-points the whole app with
// no re-import and no reload.
export let apiUrl = builtInApiUrl;
export let isApiConfigured = Boolean(apiUrl);

/** Point the app at a backend for this session. Pass null to go back to the built-in value. */
export function setApiUrl(next: string | null): void {
  const trimmed = (next ?? '').trim();
  apiUrl = (trimmed || builtInApiUrl).replace(/\/$/, '');
  isApiConfigured = Boolean(apiUrl);
}

/** Same, but remembered across restarts. */
export async function saveApiUrl(next: string | null): Promise<void> {
  setApiUrl(next);
  try {
    const trimmed = (next ?? '').trim();
    if (trimmed) await AsyncStorage.setItem(STORAGE_KEY, apiUrl);
    else await AsyncStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    // The URL still applies for this session; only persistence failed.
    console.warn('[config] could not save backend URL:', error);
  }
}

/** Restore a saved override at boot. Called once from the root layout before anything renders. */
export async function loadSavedApiUrl(): Promise<void> {
  try {
    const saved = await AsyncStorage.getItem(STORAGE_KEY);
    if (saved) setApiUrl(saved);
  } catch (error) {
    console.warn('[config] could not read saved backend URL:', error);
  }
}
