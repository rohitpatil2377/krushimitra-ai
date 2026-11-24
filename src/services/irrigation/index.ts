import { isApiConfigured } from '@/config';

import { apiIrrigationService } from './apiIrrigationService';
import { mockIrrigationService } from './mockIrrigationService';
import type { IrrigationPlan, IrrigationQuery, IrrigationService } from './types';

export type {
  Confidence,
  IrrigationDecision,
  IrrigationPlan,
  IrrigationQuery,
  IrrigationService,
} from './types';
export { DECISION_EMOJI } from './types';

/**
 * The irrigation service the app should use.
 *  - No backend URL    -> offline sample figures, flagged `rough` and badged as sample data.
 *  - Backend reachable -> FastAPI /irrigation/advice (the real FAO-56 balance); on failure fall
 *                         back to the sample so a farmer on a weak network still sees something.
 *
 * As everywhere else: "is this real?" is decided by `source`, not by the call succeeding.
 */
export function getIrrigationService(): IrrigationService {
  if (!isApiConfigured) {
    return mockIrrigationService;
  }

  return {
    async getPlan(query: IrrigationQuery): Promise<IrrigationPlan> {
      try {
        return await apiIrrigationService.getPlan(query);
      } catch (error) {
        console.warn('[irrigation] backend failed, using sample figures instead:', error);
        return mockIrrigationService.getPlan(query);
      }
    },
  };
}
