// Mandi price service contract. Mirrors the backend's /market/prices response.
//
// All prices are rupees per QUINTAL (100 kg) — fixed by the backend's `priceUnit`, never guessed
// per record. A silent quintal/kg mix-up would be a 100x error in the one number a farmer acts on.

export type PriceTrend = 'up' | 'down' | 'flat' | 'unknown';

export interface MarketQuote {
  market: string;
  marketMr?: string;
  districtName: string;
  districtMr?: string;
  commodity: string;
  arrivalDate: string;
  ageDays: number;
  minPrice: number;
  maxPrice: number;
  modalPrice: number;
  distanceKm?: number;
  transportCost?: number;
  /** modalPrice minus transport — what the farmer actually keeps. The board is sorted by this. */
  netPrice: number;
  trend: PriceTrend;
  trendChangePct?: number;
  previousPrice?: number;
  variety?: string;
  grade?: string;
  isBest: boolean;
}

export interface MarketBoard {
  crop: string;
  priceUnit: string;
  transportRatePerQtlKm: number;
  quotes: MarketQuote[];
  /** Marathi guidance from the backend. States what is known; never predicts a price. */
  notes: string[];
  historyDays: number;
  source: string;
  isMock: boolean;
}

export interface MarketQuery {
  lat: number;
  lon: number;
  cropId: string;
  maxDistanceKm?: number | null;
  transportRate?: number | null;
}

export interface MarketService {
  getPrices(query: MarketQuery): Promise<MarketBoard>;
}

export const TREND_EMOJI: Record<PriceTrend, string> = {
  up: '📈',
  down: '📉',
  flat: '➡️',
  unknown: '',
};
