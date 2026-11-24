import { useRouter } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import ScreenContainer from '@/components/ScreenContainer';
import { Colors } from '@/constants/colors';
import { CROPS } from '@/constants/crops';
import { findLocation } from '@/constants/locations';
import { createCycle, createPlot, listPlots } from '@/services/twin';
import type { IrrigationMethod, Plot, SoilType } from '@/services/twin';
import { useFarm } from '@/store/useFarm';

// Add a crop cycle. Three questions: which crop, which plot, when planted.
//
// The plot's soil/method/district default from what the farmer already chose on the advisory
// screens, so the common case is "tap crop, tap days, done" rather than a form.

const SOWING_QUICK_DAYS = [0, 7, 15, 30, 45, 60, 90];

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export default function NewCycleScreen() {
  const { t, i18n } = useTranslation();
  const isEn = i18n.language === 'en';
  const router = useRouter();
  const farm = useFarm();

  const [plots, setPlots] = useState<Plot[]>([]);
  const [plotId, setPlotId] = useState<number | null>(null);
  const [newPlotName, setNewPlotName] = useState('');
  const [cropId, setCropId] = useState<string | null>(farm.cropId);
  const [daysAgo, setDaysAgo] = useState<number | null>(null);
  const [variety, setVariety] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const list = await listPlots();
      setPlots(list);
      if (list.length > 0 && plotId === null) setPlotId(list[0].id);
    } catch (e) {
      console.warn('[cycle/new] could not load plots:', e);
    }
  }, [plotId]);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async () => {
    if (!cropId) return;
    setSaving(true);
    setError(null);
    try {
      let targetPlot = plotId;
      if (targetPlot === null) {
        // First plot: seed it from the choices already made on the advisory screens.
        const district = findLocation(farm.locationId);
        const created = await createPlot({
          name: newPlotName.trim() || district.mr,
          district: district.en,
          soil: farm.soil as SoilType,
          irrigationMethod: farm.method as IrrigationMethod,
          rowSpacingM: farm.rowSpacingM ?? undefined,
          plantSpacingM: farm.plantSpacingM ?? undefined,
          emitterLph: farm.emitterLph ?? undefined,
          emittersPerPlant: farm.emittersPerPlant,
        });
        targetPlot = created.id;
      }

      const cycle = await createCycle({
        farmId: targetPlot,
        crop: cropId,
        sowingDate: daysAgo === null ? null : isoDaysAgo(daysAgo),
        variety: variety.trim() || undefined,
      });
      router.replace(`/cycle/${cycle.id}`);
    } catch (e) {
      console.warn('[cycle/new] save failed:', e);
      setError(t('twin.saveFailed'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <ScreenContainer scroll={false}>
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>{t('twin.addCycle')}</Text>

        <Text style={styles.label}>{t('weatherScreen.forCrop')}</Text>
        <View style={styles.chips}>
          {CROPS.map((crop) => (
            <Chip
              key={crop.id}
              label={`${crop.emoji} ${isEn ? crop.en : crop.mr}`}
              selected={cropId === crop.id}
              onPress={() => setCropId(crop.id)}
            />
          ))}
        </View>

        <Text style={styles.label}>{t('twin.plot')}</Text>
        {plots.length > 0 ? (
          <View style={styles.chips}>
            {plots.map((p) => (
              <Chip
                key={p.id}
                label={p.name ?? `#${p.id}`}
                selected={plotId === p.id}
                onPress={() => setPlotId(p.id)}
              />
            ))}
            <Chip
              label={`+ ${t('twin.newPlot')}`}
              selected={plotId === null}
              onPress={() => setPlotId(null)}
            />
          </View>
        ) : (
          <Text style={styles.help}>{t('twin.firstPlotHelp')}</Text>
        )}

        {plotId === null && (
          <TextInput
            value={newPlotName}
            onChangeText={setNewPlotName}
            placeholder={t('twin.plotNamePlaceholder')}
            placeholderTextColor={Colors.textMuted}
            style={styles.input}
          />
        )}

        <Text style={styles.label}>
          {cropId
            ? t(`irrigationScreen.cycleStart.${cropId}`, {
                defaultValue: t('irrigationScreen.sowingQuestion'),
              })
            : t('irrigationScreen.sowingQuestion')}
        </Text>
        <View style={styles.chips}>
          {SOWING_QUICK_DAYS.map((d) => (
            <Chip
              key={d}
              label={d === 0 ? t('irrigationScreen.today') : t('irrigationScreen.daysShort', { days: d })}
              selected={daysAgo === d}
              onPress={() => setDaysAgo(d)}
            />
          ))}
        </View>

        <Text style={styles.label}>{t('twin.variety')}</Text>
        <TextInput
          value={variety}
          onChangeText={setVariety}
          placeholder={t('twin.varietyPlaceholder')}
          placeholderTextColor={Colors.textMuted}
          style={styles.input}
        />

        {error && <Text style={styles.error}>{error}</Text>}

        <Pressable
          style={[styles.primaryBtn, (!cropId || saving) && styles.btnDisabled]}
          disabled={!cropId || saving}
          onPress={() => void save()}
        >
          {saving ? (
            <ActivityIndicator color={Colors.white} />
          ) : (
            <Text style={styles.primaryText}>{t('twin.save')}</Text>
          )}
        </Pressable>

        <Pressable style={styles.linkBtn} onPress={() => router.back()}>
          <Text style={styles.linkText}>{t('twin.cancel')}</Text>
        </Pressable>

        {/* Defaults come from the advisory screens, so say so rather than hiding it. */}
        <Text style={styles.footnote}>
          {t('twin.defaultsNote', {
            soil: t(`farm.soils.${farm.soil}`),
            method: t(`farm.methods.${farm.method}`),
          })}
        </Text>
      </ScrollView>
    </ScreenContainer>
  );
}

function Chip({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={[styles.chip, selected && styles.chipSelected]}>
      <Text style={[styles.chipText, selected && styles.chipTextSelected]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 20, paddingBottom: 40 },
  title: { fontSize: 24, fontWeight: '800', color: Colors.primaryDark },
  label: { fontSize: 15, color: Colors.textMuted, marginTop: 22, marginBottom: 8 },
  help: { fontSize: 15, color: Colors.textMuted, lineHeight: 22 },
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
  input: {
    marginTop: 10,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.card,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    color: Colors.text,
  },
  primaryBtn: {
    marginTop: 26,
    backgroundColor: Colors.primary,
    borderRadius: 12,
    paddingVertical: 15,
    alignItems: 'center',
  },
  btnDisabled: { opacity: 0.45 },
  primaryText: { color: Colors.white, fontSize: 17, fontWeight: '800' },
  linkBtn: { marginTop: 12, alignItems: 'center', paddingVertical: 8 },
  linkText: { fontSize: 15, color: Colors.textMuted },
  error: { marginTop: 14, fontSize: 15, color: Colors.danger, fontWeight: '600' },
  footnote: { marginTop: 20, fontSize: 13, color: Colors.textMuted, lineHeight: 20 },
});
