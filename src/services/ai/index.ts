import { isApiConfigured } from '@/config';

import { apiDiseaseService } from './apiDiseaseService';
import { mockDiseaseService } from './mockDiseaseService';
import type {
  CropImageInput,
  DiagnosisFeedback,
  DiseaseDiagnosis,
  DiseaseService,
} from './types';

export type {
  Confidence,
  CropImageInput,
  DiagnosisFeedback,
  DiseaseDiagnosis,
  DiseaseService,
  Severity,
  SeverityLevel,
} from './types';
export { isMockVersion } from './types';

/**
 * Returns the disease service the app should use.
 *  - No backend URL     -> offline mock (sample data, badged as such).
 *  - Backend reachable  -> FastAPI /vision/diagnose; on failure fall back to the mock so the
 *                          farmer still sees something useful (graceful degradation).
 *
 * Note what is NOT inferred here: whether the answer is real. The backend can be reachable and
 * still be serving mock data, so "is this real?" is decided by `modelVersion` on the result.
 */
export function getDiseaseService(): DiseaseService {
  if (!isApiConfigured) {
    return mockDiseaseService;
  }

  return {
    async analyzeCropImage(input: CropImageInput): Promise<DiseaseDiagnosis> {
      try {
        return await apiDiseaseService.analyzeCropImage(input);
      } catch (error) {
        console.warn('[disease] backend failed, using mock instead:', error);
        return mockDiseaseService.analyzeCropImage(input);
      }
    },
    async submitFeedback(input: DiagnosisFeedback): Promise<boolean> {
      return apiDiseaseService.submitFeedback(input);
    },
  };
}
