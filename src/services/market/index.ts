import { isApiConfigured } from '@/config';

import { apiMarketService } from './apiMarketService';
import { mockMarketService } from './mockMarketService';
import type { MarketBoard, MarketQuery, MarketService } from './types';

export type {
  MarketBoard,
  MarketQuery,
  MarketQuote,
  MarketService,
  PriceTrend,
} from './types';
export { TREND_EMOJI } from './types';

/**
 * The mandi price service the app should use.
 *  - No backend URL    -> offline sample board, badged as sample data.
 *  - Backend reachable -> FastAPI /market/prices (real Agmarknet data when the key is set, plus
 *                         the net-realisation ranking and our accumulated price history).
 *
 * As everywhere else: "is this real?" is decided by `source`, not by the call succeeding.
 */
export function getMarketService(): MarketService {
  if (!isApiConfigured) {
    return mockMarketService;
  }

  return {
    async getPrices(query: MarketQuery): Promise<MarketBoard> {
      try {
        return await apiMarketService.getPrices(query);
      } catch (error) {
        console.warn('[market] backend failed, using sample board instead:', error);
        return mockMarketService.getPrices(query);
      }
    },
  };
}
