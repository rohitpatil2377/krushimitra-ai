import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import ScreenContainer from '@/components/ScreenContainer';
import { Colors } from '@/constants/colors';
import { CROPS } from '@/constants/crops';
import { DECISION_EMOJI, getIrrigationService } from '@/services/irrigation';
import type { IrrigationDecision, IrrigationPlan } from '@/services/irrigation';
import { IRRIGATION_METHODS, SOIL_TYPES, useFarm } from '@/store/useFarm';
import type { IrrigationMethod, SoilType } from '@/store/useFarm';

// Irrigation advice. The decision card is the answer; the "how this was calculated" block below
// it is what makes the number trustworthy rather than magic — a farmer's son will read it, and a
// figure you can check is a figure you can argue with.
//
// Dates are collected as "how many days ago" chips rather than a calendar. It needs no date-picker
// dependency, no typing, and it is closer to how a farmer actually remembers a sowing.

const SOWING_QUICK_DAYS = [15, 30, 45, 60, 75, 90, 120];
const WATERED_QUICK_DAYS = [0, 1, 2, 3, 4, 5, 7];
const DEBOUNCE_MS = 400;

const DECISION_STYLE: Record<IrrigationDecision, { border: string; tint: string }> = {
  irrigate: { border: Colors.primary, tint: '#EDF5EC' },
  wait: { border: Colors.textMuted, tint: '#F1F4EF' },
  rain_coming: { border: Colors.accent, tint: '#FFF8E1' },
  unsure: { border: Colors.accent, tint: '#FFF8E1' },
};

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function daysAgoFromIso(iso: string | null): number | null {
  if (!iso) return null;
  const [y, m, d] = iso.split('-').map(Number);
  const then = Date.UTC(y, (m ?? 1) - 1, d ?? 1);
  const now = new Date();
  const today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  const diff = Math.round((today - then) / 86400000);
  return diff < 0 ? null : diff;
}

export default function IrrigationScreen() {
  const { t, i18n } = useTranslation();
  const isEn = i18n.language === 'en';

  const farm = useFarm();
  const coords = useFarm((s) => s.coords());
  const sowingIso = farm.sowingDate();
  const daysSinceWatering = farm.daysSinceWatering();
  const sowingDaysAgo = daysAgoFromIso(sowingIso);

  const [plan, setPlan] = useState<IrrigationPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [showWorking, setShowWorking] = useState(false);

  useEffect(() => {
    if (!farm.hydrated) void farm.hydrate();
  }, [farm.hydrated, farm.hydrate]);

  const query = useMemo(
    () =>
      farm.cropId
        ? {
            lat: coords.lat,
            lon: coords.lon,
            cropId: farm.cropId,
            sowingDate: sowingIso,
            lastWateredDaysAgo: daysSinceWatering,
            soil: farm.soil,
            method: farm.method,
            rowSpacingM: farm.rowSpacingM,
            plantSpacingM: farm.plantSpacingM,
            emitterLph: farm.emitterLph,
            emittersPerPlant: farm.emittersPerPlant,
          }
        : null,
    [
      farm.cropId, farm.soil, farm.method, farm.rowSpacingM, farm.plantSpacingM,
      farm.emitterLph, farm.emittersPerPlant, coords.lat, coords.lon,
      sowingIso, daysSinceWatering,
    ],
  );

  const load = useCallback(async () => {
    if (!query) {
      setPlan(null);
      return;
    }
    setLoading(true);
    setFailed(false);
    try {
      setPlan(await getIrrigationService().getPlan(query));
    } catch (error) {
      console.warn('[irrigation] load failed:', error);
      setFailed(true);
    } finally {
      setLoading(false);
    }
  }, [query]);

  // Debounced: tapping through the day chips should not fire a request per tap.
  useEffect(() => {
    if (!farm.hydrated) return;
    const timer = setTimeout(() => void load(), DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [farm.hydrated, load]);

  const cropLabel = (id: string) => {
    const crop = CROPS.find((c) => c.id === id);
    return crop ? `${crop.emoji} ${isEn ? crop.en : crop.mr}` : id;
  };

  return (
    <ScreenContainer scroll={false}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.intro}>{t('irrigationScreen.intro')}</Text>

        {/* --- crop --- */}
        <Text style={styles.label}>{t('weatherScreen.forCrop')}</Text>
        <View style={styles.chips}>
          {CROPS.map((crop) => (
            <Chip
              key={crop.id}
              label={cropLabel(crop.id)}
              selected={farm.cropId === crop.id}
              onPress={() => farm.update({ cropId: crop.id })}
            />
          ))}
        </View>

        {!farm.cropId && <Text style={styles.hintBox}>{t('irrigationScreen.selectCropFirst')}</Text>}

        {farm.cropId && (
          <>
            {/* --- soil + method --- */}
            <Text style={styles.label}>{t('farm.soil')}</Text>
            <View style={styles.chips}>
              {SOIL_TYPES.map((soil: SoilType) => (
                <Chip
                  key={soil}
                  label={t(`farm.soils.${soil}`)}
                  selected={farm.soil === soil}
                  onPress={() => farm.update({ soil })}
                />
              ))}
            </View>

            <Text style={styles.label}>{t('farm.method')}</Text>
            <View style={styles.chips}>
              {IRRIGATION_METHODS.map((method: IrrigationMethod) => (
                <Chip
                  key={method}
                  label={t(`farm.methods.${method}`)}
                  selected={farm.method === method}
                  onPress={() => farm.update({ method })}
                />
              ))}
            </View>

            {/* --- sowing date, as days-ago chips --- */}
            <Text style={styles.label}>
              {t(`irrigationScreen.cycleStart.${farm.cropId}`, {
                defaultValue: t('irrigationScreen.sowingQuestion'),
              })}
            </Text>
            <View style={styles.chips}>
              {SOWING_QUICK_DAYS.map((days) => (
                <Chip
                  key={days}
                  label={t('irrigationScreen.daysShort', { days })}
                  selected={sowingDaysAgo === days}
                  onPress={() => farm.setSowingDate(farm.cropId!, isoDaysAgo(days))}
                />
              ))}
            </View>
            <Stepper
              value={sowingDaysAgo}
              emptyLabel={t('irrigationScreen.notSet')}
              suffix={t('irrigationScreen.daysShort', { days: '' }).trim()}
              onChange={(next) =>
                farm.setSowingDate(farm.cropId!, next === null ? null : isoDaysAgo(next))
              }
            />

            {/* --- last watered --- */}
            <Text style={styles.label}>{t('irrigationScreen.lastWateredQuestion')}</Text>
            <View style={styles.chips}>
              {WATERED_QUICK_DAYS.map((days) => (
                <Chip
                  key={days}
                  label={
                    days === 0
                      ? t('irrigationScreen.today')
                      : days === 1
                        ? t('irrigationScreen.yesterday')
                        : t('irrigationScreen.daysShort', { days })
                  }
                  selected={daysSinceWatering === days}
                  onPress={() => farm.update({ lastWateredDate: isoDaysAgo(days) })}
                />
              ))}
            </View>
            <Pressable style={styles.waterBtn} onPress={farm.markWateredToday}>
              <Text style={styles.waterBtnText}>{t('irrigationScreen.markWatered')}</Text>
            </Pressable>

            {loading && (
              <View style={styles.centered}>
                <ActivityIndicator size="large" color={Colors.primary} />
                <Text style={styles.muted}>{t('irrigationScreen.loading')}</Text>
              </View>
            )}

            {failed && !loading && (
              <View style={styles.card}>
                <Text style={styles.paragraph}>{t('irrigationScreen.error')}</Text>
                <Pressable style={styles.retryBtn} onPress={() => void load()}>
                  <Text style={styles.retryText}>{t('irrigationScreen.retry')}</Text>
                </Pressable>
              </View>
            )}

            {plan && !loading && (
              <PlanView
                plan={plan}
                showWorking={showWorking}
                onToggleWorking={() => setShowWorking((v) => !v)}
              />
            )}
          </>
        )}
      </ScrollView>
    </ScreenContainer>
  );
}

function PlanView({
  plan,
  showWorking,
  onToggleWorking,
}: {
  plan: IrrigationPlan;
  showWorking: boolean;
  onToggleWorking: () => void;
}) {
  const { t } = useTranslation();
  const style = DECISION_STYLE[plan.decision] ?? DECISION_STYLE.unsure;

  return (
    <>
      {/* --- the answer --- */}
      <View
        style={[styles.decision, { borderLeftColor: style.border, backgroundColor: style.tint }]}
      >
        <View style={styles.decisionHead}>
          <Text style={styles.decisionTitle}>
            {DECISION_EMOJI[plan.decision]} {t(`irrigationScreen.decision.${plan.decision}`)}
          </Text>
          {plan.isMock && <Text style={styles.demoBadge}>{t('common.demoData')}</Text>}
        </View>
        <Text style={styles.decisionBody}>{plan.reason}</Text>
      </View>

      {/* --- how much --- */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>{t('irrigationScreen.howMuch')}</Text>
        <View style={styles.statGrid}>
          <Stat
            label={t('irrigationScreen.depth')}
            value={`${plan.grossMm} ${t('irrigationScreen.mm')}`}
          />
          {plan.m3PerAcre != null && (
            <Stat
              label={t('irrigationScreen.perAcre')}
              value={`${plan.m3PerAcre} ${t('irrigationScreen.cubic')}`}
            />
          )}
          {plan.litresPerPlant != null && (
            <Stat
              label={t('irrigationScreen.perPlant')}
              value={`${plan.litresPerPlant} ${t('irrigationScreen.litres')}`}
            />
          )}
          {plan.runHours != null && (
            <Stat
              label={t('irrigationScreen.runTime')}
              value={`${plan.runHours} ${t('irrigationScreen.hours')}`}
            />
          )}
        </View>
        <Text style={styles.footnote}>{t('irrigationScreen.efficiencyNote')}</Text>
      </View>

      {/* --- next --- */}
      {plan.nextInDays != null && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>{t('irrigationScreen.nextWater')}</Text>
          <Text style={styles.nextValue}>
            {plan.nextInDays <= 1
              ? t('irrigationScreen.tomorrow')
              : t('irrigationScreen.inDays', { days: plan.nextInDays })}
            {plan.nextDate ? `  ·  ${plan.nextDate}` : ''}
          </Text>
        </View>
      )}

      {/* --- notes --- */}
      {plan.notes.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>{t('irrigationScreen.notes')}</Text>
          {plan.notes.map((note, i) => (
            <View key={i} style={styles.bulletRow}>
              <Text style={styles.bullet}>•</Text>
              <Text style={styles.bulletText}>{note}</Text>
            </View>
          ))}
        </View>
      )}

      {/* --- the working: what makes the number auditable --- */}
      <View style={styles.card}>
        <Pressable style={styles.workingHead} onPress={onToggleWorking}>
          <Text style={styles.sectionTitle}>{t('irrigationScreen.workingTitle')}</Text>
          <Text style={styles.workingToggle}>
            {showWorking ? t('irrigationScreen.workingHide') : t('irrigationScreen.workingShow')}
          </Text>
        </Pressable>
        <Text style={styles.footnote}>
          {plan.confidence === 'good'
            ? t('irrigationScreen.confidenceGood')
            : t('irrigationScreen.confidenceRough')}
        </Text>
        {showWorking && (
          <View style={styles.workingBody}>
            <Row label={t('irrigationScreen.stage')} value={plan.stageMr} />
            <Row
              label={t('irrigationScreen.et0')}
              value={`${plan.et0Mm} ${t('irrigationScreen.mmPerDay')}`}
            />
            <Row label={t('irrigationScreen.kc')} value={String(plan.kc)} />
            <Row
              label={t('irrigationScreen.etc')}
              value={`${plan.etcMm} ${t('irrigationScreen.mmPerDay')}`}
            />
            <Row
              label={t('irrigationScreen.rootDepth')}
              value={`${Math.round(plan.rootDepthM * 100)} ${t('irrigationScreen.cm')}`}
            />
            <Row
              label={t('irrigationScreen.raw')}
              value={`${plan.rawMm} ${t('irrigationScreen.mm')}`}
            />
            <Row label={t('irrigationScreen.depletion')} value={`${plan.depletionPct}%`} />
          </View>
        )}
      </View>
    </>
  );
}

function Chip({
  label,
  selected,
  onPress,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable onPress={onPress} style={[styles.chip, selected && styles.chipSelected]}>
      <Text style={[styles.chipText, selected && styles.chipTextSelected]}>{label}</Text>
    </Pressable>
  );
}

function Stepper({
  value,
  emptyLabel,
  suffix,
  onChange,
}: {
  value: number | null;
  emptyLabel: string;
  suffix: string;
  onChange: (next: number | null) => void;
}) {
  const current = value ?? 0;
  return (
    <View style={styles.stepper}>
      <Pressable style={styles.stepBtn} onPress={() => onChange(Math.max(0, current - 1))}>
        <Text style={styles.stepBtnText}>−</Text>
      </Pressable>
      <Text style={styles.stepValue}>
        {value === null ? emptyLabel : `${value} ${suffix}`}
      </Text>
      <Pressable style={styles.stepBtn} onPress={() => onChange(current + 1)}>
        <Text style={styles.stepBtnText}>+</Text>
      </Pressable>
      {value !== null && (
        <Pressable style={styles.clearBtn} onPress={() => onChange(null)}>
          <Text style={styles.clearBtnText}>✕</Text>
        </Pressable>
      )}
    </View>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={styles.statValue}>{value}</Text>
    </View>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 16, paddingBottom: 40 },
  intro: { fontSize: 16, color: Colors.textMuted, lineHeight: 24 },
  label: { fontSize: 15, color: Colors.textMuted, marginTop: 18, marginBottom: 8 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: {
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.card,
    borderRadius: 999,
    paddingVertical: 9,
    paddingHorizontal: 14,
  },
  chipSelected: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  chipText: { fontSize: 16, color: Colors.text },
  chipTextSelected: { color: Colors.white, fontWeight: '700' },

  hintBox: {
    marginTop: 14,
    fontSize: 16,
    color: Colors.text,
    backgroundColor: '#FFF8E1',
    borderLeftWidth: 5,
    borderLeftColor: Colors.accent,
    borderRadius: 12,
    padding: 16,
    lineHeight: 24,
  },

  stepper: { flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 10 },
  stepBtn: {
    width: 46,
    height: 46,
    borderRadius: 23,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.card,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepBtnText: { fontSize: 24, color: Colors.text, fontWeight: '700' },
  stepValue: { flex: 1, fontSize: 17, fontWeight: '700', color: Colors.text, textAlign: 'center' },
  clearBtn: { paddingHorizontal: 10, paddingVertical: 8 },
  clearBtnText: { fontSize: 18, color: Colors.textMuted },

  waterBtn: {
    marginTop: 12,
    backgroundColor: Colors.primaryDark,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  waterBtnText: { color: Colors.white, fontSize: 17, fontWeight: '700' },

  centered: { alignItems: 'center', paddingVertical: 40, gap: 12 },
  muted: { fontSize: 15, color: Colors.textMuted },

  decision: {
    marginTop: 20,
    borderLeftWidth: 6,
    borderRadius: 14,
    padding: 18,
  },
  decisionHead: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 8 },
  decisionTitle: { flex: 1, fontSize: 21, fontWeight: '800', color: Colors.text },
  decisionBody: { fontSize: 16, color: Colors.text, lineHeight: 26 },
  demoBadge: {
    backgroundColor: Colors.accent,
    color: Colors.text,
    fontSize: 12,
    fontWeight: '700',
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 999,
    overflow: 'hidden',
  },

  card: {
    backgroundColor: Colors.card,
    borderRadius: 16,
    padding: 18,
    marginTop: 14,
    borderWidth: 1,
    borderColor: Colors.border,
    elevation: 2,
  },
  sectionTitle: { fontSize: 18, fontWeight: '700', color: Colors.text, marginBottom: 10 },
  paragraph: { fontSize: 16, color: Colors.text, lineHeight: 24 },
  footnote: { fontSize: 13, color: Colors.textMuted, marginTop: 8, lineHeight: 19 },

  statGrid: { flexDirection: 'row', flexWrap: 'wrap' },
  stat: { width: '50%', paddingVertical: 8 },
  statLabel: { fontSize: 14, color: Colors.textMuted },
  statValue: { fontSize: 21, fontWeight: '800', color: Colors.primaryDark },

  nextValue: { fontSize: 19, fontWeight: '700', color: Colors.text },

  bulletRow: { flexDirection: 'row', gap: 8, marginBottom: 8 },
  bullet: { fontSize: 16, color: Colors.primary, lineHeight: 25 },
  bulletText: { flex: 1, fontSize: 16, color: Colors.text, lineHeight: 25 },

  workingHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  workingToggle: { fontSize: 15, color: Colors.primary, fontWeight: '700', marginBottom: 10 },
  workingBody: { marginTop: 10, borderTopWidth: 1, borderTopColor: Colors.border, paddingTop: 6 },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 9,
  },
  rowLabel: { flex: 1, fontSize: 15, color: Colors.textMuted, paddingRight: 10 },
  rowValue: { fontSize: 16, fontWeight: '700', color: Colors.text },

  retryBtn: {
    marginTop: 14,
    backgroundColor: Colors.primary,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
  },
  retryText: { color: Colors.white, fontSize: 16, fontWeight: '700' },
});
