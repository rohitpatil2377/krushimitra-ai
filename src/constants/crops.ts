// The three active Phase-1 crops (locked with the user). Tomato and Maize are a future phase.
// This list must stay in step with the backend taxonomy in
// krushimitra-backend/app/services/vision/labels.py — the `id` is the key sent to /vision/diagnose,
// and a crop with no labels there would get a less precise, all-crops diagnosis.
export interface Crop {
  id: string;
  mr: string; // Marathi name
  en: string; // English name
  emoji: string;
}

export const CROPS: Crop[] = [
  { id: 'onion', mr: 'कांदा', en: 'Onion', emoji: '🧅' },
  { id: 'soybean', mr: 'सोयाबीन', en: 'Soybean', emoji: '🌱' },
  { id: 'pomegranate', mr: 'डाळिंब', en: 'Pomegranate', emoji: '🍎' },
];
