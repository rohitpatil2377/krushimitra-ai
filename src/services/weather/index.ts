import { isApiConfigured } from '@/config';

import { apiWeatherService } from './apiWeatherService';
import { mockWeatherService } from './mockWeatherService';
import type { WeatherQuery, WeatherReport, WeatherService } from './types';

export type {
  Advisory,
  AdvisoryLevel,
  CurrentWeather,
  DayForecast,
  WeatherCondition,
  WeatherQuery,
  WeatherReport,
  WeatherService,
} from './types';
export { CONDITION_EMOJI, LEVEL_EMOJI, isMockSource } from './types';

/**
 * The weather service the app should use.
 *  - No backend URL    -> offline sample data, badged as such.
 *  - Backend reachable -> FastAPI /weather/forecast; on failure fall back to the sample so a
 *                         farmer on a weak network still sees something (graceful degradation).
 *
 * As with disease: "is this real?" is decided by `source`, not by the call succeeding.
 */
export function getWeatherService(): WeatherService {
  if (!isApiConfigured) {
    return mockWeatherService;
  }

  return {
    async getForecast(query: WeatherQuery): Promise<WeatherReport> {
      try {
        return await apiWeatherService.getForecast(query);
      } catch (error) {
        console.warn('[weather] backend failed, using sample data instead:', error);
        return mockWeatherService.getForecast(query);
      }
    },
  };
}
