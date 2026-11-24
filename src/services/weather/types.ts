// Weather service contract. Mirrors the backend's /weather/forecast response.

export type WeatherCondition =
  | 'clear' | 'clouds' | 'rain' | 'drizzle' | 'thunderstorm'
  | 'mist' | 'haze' | 'fog' | 'dust' | 'snow';

export type AdvisoryLevel = 'warning' | 'watch' | 'info';

export interface CurrentWeather {
  tempC: number;
  feelsLikeC: number;
  humidityPct: number;
  windKph: number;
  rainMm: number;
  condition: WeatherCondition;
  observedAt: string;
}

export interface DayForecast {
  date: string;              // yyyy-mm-dd
  tempMinC: number;
  tempMaxC: number;
  humidityPct: number;
  rainMm: number;
  rainChancePct: number;
  windKph: number;
  condition: WeatherCondition;
}

/** What the farmer should do — Marathi, from the backend's agronomy rules, not from the UI. */
export interface Advisory {
  key: string;
  level: AdvisoryLevel;
  title: string;
  body: string;
  crop?: string;
}

export interface WeatherReport {
  locationName?: string;
  current: CurrentWeather;
  days: DayForecast[];
  advisories: Advisory[];
  /** Provider that actually answered. Anything starting with "mock" is sample data. */
  source: string;
  isMock: boolean;
}

export interface WeatherQuery {
  lat: number;
  lon: number;
  cropId?: string | null;
}

export interface WeatherService {
  getForecast(query: WeatherQuery): Promise<WeatherReport>;
}

/** Same honesty rule as the vision badge: the source decides, never reachability. */
export function isMockSource(source: string | undefined): boolean {
  return !source || source.startsWith('mock');
}

export const CONDITION_EMOJI: Record<WeatherCondition, string> = {
  clear: '☀️',
  clouds: '⛅',
  rain: '🌧️',
  drizzle: '🌦️',
  thunderstorm: '⛈️',
  mist: '🌫️',
  haze: '🌫️',
  fog: '🌫️',
  dust: '🌫️',
  snow: '❄️',
};

export const LEVEL_EMOJI: Record<AdvisoryLevel, string> = {
  warning: '🚨',
  watch: '⚠️',
  info: '✅',
};
