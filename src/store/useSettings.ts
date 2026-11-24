import { create } from 'zustand';

import i18n from '@/i18n';

export type Language = 'mr' | 'en';

interface SettingsState {
  language: Language;
  /** Switch the whole app's language and keep i18next in sync. */
  setLanguage: (language: Language) => void;
  toggleLanguage: () => void;
}

export const useSettings = create<SettingsState>((set, get) => ({
  language: 'mr',
  setLanguage: (language) => {
    i18n.changeLanguage(language);
    set({ language });
  },
  toggleLanguage: () => {
    const next: Language = get().language === 'mr' ? 'en' : 'mr';
    i18n.changeLanguage(next);
    set({ language: next });
  },
}));
