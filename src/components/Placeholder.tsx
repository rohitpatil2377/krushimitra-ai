import { StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { Colors } from '@/constants/colors';
import ScreenContainer from '@/components/ScreenContainer';

interface Props {
  emoji: string;
  title: string;
}

/**
 * Temporary screen body used in Step 1 for features that aren't built yet.
 * Each feature screen gets its real UI in a later step.
 */
export default function Placeholder({ emoji, title }: Props) {
  const { t } = useTranslation();
  return (
    <ScreenContainer scroll={false}>
      <View style={styles.center}>
        <Text style={styles.emoji}>{emoji}</Text>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.badge}>{t('common.comingSoon')}</Text>
        <Text style={styles.note}>{t('common.comingSoonNote')}</Text>
      </View>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  emoji: {
    fontSize: 72,
    marginBottom: 16,
  },
  title: {
    fontSize: 26,
    fontWeight: '700',
    color: Colors.text,
    textAlign: 'center',
    marginBottom: 12,
  },
  badge: {
    fontSize: 16,
    fontWeight: '600',
    color: Colors.white,
    backgroundColor: Colors.accent,
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 20,
    overflow: 'hidden',
    marginBottom: 12,
  },
  note: {
    fontSize: 16,
    color: Colors.textMuted,
    textAlign: 'center',
    lineHeight: 23,
  },
});
