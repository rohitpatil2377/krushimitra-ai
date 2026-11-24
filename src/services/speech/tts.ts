import * as Speech from 'expo-speech';

// Text-to-speech (read aloud). Uses the device's on-device TTS engine via Expo Speech.
// No API key needed. Marathi quality depends on the phone having a Marathi voice
// installed (Settings → Languages → Text-to-speech). Falls back to default voice otherwise.

export const tts = {
  speak(text: string, language = 'mr-IN') {
    Speech.stop(); // stop anything currently playing first
    Speech.speak(text, { language, rate: 0.95, pitch: 1.0 });
  },
  stop() {
    Speech.stop();
  },
  isSpeaking() {
    return Speech.isSpeakingAsync();
  },
};
