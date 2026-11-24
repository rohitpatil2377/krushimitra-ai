import { getJson } from '@/services/api';

import type {
  MarketBoard,
  MarketQuery,
  MarketQuote,
  MarketService,
  PriceTrend,
} from './types';

// Mandi prices via the FastAPI backend (`GET /market/prices`). The data.gov.in key is server-only,
// and the net-realisation ranking plus the price history live there so there is one copy of each.

interface QuoteResponse {
  market: string;
  market_mr?: string | null;
  district_name: string;
  district_mr?: string | null;
  commodity: string;
  arrival_date: string;
  age_days: number;
  min_price: number;
  max_price: number;
  modal_price: number;
  distance_km?: number | null;
  transport_cost?: number | null;
  net_price: number;
  trend: string;
  trend_change_pct?: number | null;
  previous_price?: number | null;
  variety?: string | null;
  grade?: string | null;
  is_best: boolean;
}

interface PricesResponse {
  crop: string;
  price_unit: string;
  transport_rate_per_qtl_km: number;
  quotes: QuoteResponse[];
  notes: string[];
  history_days: number;
  source: string;
}

export const apiMarketService: MarketService = {
  async getPrices(query: MarketQuery): Promise<MarketBoard> {
    const data = await getJson<PricesResponse>('/market/prices', {
      lat: query.lat,
      lon: query.lon,
      crop: query.cropId,
      max_distance_km: query.maxDistanceKm ?? undefined,
      transport_rate: query.transportRate ?? undefined,
    });

    return {
      crop: data.crop,
      priceUnit: data.price_unit,
      transportRatePerQtlKm: data.transport_rate_per_qtl_km,
      quotes: (data.quotes ?? []).map<MarketQuote>((q) => ({
        market: q.market,
        marketMr: q.market_mr ?? undefined,
        districtName: q.district_name,
        districtMr: q.district_mr ?? undefined,
        commodity: q.commodity,
        arrivalDate: q.arrival_date,
        ageDays: q.age_days,
        minPrice: q.min_price,
        maxPrice: q.max_price,
        modalPrice: q.modal_price,
        distanceKm: q.distance_km ?? undefined,
        transportCost: q.transport_cost ?? undefined,
        netPrice: q.net_price,
        trend: q.trend as PriceTrend,
        trendChangePct: q.trend_change_pct ?? undefined,
        previousPrice: q.previous_price ?? undefined,
        variety: q.variety ?? undefined,
        grade: q.grade ?? undefined,
        isBest: q.is_best,
      })),
      notes: data.notes ?? [],
      historyDays: data.history_days ?? 0,
      source: data.source,
      isMock: !data.source || data.source.startsWith('mock'),
    };
  },
};
