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
import { TREND_EMOJI, getMarketService } from '@/services/market';
import type { MarketBoard, MarketQuote } from '@/services/market';
import { useFarm } from '@/store/useFarm';

// Mandi prices. The ranking is by NET realisation, not headline price, because a mandi paying
// Rs 200 more 200 km away nets less once the lorry is paid — and that comparison is the whole
// reason to open this screen rather than ask a neighbour.
//
// The screen never says "sell" or "hold". We cannot forecast a mandi, and a confident call that
// costs a farmer their crop's value is the same failure as a wrong diagnosis.

const TRANSPORT_RATES = [0, 0.4, 0.6, 1.0, 1.5];
const DISTANCE_LIMITS: (number | null)[] = [50, 100, 200, null];

export default function MarketScreen() {
  const { t, i18n } = useTranslation();
  const isEn = i18n.language === 'en';

  const farm = useFarm();
  const coords = useFarm((s) => s.coords());

  const [board, setBoard] = useState<MarketBoard | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!farm.hydrated) void farm.hydrate();
  }, [farm.hydrated, farm.hydrate]);

  const load = useCallback(
    async (isRefresh = false) => {
      if (!farm.cropId) {
        setBoard(null);
        return;
      }
      isRefresh ? setRefreshing(true) : setLoading(true);
      setFailed(false);
      try {
        setBoard(
          await getMarketService().getPrices({
            lat: coords.lat,
            lon: coords.lon,
            cropId: farm.cropId,
            transportRate: farm.transportRate,
            maxDistanceKm: farm.maxDistanceKm,
          }),
        );
      } catch (error) {
        console.warn('[market] load failed:', error);
        setFailed(true);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [farm.cropId, farm.transportRate, farm.maxDistanceKm, coords.lat, coords.lon],
  );

  useEffect(() => {
    if (farm.hydrated) void load();
  }, [farm.hydrated, load]);

  return (
    <ScreenContainer scroll={false}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => load(true)}
            tintColor={Colors.primary}
          />
        }
      >
        <View style={styles.headRow}>
          <Text style={styles.intro}>{t('marketScreen.intro')}</Text>
          {board?.isMock && <Text style={styles.demoBadge}>{t('common.demoData')}</Text>}
        </View>
        <LocationBar />

        {/* --- crop --- */}
        <View style={styles.chips}>
          {CROPS.map((crop) => (
            <Chip
              key={crop.id}
              label={`${crop.emoji} ${isEn ? crop.en : crop.mr}`}
              selected={farm.cropId === crop.id}
              onPress={() => farm.update({ cropId: crop.id })}
            />
          ))}
        </View>

        {!farm.cropId && <Text style={styles.hintBox}>{t('marketScreen.selectCropFirst')}</Text>}

        {farm.cropId && (
          <>
            {/* --- the two assumptions the farmer owns --- */}
            <Text style={styles.label}>{t('marketScreen.transportRate')}</Text>
            <View style={styles.chips}>
              {TRANSPORT_RATES.map((rate) => (
                <Chip
                  key={rate}
                  label={`₹${rate.toFixed(rate === 0 ? 0 : 1)}`}
                  selected={farm.transportRate === rate}
                  onPress={() => farm.update({ transportRate: rate })}
                />
              ))}
            </View>

            <Text style={styles.label}>{t('marketScreen.maxDistance')}</Text>
            <View style={styles.chips}>
              {DISTANCE_LIMITS.map((limit) => (
                <Chip
                  key={String(limit)}
                  label={
                    limit === null
                      ? t('marketScreen.anyDistance')
                      : `${limit} ${t('marketScreen.km')}`
                  }
                  selected={farm.maxDistanceKm === limit}
                  onPress={() => farm.update({ maxDistanceKm: limit })}
                />
              ))}
            </View>

            {loading && (
              <View style={styles.centered}>
                <ActivityIndicator size="large" color={Colors.primary} />
                <Text style={styles.muted}>{t('marketScreen.loading')}</Text>
              </View>
            )}

            {failed && !loading && (
              <View style={styles.card}>
                <Text style={styles.paragraph}>{t('marketScreen.error')}</Text>
                <Pressable style={styles.retryBtn} onPress={() => void load()}>
                  <Text style={styles.retryText}>{t('marketScreen.retry')}</Text>
                </Pressable>
              </View>
            )}

            {board && !loading && <BoardView board={board} isEn={isEn} />}
          </>
        )}
      </ScrollView>
    </ScreenContainer>
  );
}

function BoardView({ board, isEn }: { board: MarketBoard; isEn: boolean }) {
  const { t } = useTranslation();

  if (board.quotes.length === 0) {
    return (
      <View style={styles.card}>
        <Text style={styles.paragraph}>{t('marketScreen.empty')}</Text>
      </View>
    );
  }

  return (
    <>
      {board.quotes.map((quote) => (
        <QuoteCard key={`${quote.market}-${quote.variety ?? ''}`} quote={quote} isEn={isEn} />
      ))}

      {board.notes.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>{t('marketScreen.notes')}</Text>
          {board.notes.map((note, i) => (
            <View key={i} style={styles.bulletRow}>
              <Text style={styles.bullet}>•</Text>
              <Text style={styles.bulletText}>{note}</Text>
            </View>
          ))}
          {board.historyDays > 0 && (
            <Text style={styles.footnote}>
              {t('marketScreen.historyNote', { days: board.historyDays })}
            </Text>
          )}
        </View>
      )}
    </>
  );
}

function QuoteCard({ quote, isEn }: { quote: MarketQuote; isEn: boolean }) {
  const { t } = useTranslation();
  const name = isEn ? quote.market : (quote.marketMr ?? quote.market);
  const district = isEn ? quote.districtName : (quote.districtMr ?? quote.districtName);

  const trendLabel =
    quote.trend === 'up'
      ? t('marketScreen.trendUp', { pct: Math.abs(quote.trendChangePct ?? 0) })
      : quote.trend === 'down'
        ? t('marketScreen.trendDown', { pct: Math.abs(quote.trendChangePct ?? 0) })
        : quote.trend === 'flat'
          ? t('marketScreen.trendFlat')
          : t('marketScreen.trendUnknown');

  return (
    <View style={[styles.quote, quote.isBest && styles.quoteBest]}>
      <View style={styles.quoteHead}>
        <View style={styles.flex1}>
          <Text style={styles.marketName}>{name}</Text>
          <Text style={styles.districtName}>
            {district}
            {quote.distanceKm != null ? ` · ${Math.round(quote.distanceKm)} ${t('marketScreen.km')}` : ''}
          </Text>
        </View>
        {quote.isBest && <Text style={styles.bestBadge}>★ {t('marketScreen.best')}</Text>}
      </View>

      {/* The number that matters: what stays in the farmer's hand. */}
      <View style={styles.netRow}>
        <Text style={styles.netLabel}>{t('marketScreen.netPrice')}</Text>
        <Text style={styles.netValue}>₹{Math.round(quote.netPrice).toLocaleString('en-IN')}</Text>
      </View>
      <Text style={styles.perUnit}>{t('marketScreen.perQuintal')}</Text>

      <View style={styles.breakdown}>
        <Cell label={t('marketScreen.modalPrice')} value={`₹${Math.round(quote.modalPrice)}`} />
        {quote.transportCost != null && (
          <Cell label={t('marketScreen.transport')} value={`− ₹${Math.round(quote.transportCost)}`} />
        )}
        <Cell
          label={t('marketScreen.range')}
          value={`₹${Math.round(quote.minPrice)}–${Math.round(quote.maxPrice)}`}
        />
      </View>

      <View style={styles.metaRow}>
        <Text style={styles.meta}>
          {TREND_EMOJI[quote.trend]} {trendLabel}
        </Text>
        {quote.ageDays > 0 && (
          <Text style={styles.stale}>{t('marketScreen.stale', { days: quote.ageDays })}</Text>
        )}
        {quote.variety && <Text style={styles.meta}>{quote.variety}</Text>}
      </View>
    </View>
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

function Cell({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.cell}>
      <Text style={styles.cellLabel}>{label}</Text>
      <Text style={styles.cellValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 16, paddingBottom: 40 },
  flex1: { flex: 1 },
  headRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  intro: { flex: 1, fontSize: 16, color: Colors.textMuted, lineHeight: 24 },
  locationLine: { fontSize: 16, fontWeight: '700', color: Colors.text, marginTop: 8 },
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

  label: { fontSize: 15, color: Colors.textMuted, marginTop: 18, marginBottom: 8 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12 },
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
    marginTop: 16,
    fontSize: 16,
    color: Colors.text,
    backgroundColor: '#FFF8E1',
    borderLeftWidth: 5,
    borderLeftColor: Colors.accent,
    borderRadius: 12,
    padding: 16,
    lineHeight: 24,
  },

  centered: { alignItems: 'center', paddingVertical: 40, gap: 12 },
  muted: { fontSize: 15, color: Colors.textMuted },

  quote: {
    backgroundColor: Colors.card,
    borderRadius: 16,
    padding: 16,
    marginTop: 14,
    borderWidth: 1,
    borderColor: Colors.border,
    elevation: 2,
  },
  quoteBest: { borderColor: Colors.primary, borderWidth: 2, backgroundColor: '#F6FBF5' },
  quoteHead: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  marketName: { fontSize: 19, fontWeight: '800', color: Colors.text },
  districtName: { fontSize: 14, color: Colors.textMuted, marginTop: 2 },
  bestBadge: {
    backgroundColor: Colors.primary,
    color: Colors.white,
    fontSize: 12,
    fontWeight: '800',
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 999,
    overflow: 'hidden',
  },

  netRow: { flexDirection: 'row', alignItems: 'baseline', gap: 10, marginTop: 12 },
  netLabel: { flex: 1, fontSize: 15, color: Colors.textMuted },
  netValue: { fontSize: 28, fontWeight: '800', color: Colors.primaryDark },
  perUnit: { fontSize: 13, color: Colors.textMuted, textAlign: 'right' },

  breakdown: {
    flexDirection: 'row',
    marginTop: 12,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    paddingTop: 10,
  },
  cell: { flex: 1 },
  cellLabel: { fontSize: 13, color: Colors.textMuted },
  cellValue: { fontSize: 16, fontWeight: '700', color: Colors.text, marginTop: 2 },

  metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginTop: 10 },
  meta: { fontSize: 13, color: Colors.textMuted },
  stale: { fontSize: 13, color: Colors.danger, fontWeight: '600' },

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
  footnote: { fontSize: 13, color: Colors.textMuted, marginTop: 8 },
  bulletRow: { flexDirection: 'row', gap: 8, marginBottom: 8 },
  bullet: { fontSize: 16, color: Colors.primary, lineHeight: 25 },
  bulletText: { flex: 1, fontSize: 16, color: Colors.text, lineHeight: 25 },

  retryBtn: {
    marginTop: 14,
    backgroundColor: Colors.primary,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
  },
  retryText: { color: Colors.white, fontSize: 16, fontWeight: '700' },
});
