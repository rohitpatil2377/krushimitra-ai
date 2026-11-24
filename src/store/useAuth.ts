import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';

import { setAuthToken } from '@/services/api';
import { fetchMe, updateMe, verifyOtp } from '@/services/auth';
import type { Farmer } from '@/services/auth';
import { getFarmerId } from '@/services/field/context';

// Who is signed in.
//
// Deliberately NOT a gate on the whole app: the advisory screens work signed-out, and only the
// crop twin — which is personal data — requires an account. Demanding a phone number before a
// farmer has seen anything useful is the surest way to lose them at the front door.
//
// The JWT is long-lived (30 days server-side) because farmers will not re-login often, and it
// lives in AsyncStorage: adequate for an advisory app holding no money and no payments. Move it
// to expo-secure-store before anything transactional ships.

const TOKEN_KEY = 'krushimitra.auth_token';

interface AuthState {
  token: string | null;
  farmer: Farmer | null;
  hydrated: boolean;
  busy: boolean;
  isSignedIn: () => boolean;
  hydrate: () => Promise<void>;
  signIn: (phone: string, otp: string) => Promise<void>;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
  saveProfile: (patch: { name?: string; village?: string; district?: string }) => Promise<void>;
}

export const useAuth = create<AuthState>((set, get) => ({
  token: null,
  farmer: null,
  hydrated: false,
  busy: false,

  isSignedIn: () => Boolean(get().token),

  hydrate: async () => {
    try {
      const token = await AsyncStorage.getItem(TOKEN_KEY);
      if (token) {
        setAuthToken(token);
        set({ token });
        try {
          set({ farmer: await fetchMe() });
        } catch {
          // Expired or rejected token, or the backend is simply unreachable right now.
          // Keep the token: dropping it on a flaky rural connection would log the farmer out
          // every time they lose signal. /auth/me is retried on the next refresh.
        }
      }
    } catch (error) {
      console.warn('[auth] could not restore session:', error);
    } finally {
      set({ hydrated: true });
    }
  },

  signIn: async (phone, otp) => {
    set({ busy: true });
    try {
      const token = await verifyOtp(phone, otp);
      setAuthToken(token);
      await AsyncStorage.setItem(TOKEN_KEY, token).catch(() => undefined);
      set({ token });

      const farmer = await fetchMe();
      set({ farmer });

      // Claim this handset's anonymous id, so photos captured before signing up are attributed
      // to this farmer instead of being stranded (see docs/DATASET.md).
      try {
        set({ farmer: await updateMe({ deviceId: await getFarmerId() }) });
      } catch {
        // Not worth failing a login over.
      }
    } finally {
      set({ busy: false });
    }
  },

  signOut: async () => {
    setAuthToken(null);
    set({ token: null, farmer: null });
    await AsyncStorage.removeItem(TOKEN_KEY).catch(() => undefined);
  },

  refresh: async () => {
    if (!get().token) return;
    try {
      set({ farmer: await fetchMe() });
    } catch (error) {
      console.warn('[auth] refresh failed:', error);
    }
  },

  saveProfile: async (patch) => {
    set({ farmer: await updateMe(patch) });
  },
}));
