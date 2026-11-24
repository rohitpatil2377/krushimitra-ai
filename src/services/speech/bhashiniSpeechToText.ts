import { config } from '@/config';

import type { SpeechToTextService } from './types';

// Real Marathi speech-to-text via Bhashini (AI4Bharat).
//
// TODO (backend pass): finish this implementation. It will:
//   1. Record audio with expo-audio (and request mic permission).
//   2. Send the audio to a Supabase Edge Function "transcribe" that holds the
//      Bhashini key and returns recognized Marathi text.
//
// Kept as a stub so the SpeechToTextService interface is wired end-to-end; the
// factory in ./index.ts uses the mock until this is completed.

const FUNCTION_NAME = 'transcribe';

export const bhashiniSpeechToText: SpeechToTextService = {
  async transcribe(): Promise<string> {
    void config; // referenced so the intent (uses Supabase endpoint) is clear
    void FUNCTION_NAME;
    throw new Error('Bhashini speech-to-text not implemented yet — wire in the backend pass.');
  },
};
