// Contract for speech-to-text (voice input). Swappable: mock now, Bhashini later.

export interface SpeechToTextService {
  /**
   * Capture the user's spoken question and return it as Marathi text.
   * (The real implementation records audio and sends it to Bhashini/AI4Bharat.)
   */
  transcribe(): Promise<string>;
}
