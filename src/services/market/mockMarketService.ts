import type { MarketBoard, MarketQuery, MarketQuote, MarketService } from './types';

// Offline sample board — used only when there is no backend at all.
//
// Uses real Maharashtra mandis so the screen is recognisable, but the net-realisation ranking and
// the accumulated price history live in the backend and are deliberately NOT duplicated here: two
// copies would drift, and the app's copy would be the untested one. Badged via MOCK_SOURCE.

const MOCK_SOURCE = 'mock-app';

const MANDIS: Record<string, { market: string; mr: string; district: string; km: number }[]> = {
  onion: [
    { market: 'Lasalgaon', mr: 'लासलगाव', district: 'नाशिक', km: 15 },
    { market: 'Pimpalgaon Baswant', mr: 'पिंपळगाव बसवंत', district: 'नाशिक', km: 15 },
    { market: 'Yeola', mr: 'येवला', district: 'नाशिक', km: 15 },
    { market: 'Pune', mr: 'पुणे', district: 'पुणे', km: 214 },
  ],
  soybean: [
    { market: 'Latur', mr: 'लातूर', district: 'लातूर', km: 60 },
    { market: 'Nanded', mr: 'नांदेड', district: 'नांदेड', km: 120 },
    { market: 'Akola', mr: 'अकोला', district: 'अकोला', km: 180 },
  ],
  pomegranate: [
    { market: 'Sangola', mr: 'सांगोला', district: 'सोलापूर', km: 40 },
    { market: 'Pune', mr: 'पुणे', district: 'पुणे', km: 180 },
    { market: 'Sangli', mr: 'सांगली', district: 'सांगली', km: 120 },
  ],
};

const BANDS: Record<string, number> = { onion: 1500, soybean: 4600, pomegranate: 7000 };

export const mockMarketService: MarketService = {
  async getPrices(query: MarketQuery): Promise<MarketBoard> {
    const mandis = MANDIS[query.cropId] ?? [];
    const centre = BANDS[query.cropId] ?? 2000;
    const rate = query.transportRate ?? 0.6;
    const today = new Date().toISOString().slice(0, 10);

    const quotes: MarketQuote[] = mandis
      .map((m, i) => {
        const modal = Math.round((centre * (1 + (i % 3) * 0.04 - 0.04)) / 10) * 10;
        const transport = Math.round(m.km * rate);
        return {
          market: m.market,
          marketMr: m.mr,
          districtName: m.district,
          districtMr: m.district,
          commodity: query.cropId,
          arrivalDate: today,
          ageDays: 0,
          minPrice: modal - 150,
          maxPrice: modal + 150,
          modalPrice: modal,
          distanceKm: m.km,
          transportCost: transport,
          netPrice: modal - transport,
          trend: 'unknown' as const,
          isBest: false,
        };
      })
      .sort((a, b) => b.netPrice - a.netPrice);

    if (quotes.length > 0) quotes[0].isBest = true;

    return {
      crop: query.cropId,
      priceUnit: 'rs_per_quintal',
      transportRatePerQtlKm: rate,
      quotes,
      notes: [
        'हे नमुना भाव आहेत — इंटरनेट/सर्व्हर उपलब्ध नसल्याने आजचे प्रत्यक्ष भाव आणलेले नाहीत.',
        'भाव प्रतवारी, आकार आणि आवकेनुसार बदलतो. गाडी भरण्यापूर्वी बाजार समितीत फोन करून ' +
          'आजचा भाव आणि आवक विचारून खात्री करा.',
      ],
      historyDays: 0,
      source: MOCK_SOURCE,
      isMock: true,
    };
  },
};
