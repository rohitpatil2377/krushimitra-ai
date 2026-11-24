import { getJson } from '@/services/api';

import { isMockSource } from './types';
import type {
  Advisory,
  AdvisoryLevel,
  WeatherCondition,
  WeatherQuery,
  WeatherReport,
  WeatherService,
} from './types';

// Weather via the FastAPI backend (`GET /weather/forecast`). The OpenWeatherMap key is
// server-only — the app never calls the vendor directly, so the key can't be extracted from it.

interface ForecastResponse {
  location_name?: string | null;
  lat: number;
  lon: number;
  crop?: string | null;
  current: {
    temp_c: number;
    feels_like_c: number;
    humidity_pct: number;
    wind_kph: number;
    rain_mm: number;
    condition: string;
    observed_at: string;
  };
  days: {
    date: string;
    temp_min_c: number;
    temp_max_c: number;
    humidity_pct: number;
    rain_mm: number;
    rain_chance_pct: number;
    wind_kph: number;
    condition: string;
  }[];
  advisories: { key: string; level: string; title: string; body: string; crop?: string | null }[];
  source: string;
}

export const apiWeatherService: WeatherService = {
  async getForecast(query: WeatherQuery): Promise<WeatherReport> {
    const data = await getJson<ForecastResponse>('/weather/forecast', {
      lat: query.lat,
      lon: query.lon,
      crop: query.cropId ?? undefined,
    });

    return {
      locationName: data.location_name ?? undefined,
      current: {
        tempC: data.current.temp_c,
        feelsLikeC: data.current.feels_like_c,
        humidityPct: data.current.humidity_pct,
        windKph: data.current.wind_kph,
        rainMm: data.current.rain_mm,
        condition: data.current.condition as WeatherCondition,
        observedAt: data.current.observed_at,
      },
      days: (data.days ?? []).map((d) => ({
        date: d.date,
        tempMinC: d.temp_min_c,
        tempMaxC: d.temp_max_c,
        humidityPct: d.humidity_pct,
        rainMm: d.rain_mm,
        rainChancePct: d.rain_chance_pct,
        windKph: d.wind_kph,
        condition: d.condition as WeatherCondition,
      })),
      advisories: (data.advisories ?? []).map<Advisory>((a) => ({
        key: a.key,
        level: a.level as AdvisoryLevel,
        title: a.title,
        body: a.body,
        crop: a.crop ?? undefined,
      })),
      source: data.source,
      isMock: isMockSource(data.source),
    };
  },
};
