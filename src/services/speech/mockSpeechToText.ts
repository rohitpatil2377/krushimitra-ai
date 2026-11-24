import type { SpeechToTextService } from './types';

// Mock voice input. Returns a realistic Marathi question so the chat flow can be
// tested without a microphone or the Bhashini key. Cycles through sample questions.

const SAMPLE_QUESTIONS = [
  'माझ्या टोमॅटोच्या पानांवर तपकिरी ठिपके आहेत, काय करू?',
  'कांद्याला किती वेळा पाणी द्यावे?',
  'सोयाबीनसाठी कोणते खत चांगले आहे?',
  'डाळिंबाला तेल्या रोग झाला आहे, उपाय सांगा.',
];

let index = 0;

export const mockSpeechToText: SpeechToTextService = {
  async transcribe(): Promise<string> {
    // Simulate recording + recognition time.
    await new Promise((resolve) => setTimeout(resolve, 1400));
    const question = SAMPLE_QUESTIONS[index % SAMPLE_QUESTIONS.length];
    index += 1;
    return question;
  },
};
