import { postJson } from '@/services/api';
import { getFieldContext } from '@/services/field/context';
import type { FieldContext } from '@/services/field/context';

import { isMockVersion } from './types';
import type {
  Confidence,
  CropImageInput,
  DiagnosisFeedback,
  DiseaseDiagnosis,
  DiseaseService,
  SeverityLevel,
} from './types';

// Disease detection via the FastAPI backend (`POST /vision/diagnose`).
// Sends the photo as base64 JSON (React Native's fetch can't reliably upload file parts; base64
// is also exactly what the vision model needs server-side) plus the chosen crop.

interface VisionResponse {
  crop: string;
  disease: string;
  disease_en?: string | null;
  disease_slug: string;
  kind: string;
  confidence: number;
  identified: boolean;
  severity?: {
    level: string;
    severity_pct: number;
    risk_level: string;
    recommended_action: string;
    method?: string;
    evidence?: string | null;
  } | null;
  cause: string;
  treatment: string[];
  prevention: string[];
  chemicals: string[];
  dose_note?: string | null;
  curable: boolean;
  note?: string | null;
  symptoms?: string | null;
  model_version: string;
  diagnosis_id?: string | null;
}

function toConfidence(score: number): Confidence {
  if (score >= 0.8) return 'high';
  if (score >= 0.6) return 'medium';
  return 'low';
}

export const apiDiseaseService: DiseaseService = {
  async analyzeCropImage(input: CropImageInput): Promise<DiseaseDiagnosis> {
    if (!input.base64) {
      throw new Error('Image base64 missing — cannot call backend.');
    }

    // Field context rides along with every photo. Collecting it later is impossible — a capture
    // without a grouping key can never be held out honestly — so it goes in from the first user.
    let context: FieldContext | null = null;
    try {
      context = await getFieldContext();
    } catch (error) {
      console.warn('[disease] field context unavailable:', error);
    }

    const data = await postJson<VisionResponse>('/vision/diagnose', {
      image_base64: input.base64,
      crop: input.cropId ?? null,
      context,
    });

    return {
      diseaseName: data.disease,
      diseaseNameEn: data.disease_en ?? undefined,
      diseaseSlug: data.disease_slug,
      kind: data.kind,
      confidence: toConfidence(data.confidence),
      confidenceScore: data.confidence,
      identified: data.identified,
      cause: data.cause,
      treatment: data.treatment ?? [],
      prevention: data.prevention ?? [],
      chemicals: data.chemicals ?? [],
      doseNote: data.dose_note ?? undefined,
      curable: data.curable,
      note: data.note ?? undefined,
      symptoms: data.symptoms ?? undefined,
      severity: data.severity
        ? {
            level: data.severity.level as SeverityLevel,
            severityPct: data.severity.severity_pct,
            riskLevel: data.severity.risk_level,
            recommendedAction: data.severity.recommended_action,
            method: data.severity.method,
            evidence: data.severity.evidence ?? undefined,
          }
        : undefined,
      modelVersion: data.model_version,
      diagnosisId: data.diagnosis_id ?? undefined,
      // The badge tracks what actually produced the answer, not whether the call succeeded.
      isMock: isMockVersion(data.model_version),
    };
  },

  async submitFeedback(input: DiagnosisFeedback): Promise<boolean> {
    try {
      await postJson<{ recorded: boolean }>('/vision/feedback', {
        diagnosis_id: input.diagnosisId,
        was_correct: input.wasCorrect,
        correct_disease: input.correctDisease ?? null,
        note: input.note ?? null,
      });
      return true;
    } catch (error) {
      // A lost correction is a lost training example, not a farmer-facing failure.
      console.warn('[disease] feedback not recorded:', error);
      return false;
    }
  },
};
