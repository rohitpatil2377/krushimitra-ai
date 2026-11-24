import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import LocationBar from '@/components/LocationBar';
import ScreenContainer from '@/components/ScreenContainer';
import { Colors } from '@/constants/colors';
import { CROPS } from '@/constants/crops';
import { CONDITION_EMOJI, LEVEL_EMOJI, getWeatherService } from '@/services/weather';
import type { Advisory, DayForecast, WeatherReport } from '@/services/weather';
import { useFarm } from '@/store/useFarm';

// Weather, but the point of the screen is the advisory block, not the thermometer. Every app
// shows 28°C; the value here is "don't spray today, it will wash off". So the advisories sit
// directly under the current conditions, above the 5-day strip.

const LEVEL_STYLE: Record<Advisory['level'], { border: string; tint: string }> = {
  warning: { border: Colors.danger, tint: '#FDECEA' },
  watch: { border: Colors.accent, tint: '#FFF8E1' },
  info: { border: Colors.primary, tint: '#EDF5EC' },
};

function parseDay(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, (m ?? 1) - 1, d ?? 1);
}

export default function WeatherScreen() {
  const { t, i18n } = useTranslation();
  const isEn = i18n.language === 'en';

  const { cropId, hydrated, update, hydrate } = useFarm();
  const coords = useFarm((s) => s.coords());

  const [report, setReport] = useState<WeatherReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    // Only on first mount — re-reading storage on every tab switch would be wasted I/O.
    if (!hydrated) void hydrate();
  }, [hydrated, hydrate]);

  const load = useCallback(
    async (isRefresh = false) => {
      isRefresh ? setRefreshing(true) : setLoading(true);
      setFailed(false);
      try {
        const data = await getWeatherService().getForecast({
          lat: coords.lat,
          lon: coords.lon,
          cropId,
        });
        setReport(data);
      } catch (error) {
        console.warn('[weather] load failed:', error);
        setFailed(true);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [coords.lat, coords.lon, cropId],
  );

  useEffect(() => {
    if (hydrated) void load();
  }, [hydrated, load]);

  return (
    <ScreenContainer scroll={false}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => load(true)} tintColor={Colors.primary} />
        }
      >
        {/* --- where + what --- */}
        <LocationBar />
        {report?.isMock && (
          <Text style={styles.demoBadge}>{t('common.demoData')}</Text>
        )}

        <Text style={styles.sectionLabel}>{t('weatherScreen.forCrop')}</Text>
        <View style={styles.chips}>
          {CROPS.map((crop) => {
            const selected = cropId === crop.id;
            return (
              <Pressable
                key={crop.id}
                onPress={() => update({ cropId: selected ? null : crop.id })}
                style={[styles.chip, selected && styles.chipSelected]}
              >
                <Text style={[styles.chipText, selected && styles.chipTextSelected]}>
                  {crop.emoji} {isEn ? crop.en : crop.mr}
                </Text>
              </Pressable>
            );
          })}
        </View>

        {loading && (
          <View style={styles.centered}>
            <ActivityIndicator size="large" color={Colors.primary} />
            <Text style={styles.muted}>{t('weatherScreen.loading')}</Text>
          </View>
        )}

        {failed && !loading && (
          <View style={styles.card}>
            <Text style={styles.paragraph}>{t('weatherScreen.error')}</Text>
            <Pressable style={styles.retryBtn} onPress={() => load()}>
              <Text style={styles.retryText}>{t('weatherScreen.retry')}</Text>
            </Pressable>
          </View>
        )}

        {report && !loading && (
          <>
            <CurrentCard report={report} />
            <AdviceSection report={report} hasCrop={Boolean(cropId)} />
            <ForecastSection days={report.days} />
          </>
        )}
      </ScrollView>

    </ScreenContainer>
  );
}

function CurrentCard({ report }: { report: WeatherReport }) {
  const { t } = useTranslation();
  const { current } = report;
  return (
    <View style={styles.card}>
      <Text style={styles.sectionTitle}>{t('weatherScreen.now')}</Text>
      <View style={styles.nowRow}>
        <Text style={styles.nowEmoji}>{CONDITION_EMOJI[current.condition] ?? '⛅'}</Text>
        <View style={styles.flex1}>
          <Text style={styles.nowTemp}>{Math.round(current.tempC)}°C</Text>
          <Text style={styles.muted}>{t(`weatherScreen.conditions.${current.condition}`)}</Text>
        </View>
      </View>
      <View style={styles.statGrid}>
        <Stat label={t('weatherScreen.feelsLike')} value={`${Math.round(current.feelsLikeC)}°C`} />
        <Stat label={t('weatherScreen.humidity')} value={`${current.humidityPct}%`} />
        <Stat label={t('weatherScreen.wind')} value={`${Math.round(current.windKph)} km/h`} />
        <Stat label={t('weatherScreen.rain')} value={`${current.rainMm} mm`} />
      </View>
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

function AdviceSection({ report, hasCrop }: { report: WeatherReport; hasCrop: boolean }) {
  const { t } = useTranslation();
  return (
    <View style={styles.adviceBlock}>
      <Text style={styles.sectionTitle}>{t('weatherScreen.adviceTitle')}</Text>
      {report.advisories.length === 0 ? (
        <View style={styles.card}>
          <Text style={styles.paragraph}>{t('weatherScreen.adviceEmpty')}</Text>
        </View>
      ) : (
        report.advisories.map((a) => {
          const style = LEVEL_STYLE[a.level] ?? LEVEL_STYLE.info;
          return (
            <View
              key={a.key}
              style={[styles.advisory, { borderLeftColor: style.border, backgroundColor: style.tint }]}
            >
              <Text style={styles.advisoryTitle}>
                {LEVEL_EMOJI[a.level] ?? 'ℹ️'} {a.title}
              </Text>
              <Text style={styles.advisoryBody}>{a.body}</Text>
            </View>
          );
        })
      )}
      {!hasCrop && <Text style={styles.hint}>{t('weatherScreen.advicePickCrop')}</Text>}
    </View>
  );
}

function ForecastSection({ days }: { days: DayForecast[] }) {
  const { t } = useTranslation();
  const raw = t('weatherScreen.weekdays', { returnObjects: true });
  const weekdays = Array.isArray(raw) ? (raw as string[]) : [];

  // Label by date, not by position: the first forecast day is not always today (a late-night
  // refresh can roll the server's day over before the phone's).
  const isoFor = (offset: number) => {
    const d = new Date();
    d.setDate(d.getDate() + offset);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  };
  const todayIso = isoFor(0);
  const tomorrowIso = isoFor(1);

  return (
    <View style={styles.card}>
      <Text style={styles.sectionTitle}>{t('weatherScreen.forecastTitle')}</Text>
      {days.map((day) => {
        const label =
          day.date === todayIso
            ? t('weatherScreen.today')
            : day.date === tomorrowIso
              ? t('weatherScreen.tomorrow')
              : (weekdays[parseDay(day.date).getDay()] ?? day.date);
        return (
          <View key={day.date} style={styles.dayRow}>
            <Text style={styles.dayLabel}>{label}</Text>
            <Text style={styles.dayEmoji}>{CONDITION_EMOJI[day.condition] ?? '⛅'}</Text>
            <Text style={styles.dayRain}>
              {day.rainChancePct}%{day.rainMm > 0 ? ` · ${day.rainMm}mm` : ''}
            </Text>
            <Text style={styles.dayTemp}>
              {Math.round(day.tempMinC)}° / {Math.round(day.tempMaxC)}°
            </Text>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 16, paddingBottom: 32 },
  flex1: { flex: 1 },
  centered: { alignItems: 'center', paddingVertical: 48, gap: 12 },

  pickRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  locationChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 999,
    paddingVertical: 10,
    paddingHorizontal: 16,
  },
  locationText: { fontSize: 17, fontWeight: '700', color: Colors.text },
  changeText: { fontSize: 14, color: Colors.primary, fontWeight: '600' },
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

  sectionLabel: { fontSize: 15, color: Colors.textMuted, marginTop: 16, marginBottom: 8 },
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
  muted: { fontSize: 15, color: Colors.textMuted },
  hint: { fontSize: 14, color: Colors.textMuted, marginTop: 8, fontStyle: 'italic' },

  nowRow: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  nowEmoji: { fontSize: 52 },
  nowTemp: { fontSize: 40, fontWeight: '800', color: Colors.text },
  statGrid: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 14 },
  stat: { width: '50%', paddingVertical: 8 },
  statLabel: { fontSize: 14, color: Colors.textMuted },
  statValue: { fontSize: 19, fontWeight: '700', color: Colors.text },

  adviceBlock: { marginTop: 20 },
  advisory: {
    borderLeftWidth: 5,
    borderRadius: 12,
    padding: 16,
    marginBottom: 10,
  },
  advisoryTitle: { fontSize: 17, fontWeight: '800', color: Colors.text, marginBottom: 6 },
  advisoryBody: { fontSize: 16, color: Colors.text, lineHeight: 25 },

  dayRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
  dayLabel: { width: 70, fontSize: 16, fontWeight: '700', color: Colors.text },
  dayEmoji: { width: 40, fontSize: 24 },
  dayRain: { flex: 1, fontSize: 15, color: Colors.textMuted },
  dayTemp: { fontSize: 16, fontWeight: '700', color: Colors.text },

  retryBtn: {
    marginTop: 14,
    backgroundColor: Colors.primary,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
  },
  retryText: { color: Colors.white, fontSize: 16, fontWeight: '700' },

  modalBackdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', justifyContent: 'flex-end' },
  modalSheet: {
    backgroundColor: Colors.bg,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingTop: 18,
    paddingHorizontal: 16,
    maxHeight: '75%',
  },
  modalTitle: { fontSize: 19, fontWeight: '800', color: Colors.text, marginBottom: 12 },
  districtRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 15,
    paddingHorizontal: 14,
    borderRadius: 12,
    marginBottom: 6,
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  districtRowSelected: { borderColor: Colors.primary, backgroundColor: '#EDF5EC' },
  districtText: { fontSize: 17, color: Colors.text },
  districtTextSelected: { fontWeight: '700', color: Colors.primaryDark },
  tick: { fontSize: 18, color: Colors.primary, fontWeight: '800' },
});
