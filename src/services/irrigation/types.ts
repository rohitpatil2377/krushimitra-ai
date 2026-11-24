// Irrigation service contract. Mirrors the backend's /irrigation/advice response.

export type IrrigationDecision = 'irrigate' | 'wait' | 'rain_coming' | 'unsure';
export type Confidence = 'good' | 'rough';

export interface IrrigationPlan {
  crop: string;
  decision: IrrigationDecision;
  irrigateToday: boolean;
  /** Marathi, from the backend's FAO-56 calculation — not UI chrome. */
  reason: string;

  stage: string;
  stageMr: string;
  daysAfterStart?: number;

  // The working, so the number is auditable rather than magic.
  kc: number;
  et0Mm: number;
  etcMm: number;
  rootDepthM: number;
  awcMmPerM: number;
  rawMm: number;
  deficitMm: number;
  depletionPct: number;

  netMm: number;
  grossMm: number;
  litresPerPlant?: number;
  m3PerAcre?: number;
  runHours?: number;

  nextInDays?: number;
  nextDate?: string;
  rainNext3dMm: number;

  soil: string;
  method: string;
  notes: string[];
  confidence: Confidence;
  /** Weather provider behind the plan. Anything starting with "mock" is sample data. */
  source: string;
  isMock: boolean;
}

export interface IrrigationQuery {
  lat: number;
  lon: number;
  cropId: string;
  sowingDate?: string | null;
  lastWateredDaysAgo?: number | null;
  soil: string;
  method: string;
  rowSpacingM?: number | null;
  plantSpacingM?: number | null;
  emitterLph?: number | null;
  emittersPerPlant?: number;
}

export interface IrrigationService {
  getPlan(query: IrrigationQuery): Promise<IrrigationPlan>;
}

export const DECISION_EMOJI: Record<IrrigationDecision, string> = {
  irrigate: '💧',
  wait: '✋',
  rain_coming: '🌧️',
  unsure: '🤔',
};
