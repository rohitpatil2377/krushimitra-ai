import { Pressable, StyleSheet, Text } from 'react-native';
import { useTranslation } from 'react-i18next';

import { Colors } from '@/constants/colors';
import { useSettings } from '@/store/useSettings';

/** Small pill that flips the app between Marathi and English. Demonstrates i18n + Zustand. */
export default function LanguageToggle() {
  const { t } = useTranslation();
  const toggleLanguage = useSettings((s) => s.toggleLanguage);

  return (
    <Pressable
      onPress={toggleLanguage}
      accessibilityRole="button"
      style={({ pressed }) => [styles.pill, pressed && styles.pressed]}
    >
      <Text style={styles.text}>🌐 {t('common.switchToEnglish')}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  pill: {
    alignSelf: 'flex-start',
    backgroundColor: Colors.white,
    borderColor: Colors.primary,
    borderWidth: 1.5,
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 6,
  },
  pressed: {
    opacity: 0.6,
  },
  text: {
    fontSize: 15,
    fontWeight: '600',
    color: Colors.primary,
  },
});
