import { mockSpeechToText } from './mockSpeechToText';
import type { SpeechToTextService } from './types';

export { tts } from './tts';
export type { SpeechToTextService } from './types';

// Whether voice input uses the real Bhashini service yet.
// Stays false until the Bhashini Edge Function + audio recording are wired in.
export const REAL_VOICE_INPUT_READY = false;

/**
 * Returns the speech-to-text service.
 * For now always the mock; flip to `bhashiniSpeechToText` once it's implemented.
 */
export function getSpeechToText(): SpeechToTextService {
  return mockSpeechToText;
}
