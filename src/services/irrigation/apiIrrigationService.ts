import { getJson } from '@/services/api';

import type {
  Confidence,
  IrrigationDecision,
  IrrigationPlan,
  IrrigationQuery,
  IrrigationService,
} from './types';

// Irrigation advice via the FastAPI backend (`GET /irrigation/advice`). The FAO-56 water balance
// runs server-side so the coefficients and thresholds live in one auditable place rather than
// being duplicated into the app.

interface AdviceResponse {
  crop: string;
  decision: string;
  irrigate_today: boolean;
  reason: string;
  stage: string;
  stage_mr: string;
  days_after_start?: number | null;
  kc: number;
  et0_mm: number;
  etc_mm: number;
  root_depth_m: number;
  awc_mm_per_m: number;
  raw_mm: number;
  deficit_mm: number;
  depletion_pct: number;
  net_mm: number;
  gross_mm: number;
  litres_per_plant?: number | null;
  m3_per_acre?: number | null;
  run_hours?: number | null;
  next_in_days?: number | null;
  next_date?: string | null;
  rain_next_3d_mm: number;
  soil: string;
  method: string;
  notes: string[];
  confidence: string;
  source: string;
}

export const apiIrrigationService: IrrigationService = {
  async getPlan(query: IrrigationQuery): Promise<IrrigationPlan> {
    const data = await getJson<AdviceResponse>('/irrigation/advice', {
      lat: query.lat,
      lon: query.lon,
      crop: query.cropId,
      sowing_date: query.sowingDate ?? undefined,
      last_watered_days_ago: query.lastWateredDaysAgo ?? undefined,
      soil: query.soil,
      method: query.method,
      row_spacing_m: query.rowSpacingM ?? undefined,
      plant_spacing_m: query.plantSpacingM ?? undefined,
      emitter_lph: query.emitterLph ?? undefined,
      emitters_per_plant: query.emittersPerPlant ?? undefined,
    });

    return {
      crop: data.crop,
      decision: data.decision as IrrigationDecision,
      irrigateToday: data.irrigate_today,
      reason: data.reason,
      stage: data.stage,
      stageMr: data.stage_mr,
      daysAfterStart: data.days_after_start ?? undefined,
      kc: data.kc,
      et0Mm: data.et0_mm,
      etcMm: data.etc_mm,
      rootDepthM: data.root_depth_m,
      awcMmPerM: data.awc_mm_per_m,
      rawMm: data.raw_mm,
      deficitMm: data.deficit_mm,
      depletionPct: data.depletion_pct,
      netMm: data.net_mm,
      grossMm: data.gross_mm,
      litresPerPlant: data.litres_per_plant ?? undefined,
      m3PerAcre: data.m3_per_acre ?? undefined,
      runHours: data.run_hours ?? undefined,
      nextInDays: data.next_in_days ?? undefined,
      nextDate: data.next_date ?? undefined,
      rainNext3dMm: data.rain_next_3d_mm,
      soil: data.soil,
      method: data.method,
      notes: data.notes ?? [],
      confidence: data.confidence as Confidence,
      source: data.source,
      isMock: !data.source || data.source.startsWith('mock'),
    };
  },
};
