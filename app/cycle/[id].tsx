import { useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { useFocusEffect } from 'expo-router';
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

import { BAND_COLOR } from '@/components/CycleCard';
import ScreenContainer from '@/components/ScreenContainer';
import { Colors } from '@/constants/colors';
import { CROPS } from '@/constants/crops';
import { addEvent, getCycle, getTimeline, updateCycle } from '@/services/twin';
import type { CycleDetail, TimelineEvent } from '@/services/twin';

// One crop cycle: where it is in the season, how it is doing, and everything that has happened.
//
// The health score shows its working — every point deducted is listed with the date and reason.
// A number a farmer cannot interrogate is a number they will not act on, which is the same
// principle as the irrigation screen's "हिशोब कसा केला".

const EVENT_EMOJI: Record<string, string> = {
  sowing: '🌱',
  diagnosis: '🔬',
  irrigation: '💧',
  treatment: '🧴',
  note: '📝',
  weather: '🌦️',
  harvest: '🚜',
  image: '📷',
  voice: '🎤',
};

export default function CycleDetailScreen() {
  const { t, i18n } = useTranslation();
  const isEn = i18n.language === 'en';
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const cycleId = Number(id);

  const [cycle, setCycle] = useState<CycleDetail | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('');
  const [showWorking, setShowWorking] = useState(false);

  const load = useCallback(async () => {
    try {
      const [detail, timeline] = await Promise.all([getCycle(cycleId), getTimeline(cycleId)]);
      setCycle(detail);
      setEvents(timeline);
    } catch (error) {
      console.warn('[cycle] load failed:', error);
    } finally {
      setLoading(false);
    }
  }, [cycleId]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  const record = async (type: string, body?: string, title?: string) => {
    setBusy(true);
    try {
      await addEvent(cycleId, { type, body, title });
      setNote('');
      await load();
    } catch (error) {
      console.warn('[cycle] could not record event:', error);
    } finally {
      setBusy(false);
    }
  };

  const harvest = async () => {
    setBusy(true);
    try {
      setCycle(await updateCycle(cycleId, { status: 'harvested' }));
      await load();
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <ScreenContainer scroll={false}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      </ScreenContainer>
    );
  }

  if (!cycle) {
    return (
      <ScreenContainer>
        <Text style={styles.body}>{t('twin.loadFailed')}</Text>
        <Pressable style={styles.linkBtn} onPress={() => router.back()}>
          <Text style={styles.linkText}>{t('twin.back')}</Text>
        </Pressable>
      </ScreenContainer>
    );
  }

  const crop = CROPS.find((c) => c.id === cycle.crop);
  const band = cycle.health.band;

  return (
    <ScreenContainer scroll={false}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Pressable style={styles.backBtn} onPress={() => router.back()}>
          <Text style={styles.backText}>‹ {t('twin.back')}</Text>
        </Pressable>

        {/* --- what and where --- */}
        <Text style={styles.title}>
          {crop?.emoji} {crop ? (isEn ? crop.en : crop.mr) : cycle.crop}
          {cycle.variety ? ` · ${cycle.variety}` : ''}
        </Text>
        <Text style={styles.subtitle}>
          {cycle.plot.name ?? ''}
          {cycle.plot.district ? ` · ${cycle.plot.district}` : ''}
        </Text>

        {/* --- where in the season --- */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>{cycle.stage.stageMr}</Text>
          {cycle.stage.daysAfterSowing != null && (
            <Text style={styles.body}>
              {t('twin.dayN', { n: cycle.stage.daysAfterSowing })}
              {cycle.stage.totalDays ? ` / ${cycle.stage.totalDays}` : ''}
            </Text>
          )}
          {cycle.stage.progressPct != null && (
            <View style={styles.track}>
              <View
                style={[
                  styles.fill,
                  { width: `${Math.max(2, cycle.stage.progressPct)}%`, backgroundColor: Colors.primary },
                ]}
              />
            </View>
          )}
        </View>

        {/* --- health, with its working --- */}
        <View style={[styles.card, { borderLeftWidth: 6, borderLeftColor: BAND_COLOR[band] }]}>
          <View style={styles.healthRow}>
            <View style={styles.flex1}>
              <Text style={styles.cardTitle}>{t('twin.health')}</Text>
              <Text style={[styles.bandText, { color: BAND_COLOR[band] }]}>
                {cycle.health.bandMr}
              </Text>
            </View>
            <Text style={[styles.bigScore, { color: BAND_COLOR[band] }]}>
              {cycle.health.score}
            </Text>
          </View>
          <Text style={styles.footnote}>{cycle.health.note}</Text>

          {cycle.health.items.length > 0 && (
            <>
              <Pressable onPress={() => setShowWorking((v) => !v)}>
                <Text style={styles.toggle}>
                  {showWorking ? t('irrigationScreen.workingHide') : t('twin.whyThisScore')}
                </Text>
              </Pressable>
              {showWorking &&
                cycle.health.items.map((item, i) => (
                  <View key={i} style={styles.itemRow}>
                    <Text style={styles.itemLeft}>
                      {item.on} · {item.level}
                    </Text>
                    <Text style={styles.itemRight}>− {item.applied}</Text>
                  </View>
                ))}
            </>
          )}
        </View>

        {/* --- quick actions --- */}
        <View style={styles.actions}>
          <ActionBtn
            label={`💧 ${t('irrigationScreen.markWatered')}`}
            disabled={busy}
            onPress={() => void record('irrigation')}
          />
          {cycle.status === 'active' && (
            <ActionBtn
              label={`🚜 ${t('twin.markHarvested')}`}
              disabled={busy}
              onPress={() => void harvest()}
            />
          )}
        </View>

        <View style={styles.noteRow}>
          <TextInput
            value={note}
            onChangeText={setNote}
            placeholder={t('twin.notePlaceholder')}
            placeholderTextColor={Colors.textMuted}
            style={styles.noteInput}
          />
          <Pressable
            style={[styles.noteBtn, (!note.trim() || busy) && styles.btnDisabled]}
            disabled={!note.trim() || busy}
            onPress={() => void record('note', note.trim())}
          >
            <Text style={styles.noteBtnText}>{t('twin.add')}</Text>
          </Pressable>
        </View>

        {/* --- the season so far --- */}
        <Text style={styles.sectionTitle}>{t('twin.timeline')}</Text>
        {events.length === 0 && <Text style={styles.footnote}>{t('twin.timelineEmpty')}</Text>}
        {events.map((e) => (
          <View key={e.id} style={styles.event}>
            <Text style={styles.eventEmoji}>{EVENT_EMOJI[e.type] ?? '•'}</Text>
            <View style={styles.flex1}>
              <Text style={styles.eventTitle}>
                {e.title ?? t(`twin.events.${e.type}`, { defaultValue: e.type })}
              </Text>
              {e.body ? <Text style={styles.eventBody}>{e.body}</Text> : null}
              <Text style={styles.eventMeta}>
                {e.createdAt.slice(0, 10)}
                {e.dayIndex != null ? ` · ${t('twin.dayN', { n: e.dayIndex })}` : ''}
              </Text>
            </View>
          </View>
        ))}
      </ScrollView>
    </ScreenContainer>
  );
}

function ActionBtn({
  label,
  disabled,
  onPress,
}: {
  label: string;
  disabled: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable style={[styles.actionBtn, disabled && styles.btnDisabled]} disabled={disabled} onPress={onPress}>
      <Text style={styles.actionText}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  flex1: { flex: 1 },
  scroll: { padding: 16, paddingBottom: 40 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  backBtn: { paddingVertical: 6 },
  backText: { fontSize: 16, color: Colors.primary, fontWeight: '700' },
  title: { fontSize: 25, fontWeight: '800', color: Colors.text, marginTop: 6 },
  subtitle: { fontSize: 15, color: Colors.textMuted, marginTop: 2 },

  card: {
    backgroundColor: Colors.card,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Colors.border,
    padding: 16,
    marginTop: 14,
  },
  cardTitle: { fontSize: 17, fontWeight: '800', color: Colors.text },
  body: { fontSize: 15, color: Colors.text, marginTop: 4 },
  footnote: { fontSize: 13, color: Colors.textMuted, marginTop: 8, lineHeight: 20 },

  track: { height: 8, borderRadius: 4, backgroundColor: Colors.border, marginTop: 12, overflow: 'hidden' },
  fill: { height: 8, borderRadius: 4 },

  healthRow: { flexDirection: 'row', alignItems: 'center' },
  bandText: { fontSize: 16, fontWeight: '700', marginTop: 2 },
  bigScore: { fontSize: 40, fontWeight: '800' },
  toggle: { fontSize: 14, color: Colors.primary, fontWeight: '700', marginTop: 10 },
  itemRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 7,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
  itemLeft: { fontSize: 14, color: Colors.textMuted },
  itemRight: { fontSize: 14, fontWeight: '700', color: Colors.danger },

  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginTop: 16 },
  actionBtn: {
    flexGrow: 1,
    backgroundColor: Colors.primaryDark,
    borderRadius: 12,
    paddingVertical: 13,
    paddingHorizontal: 14,
    alignItems: 'center',
  },
  actionText: { color: Colors.white, fontSize: 15, fontWeight: '700' },
  btnDisabled: { opacity: 0.45 },

  noteRow: { flexDirection: 'row', gap: 8, marginTop: 12 },
  noteInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.card,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 11,
    fontSize: 16,
    color: Colors.text,
  },
  noteBtn: {
    backgroundColor: Colors.primary,
    borderRadius: 12,
    paddingHorizontal: 18,
    justifyContent: 'center',
  },
  noteBtnText: { color: Colors.white, fontSize: 15, fontWeight: '700' },

  sectionTitle: { fontSize: 19, fontWeight: '800', color: Colors.text, marginTop: 24, marginBottom: 10 },
  event: {
    flexDirection: 'row',
    gap: 12,
    backgroundColor: Colors.card,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: Colors.border,
    padding: 13,
    marginBottom: 8,
  },
  eventEmoji: { fontSize: 22 },
  eventTitle: { fontSize: 16, fontWeight: '700', color: Colors.text },
  eventBody: { fontSize: 15, color: Colors.text, marginTop: 3, lineHeight: 22 },
  eventMeta: { fontSize: 12, color: Colors.textMuted, marginTop: 4 },

  linkBtn: { marginTop: 12, alignItems: 'center' },
  linkText: { fontSize: 15, color: Colors.primary },
});
