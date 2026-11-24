import { useTranslation } from 'react-i18next';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Colors } from '@/constants/colors';
import { CROPS } from '@/constants/crops';
import type { Cycle, HealthBand } from '@/services/twin';

// One crop cycle, summarised: what it is, how far through the season, and how it is doing.
// The health colour is the thing a farmer reads first, so it has to mean something — it comes
// straight from the backend's banding, never recomputed here where it could drift.

export const BAND_COLOR: Record<HealthBand, string> = {
  good: Colors.primary,
  fair: Colors.accent,
  poor: '#EF6C00',
  critical: Colors.danger,
};

export interface CycleSummary extends Cycle {
  stageMr?: string;
  daysAfterSowing?: number;
  progressPct?: number;
  healthScore?: number;
  healthBand?: HealthBand;
  healthBandMr?: string;
  plotName?: string;
}

export default function CycleCard({
  cycle,
  onPress,
}: {
  cycle: CycleSummary;
  onPress: () => void;
}) {
  const { t, i18n } = useTranslation();
  const isEn = i18n.language === 'en';
  const crop = CROPS.find((c) => c.id === cycle.crop);
  const band = cycle.healthBand ?? 'good';

  return (
    <Pressable style={styles.card} onPress={onPress}>
      <View style={styles.row}>
        <Text style={styles.emoji}>{crop?.emoji ?? '🌱'}</Text>
        <View style={styles.flex1}>
          <Text style={styles.crop}>
            {crop ? (isEn ? crop.en : crop.mr) : cycle.crop}
            {cycle.variety ? ` · ${cycle.variety}` : ''}
          </Text>
          <Text style={styles.meta}>
            {cycle.plotName ? `${cycle.plotName} · ` : ''}
            {cycle.stageMr ?? ''}
            {cycle.daysAfterSowing != null
              ? ` · ${t('twin.dayN', { n: cycle.daysAfterSowing })}`
              : ''}
          </Text>
        </View>
        {cycle.healthScore != null && (
          <View style={[styles.scoreChip, { backgroundColor: BAND_COLOR[band] }]}>
            <Text style={styles.scoreText}>{cycle.healthScore}</Text>
          </View>
        )}
      </View>

      {cycle.progressPct != null && (
        <View style={styles.track}>
          <View
            style={[
              styles.fill,
              { width: `${Math.max(2, Math.min(100, cycle.progressPct))}%`, backgroundColor: BAND_COLOR[band] },
            ]}
          />
        </View>
      )}

      {cycle.status !== 'active' && (
        <Text style={styles.status}>{t(`twin.status.${cycle.status}`)}</Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  flex1: { flex: 1 },
  card: {
    backgroundColor: Colors.card,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Colors.border,
    padding: 14,
    marginBottom: 10,
    elevation: 1,
  },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  emoji: { fontSize: 30 },
  crop: { fontSize: 18, fontWeight: '800', color: Colors.text },
  meta: { fontSize: 14, color: Colors.textMuted, marginTop: 2 },
  scoreChip: {
    minWidth: 46,
    height: 46,
    borderRadius: 23,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 6,
  },
  scoreText: { color: Colors.white, fontSize: 18, fontWeight: '800' },
  track: {
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.border,
    marginTop: 12,
    overflow: 'hidden',
  },
  fill: { height: 6, borderRadius: 3 },
  status: { marginTop: 8, fontSize: 13, color: Colors.textMuted, fontWeight: '600' },
});
