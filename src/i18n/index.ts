import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import en from './locales/en/translation.json';
import mr from './locales/mr/translation.json';

// All app text lives in the locale JSON files above.
// Marathi (mr) is the default; English (en) is the fallback when a key is missing.
export const resources = {
  mr: { translation: mr },
  en: { translation: en },
} as const;

i18n.use(initReactI18next).init({
  resources,
  lng: 'mr', // Marathi-first by default
  fallbackLng: 'en',
  supportedLngs: ['mr', 'en'],
  interpolation: {
    escapeValue: false, // React already protects against injection
  },
  returnNull: false,
});

export default i18n;
