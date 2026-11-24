import type { IrrigationPlan, IrrigationQuery, IrrigationService } from './types';

// Offline sample plan — used only when there is no backend at all.
//
// The real FAO-56 water balance (ET0, Kc by growth stage, root depth, depletion fraction) lives
// in the backend, deliberately NOT duplicated here: two copies of the agronomy would drift, and
// the one in the app would be the one nobody tested. So this returns a rough seasonal figure,
// flags itself `rough`, and says in the notes that it is not the real calculation.

const MOCK_SOURCE = 'mock-app';

// Indicative mm/day the crop drinks, by month — enough for the screen to look right offline.
const ETC_BY_MONTH = [3.5, 4.2, 5.2, 6.0, 6.4, 4.0, 3.2, 3.0, 3.6, 4.0, 3.4, 3.2];

const INTERVAL_BY_SOIL: Record<string, number> = { light: 1, medium: 2, heavy: 3 };
const EFFICIENCY: Record<string, number> = { drip: 0.9, sprinkler: 0.75, flood: 0.55 };

export const mockIrrigationService: IrrigationService = {
  async getPlan(query: IrrigationQuery): Promise<IrrigationPlan> {
    const etc = ETC_BY_MONTH[new Date().getMonth()];
    const interval = INTERVAL_BY_SOIL[query.soil] ?? 2;
    const efficiency = EFFICIENCY[query.method] ?? 0.9;
    const netMm = Math.round(etc * interval * 10) / 10;
    const grossMm = Math.round((netMm / efficiency) * 10) / 10;
    const daysSince = query.lastWateredDaysAgo ?? null;

    const decision = daysSince === null ? 'unsure' : daysSince >= interval ? 'irrigate' : 'wait';
    const reason =
      decision === 'unsure'
        ? 'शेवटचे पाणी कधी दिले हे सांगितले नाही. या हंगामात साधारण दर ' +
          `${interval} दिवसांनी पाणी लागते.`
        : decision === 'irrigate'
          ? 'आज पाणी द्या — शेवटच्या पाण्यानंतर पुरेसे दिवस झाले आहेत.'
          : 'आज पाणी देण्याची गरज नाही.';

    const areaPerPlant =
      query.rowSpacingM && query.plantSpacingM ? query.rowSpacingM * query.plantSpacingM : null;

    return {
      crop: query.cropId,
      decision,
      irrigateToday: decision === 'irrigate',
      reason,
      stage: 'unknown',
      stageMr: 'अवस्था माहीत नाही',
      kc: 1,
      et0Mm: etc,
      etcMm: etc,
      rootDepthM: 0.5,
      awcMmPerM: 150,
      rawMm: netMm,
      deficitMm: daysSince === null ? 0 : Math.round(etc * daysSince * 10) / 10,
      depletionPct: 0,
      netMm,
      grossMm,
      litresPerPlant: areaPerPlant ? Math.round(grossMm * areaPerPlant * 10) / 10 : undefined,
      m3PerAcre: Math.round(grossMm * 4.047 * 10) / 10,
      nextInDays: daysSince === null ? interval : Math.max(0, interval - daysSince),
      rainNext3dMm: 0,
      soil: query.soil,
      method: query.method,
      notes: [
        'हे नमुना आकडे आहेत — इंटरनेट/सर्व्हर उपलब्ध नसल्याने प्रत्यक्ष हवामानावर आधारित ' +
          'हिशोब झालेला नाही.',
        'खात्री करण्यासाठी मुळाच्या भागातील मूठभर माती घेऊन दाबा — घट्ट गोळा झाला तर ओलावा ' +
          'पुरेसा आहे; भुरभुरीत पडली तर पाणी द्या.',
      ],
      confidence: 'rough',
      source: MOCK_SOURCE,
      isMock: true,
    };
  },
};
