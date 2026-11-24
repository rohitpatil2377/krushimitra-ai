import { isMockSource } from './types';
import type { DayForecast, WeatherCondition, WeatherQuery, WeatherReport, WeatherService } from './types';

// Offline sample weather — used only when there is no backend at all (no Metro host, no
// EXPO_PUBLIC_API_URL). The real agronomy rules live in the backend
// (krushimitra-backend/app/services/weather/advice.py); only a token advisory is repeated here so
// the screen is not empty while offline. Everything is badged "नमुना माहिती" via MOCK_SOURCE.

const MOCK_SOURCE = 'mock-app';

// Rough Deccan-plateau seasonality, so the sample at least matches the month on screen.
const SEASON: Record<number, [number, number, number, number, WeatherCondition]> = {
  1: [12, 29, 45, 5, 'clear'], 2: [14, 32, 40, 5, 'clear'],
  3: [18, 36, 35, 5, 'clear'], 4: [22, 39, 30, 10, 'haze'],
  5: [24, 40, 35, 20, 'haze'], 6: [23, 32, 75, 65, 'rain'],
  7: [22, 29, 86, 80, 'rain'], 8: [22, 28, 88, 80, 'rain'],
  9: [21, 30, 82, 60, 'rain'], 10: [19, 32, 65, 30, 'clouds'],
  11: [15, 30, 55, 15, 'clouds'], 12: [12, 28, 48, 5, 'clear'],
};

function isoDate(offsetDays: number): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

export const mockWeatherService: WeatherService = {
  async getForecast(_query: WeatherQuery): Promise<WeatherReport> {
    const [tMin, tMax, humidity, rainChance, condition] = SEASON[new Date().getMonth() + 1];
    const wet = rainChance >= 50;

    const days: DayForecast[] = Array.from({ length: 5 }, (_, i) => ({
      date: isoDate(i),
      tempMinC: tMin,
      tempMaxC: tMax,
      humidityPct: humidity,
      rainMm: wet ? 8 : 0,
      rainChancePct: rainChance,
      windKph: 9,
      condition,
    }));

    return {
      current: {
        tempC: Math.round((tMin + tMax) / 2),
        feelsLikeC: Math.round((tMin + tMax) / 2) + 1,
        humidityPct: humidity,
        windKph: 9,
        rainMm: wet ? 2 : 0,
        condition,
        observedAt: new Date().toISOString(),
      },
      days,
      advisories: [
        wet
          ? {
              key: 'no_spray_rain',
              level: 'warning' as const,
              title: 'आज फवारणी करू नका',
              body:
                'पुढील दोन दिवसांत पाऊस अपेक्षित आहे. आत्ता फवारणी केल्यास औषध धुऊन जाईल. ' +
                'पाऊस थांबून पाने सुकल्यावरच फवारणी करा.',
            }
          : {
              key: 'spray_window_ok',
              level: 'info' as const,
              title: 'फवारणीसाठी योग्य दिवस',
              body:
                'पुढील दोन दिवस कोरडे आहेत आणि वारा कमी आहे. फवारणी सकाळी लवकर किंवा ' +
                'संध्याकाळी करा.',
            },
      ],
      source: MOCK_SOURCE,
      isMock: isMockSource(MOCK_SOURCE),
    };
  },
};
