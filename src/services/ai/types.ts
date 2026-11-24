// Shared types for the disease-detection service.
// The mock and the real backend return this same shape, so the screen never needs to know
// which one answered — it reads the flags instead.

export interface CropImageInput {
  /** Local file URI from the image picker. */
  uri: string;
  /** Base64-encoded image data (the vision model needs this; the mock ignores it). */
  base64?: string;
  /** The crop the farmer selected, if any (narrows the model's options → better accuracy). */
  cropId?: string;
}

export type Confidence = 'low' | 'medium' | 'high';

export type SeverityLevel = 'healthy' | 'mild' | 'moderate' | 'severe' | 'critical';

export interface Severity {
  level: SeverityLevel;
  severityPct: number;
  riskLevel: string;
  recommendedAction: string;
  /** How it was measured: vlm | segmentation | mock | skipped. */
  method?: string;
  /** What the model says it measured (English) — shown as provenance, not advice. */
  evidence?: string;
}

export interface DiseaseDiagnosis {
  /** Disease/pest name in Marathi — or "निदान निश्चित नाही" when the model abstained. */
  diseaseName: string;
  /** Disease/pest name in English (for reference). */
  diseaseNameEn?: string;
  /** Canonical slug — the stable key for analytics and feedback. */
  diseaseSlug: string;
  /** fungal | bacterial | viral | pest | abiotic | none */
  kind: string;
  confidence: Confidence;
  /** The raw 0–1 score behind `confidence`. */
  confidenceScore: number;
  /**
   * False when the model was not confident enough, or saw no crop at all.
   * The UI MUST then show the "not sure" card: there is no treatment and no severity, by design.
   * Rendering an empty treatment list as advice would break the product's core promise.
   */
  identified: boolean;
  /** What causes it — short paragraph in Marathi. */
  cause: string;
  /** Treatment steps in Marathi. Empty when `identified` is false. */
  treatment: string[];
  /** Prevention tips in Marathi — when abstaining, these become "how to retake the photo". */
  prevention: string[];
  /** English active ingredients named (feeds the future medicine-seller tie-up). */
  chemicals: string[];
  /** The mandatory KVK dosage disclaimer — present whenever a chemical is named. */
  doseNote?: string;
  /** False when no spray fixes this (virus, wilt, sun damage). The UI says so plainly. */
  curable: boolean;
  /** Short honest caveat shown above the advice. */
  note?: string;
  /** What the model reports seeing (English) — provenance for a curious farmer or an agronomist. */
  symptoms?: string;
  /** Disease severity — the product's core wedge. Absent when the model abstained. */
  severity?: Severity;
  /** Which engine answered, e.g. "self_hosted:gemma-3-27b-it" or "mock-0". */
  modelVersion: string;
  /** Pass back to `submitFeedback` so the farmer's correction becomes a training example. */
  diagnosisId?: string;
  /**
   * True when this is SAMPLE DATA rather than a real analysis — derived from `modelVersion`,
   * never from whether the backend happened to reply. A reachable backend can still be serving
   * mocks, which is exactly how the old badge misled.
   */
  isMock: boolean;
}

export interface DiagnosisFeedback {
  diagnosisId: string;
  wasCorrect: boolean;
  /** A disease slug, when the farmer or an agronomist knows the right answer. */
  correctDisease?: string;
  note?: string;
}

/** True when a model_version denotes sample data rather than real analysis. */
export function isMockVersion(modelVersion: string | undefined): boolean {
  return !modelVersion || modelVersion.startsWith('mock');
}

/** The contract every disease-analysis backend must implement. */
export interface DiseaseService {
  analyzeCropImage(input: CropImageInput): Promise<DiseaseDiagnosis>;
  /** Records the farmer's verdict. Returns false when it couldn't be recorded (e.g. offline). */
  submitFeedback(input: DiagnosisFeedback): Promise<boolean>;
}
