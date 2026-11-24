import { del, getJson, patchJson, postJson } from '@/services/api';

// Digital Crop Twin client: plots, crop cycles, timeline, health score.
//
// All of it is per-farmer and requires a token — the backend 404s rather than 403s on someone
// else's data, so a guessed id cannot even confirm that a plot exists.

export type SoilType = 'heavy' | 'medium' | 'light';
export type IrrigationMethod = 'drip' | 'sprinkler' | 'flood';
export type CycleStatus = 'active' | 'harvested' | 'abandoned';
export type HealthBand = 'good' | 'fair' | 'poor' | 'critical';

export interface Plot {
  id: number;
  name?: string;
  district?: string;
  areaAcres?: number;
  soil?: SoilType;
  irrigationMethod?: IrrigationMethod;
  rowSpacingM?: number;
  plantSpacingM?: number;
  emitterLph?: number;
  emittersPerPlant?: number;
}

export interface Stage {
  stage: string;
  stageMr: string;
  daysAfterSowing?: number;
  totalDays?: number;
  progressPct?: number;
  cycleStartLabelMr?: string;
}

export interface HealthItem {
  on: string;
  reason: string;
  level: string;
  rawPenalty: number;
  ageDays: number;
  applied: number;
}

export interface Health {
  score: number;
  band: HealthBand;
  bandMr: string;
  items: HealthItem[];
  note: string;
}

export interface Cycle {
  id: number;
  farmId: number;
  crop: string;
  variety?: string;
  sowingDate?: string;
  lastWateredDate?: string;
  status: CycleStatus;
  harvestDate?: string;
  yieldQuintal?: number;
  notes?: string;
}

export interface CycleDetail extends Cycle {
  plot: Plot;
  stage: Stage;
  health: Health;
  eventCount: number;
}

export interface TimelineEvent {
  id: number;
  type: string;
  dayIndex?: number;
  title?: string;
  body?: string;
  data?: Record<string, unknown>;
  diagnosisId?: string;
  createdAt: string;
}

/* eslint-disable @typescript-eslint/no-explicit-any */
function toPlot(d: any): Plot {
  return {
    id: d.id,
    name: d.name ?? undefined,
    district: d.district ?? undefined,
    areaAcres: d.area_acres ?? undefined,
    soil: d.soil ?? undefined,
    irrigationMethod: d.irrigation_method ?? undefined,
    rowSpacingM: d.row_spacing_m ?? undefined,
    plantSpacingM: d.plant_spacing_m ?? undefined,
    emitterLph: d.emitter_lph ?? undefined,
    emittersPerPlant: d.emitters_per_plant ?? undefined,
  };
}

function toCycle(d: any): Cycle {
  return {
    id: d.id,
    farmId: d.farm_id,
    crop: d.crop,
    variety: d.variety ?? undefined,
    sowingDate: d.sowing_date ?? undefined,
    lastWateredDate: d.last_watered_date ?? undefined,
    status: d.status,
    harvestDate: d.harvest_date ?? undefined,
    yieldQuintal: d.yield_quintal ?? undefined,
    notes: d.notes ?? undefined,
  };
}

function toDetail(d: any): CycleDetail {
  return {
    ...toCycle(d),
    plot: toPlot(d.farm),
    stage: {
      stage: d.stage.stage,
      stageMr: d.stage.stage_mr,
      daysAfterSowing: d.stage.days_after_sowing ?? undefined,
      totalDays: d.stage.total_days ?? undefined,
      progressPct: d.stage.progress_pct ?? undefined,
      cycleStartLabelMr: d.stage.cycle_start_label_mr ?? undefined,
    },
    health: {
      score: d.health.score,
      band: d.health.band,
      bandMr: d.health.band_mr,
      note: d.health.note,
      items: (d.health.items ?? []).map((i: any) => ({
        on: i.on, reason: i.reason, level: i.level,
        rawPenalty: i.raw_penalty, ageDays: i.age_days, applied: i.applied,
      })),
    },
    eventCount: d.event_count ?? 0,
  };
}

function toEvent(d: any): TimelineEvent {
  return {
    id: d.id,
    type: d.type,
    dayIndex: d.day_index ?? undefined,
    title: d.title ?? undefined,
    body: d.body ?? undefined,
    data: d.data ?? undefined,
    diagnosisId: d.diagnosis_id ?? undefined,
    createdAt: d.created_at,
  };
}
/* eslint-enable @typescript-eslint/no-explicit-any */

// --- plots ---
export async function listPlots(): Promise<Plot[]> {
  return (await getJson<unknown[]>('/farms')).map(toPlot);
}

export async function createPlot(input: Partial<Plot>): Promise<Plot> {
  return toPlot(await postJson('/farms', {
    name: input.name,
    district: input.district,
    area_acres: input.areaAcres,
    soil: input.soil,
    irrigation_method: input.irrigationMethod,
    row_spacing_m: input.rowSpacingM,
    plant_spacing_m: input.plantSpacingM,
    emitter_lph: input.emitterLph,
    emitters_per_plant: input.emittersPerPlant,
  }));
}

export async function updatePlot(id: number, input: Partial<Plot>): Promise<Plot> {
  return toPlot(await patchJson(`/farms/${id}`, {
    name: input.name,
    district: input.district,
    area_acres: input.areaAcres,
    soil: input.soil,
    irrigation_method: input.irrigationMethod,
    row_spacing_m: input.rowSpacingM,
    plant_spacing_m: input.plantSpacingM,
    emitter_lph: input.emitterLph,
    emitters_per_plant: input.emittersPerPlant,
  }));
}

export async function deletePlot(id: number): Promise<void> {
  await del(`/farms/${id}`);
}

// --- cycles ---
/** Dashboard shape: stage + cached health arrive with the list, so Home is one request. */
export interface CycleSummary extends Cycle {
  plotName?: string;
  stageMr?: string;
  daysAfterSowing?: number;
  progressPct?: number;
  healthScore?: number;
  healthBand?: HealthBand;
  healthBandMr?: string;
}

export async function listCycles(status?: CycleStatus): Promise<CycleSummary[]> {
  const rows = await getJson<any[]>('/crop-cycles', { status });
  return rows.map((d) => ({
    ...toCycle(d),
    plotName: d.plot_name ?? undefined,
    stageMr: d.stage?.stage_mr ?? undefined,
    daysAfterSowing: d.stage?.days_after_sowing ?? undefined,
    progressPct: d.stage?.progress_pct ?? undefined,
    healthScore: d.health_score ?? undefined,
    healthBand: d.health_band ?? undefined,
    healthBandMr: d.health_band_mr ?? undefined,
  }));
}

export async function getCycle(id: number): Promise<CycleDetail> {
  return toDetail(await getJson(`/crop-cycles/${id}`));
}

export async function createCycle(input: {
  farmId: number;
  crop: string;
  sowingDate?: string | null;
  variety?: string;
}): Promise<CycleDetail> {
  return toDetail(await postJson('/crop-cycles', {
    farm_id: input.farmId,
    crop: input.crop,
    sowing_date: input.sowingDate ?? null,
    variety: input.variety,
  }));
}

export async function updateCycle(id: number, patch: {
  status?: CycleStatus;
  lastWateredDate?: string;
  yieldQuintal?: number;
  notes?: string;
  variety?: string;
  sowingDate?: string;
}): Promise<CycleDetail> {
  return toDetail(await patchJson(`/crop-cycles/${id}`, {
    status: patch.status,
    last_watered_date: patch.lastWateredDate,
    yield_quintal: patch.yieldQuintal,
    notes: patch.notes,
    variety: patch.variety,
    sowing_date: patch.sowingDate,
  }));
}

// --- timeline ---
export async function getTimeline(cycleId: number): Promise<TimelineEvent[]> {
  return (await getJson<unknown[]>(`/crop-cycles/${cycleId}/timeline`)).map(toEvent);
}

export async function addEvent(cycleId: number, input: {
  type: string;
  title?: string;
  body?: string;
  data?: Record<string, unknown>;
  diagnosisId?: string;
  on?: string;
}): Promise<TimelineEvent> {
  return toEvent(await postJson(`/crop-cycles/${cycleId}/events`, {
    type: input.type,
    title: input.title,
    body: input.body,
    data: input.data,
    diagnosis_id: input.diagnosisId,
    on: input.on,
  }));
}
