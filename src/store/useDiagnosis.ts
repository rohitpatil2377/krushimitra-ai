import { create } from 'zustand';

import type { DiseaseDiagnosis } from '@/services/ai';

// Holds the most recent diagnosis + photo so it survives tab switches.
// (In-memory for now; persisting across app restarts is an easy later add via AsyncStorage.)
interface DiagnosisState {
  imageUri: string | null;
  cropId: string | null;
  result: DiseaseDiagnosis | null;
  setImage: (uri: string | null) => void;
  setCrop: (cropId: string | null) => void;
  setResult: (result: DiseaseDiagnosis | null) => void;
  reset: () => void;
}

export const useDiagnosis = create<DiagnosisState>((set) => ({
  imageUri: null,
  cropId: null,
  result: null,
  setImage: (imageUri) => set({ imageUri }),
  setCrop: (cropId) => set({ cropId }),
  setResult: (result) => set({ result }),
  reset: () => set({ imageUri: null, cropId: null, result: null }),
}));
