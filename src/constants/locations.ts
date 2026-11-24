// Maharashtra districts with their headquarters' coordinates.
//
// Why a baked-in list instead of GPS: a district picker needs no permission dialog, works with
// the radio off, and costs nothing on a low-end phone. A farmer knows their district; asking for
// it once is less friction than a permission prompt they may well deny. GPS can refine this
// later — `setLocation` takes any lat/lon, so nothing here blocks that.
//
// The district a farmer picks also fills `district` in the capture context, which is how disease
// pressure becomes mappable (Nashik onion is not Solapur onion). See docs/DATASET.md.

export interface Location {
  id: string;
  mr: string;
  en: string;
  lat: number;
  lon: number;
}

export const LOCATIONS: Location[] = [
  { id: 'ahilyanagar', mr: 'अहिल्यानगर', en: 'Ahilyanagar', lat: 19.0948, lon: 74.748 },
  { id: 'akola', mr: 'अकोला', en: 'Akola', lat: 20.7002, lon: 77.0082 },
  { id: 'amravati', mr: 'अमरावती', en: 'Amravati', lat: 20.9374, lon: 77.7796 },
  { id: 'beed', mr: 'बीड', en: 'Beed', lat: 18.9891, lon: 75.7601 },
  { id: 'bhandara', mr: 'भंडारा', en: 'Bhandara', lat: 21.1666, lon: 79.65 },
  { id: 'buldhana', mr: 'बुलढाणा', en: 'Buldhana', lat: 20.5292, lon: 76.1842 },
  { id: 'chandrapur', mr: 'चंद्रपूर', en: 'Chandrapur', lat: 19.9615, lon: 79.2961 },
  { id: 'chh_sambhajinagar', mr: 'छत्रपती संभाजीनगर', en: 'Chh. Sambhajinagar', lat: 19.8762, lon: 75.3433 },
  { id: 'dharashiv', mr: 'धाराशिव', en: 'Dharashiv', lat: 18.186, lon: 76.0419 },
  { id: 'dhule', mr: 'धुळे', en: 'Dhule', lat: 20.9042, lon: 74.7749 },
  { id: 'gadchiroli', mr: 'गडचिरोली', en: 'Gadchiroli', lat: 20.1809, lon: 80.0036 },
  { id: 'gondia', mr: 'गोंदिया', en: 'Gondia', lat: 21.4624, lon: 80.1961 },
  { id: 'hingoli', mr: 'हिंगोली', en: 'Hingoli', lat: 19.7173, lon: 77.149 },
  { id: 'jalgaon', mr: 'जळगाव', en: 'Jalgaon', lat: 21.0077, lon: 75.5626 },
  { id: 'jalna', mr: 'जालना', en: 'Jalna', lat: 19.8347, lon: 75.8816 },
  { id: 'kolhapur', mr: 'कोल्हापूर', en: 'Kolhapur', lat: 16.705, lon: 74.2433 },
  { id: 'latur', mr: 'लातूर', en: 'Latur', lat: 18.4088, lon: 76.5604 },
  { id: 'mumbai', mr: 'मुंबई', en: 'Mumbai', lat: 19.076, lon: 72.8777 },
  { id: 'nagpur', mr: 'नागपूर', en: 'Nagpur', lat: 21.1458, lon: 79.0882 },
  { id: 'nanded', mr: 'नांदेड', en: 'Nanded', lat: 19.1383, lon: 77.321 },
  { id: 'nandurbar', mr: 'नंदुरबार', en: 'Nandurbar', lat: 21.3667, lon: 74.24 },
  { id: 'nashik', mr: 'नाशिक', en: 'Nashik', lat: 19.9975, lon: 73.7898 },
  { id: 'palghar', mr: 'पालघर', en: 'Palghar', lat: 19.6967, lon: 72.7655 },
  { id: 'parbhani', mr: 'परभणी', en: 'Parbhani', lat: 19.2704, lon: 76.7601 },
  { id: 'pune', mr: 'पुणे', en: 'Pune', lat: 18.5204, lon: 73.8567 },
  { id: 'raigad', mr: 'रायगड', en: 'Raigad', lat: 18.6414, lon: 72.8722 },
  { id: 'ratnagiri', mr: 'रत्नागिरी', en: 'Ratnagiri', lat: 16.9902, lon: 73.312 },
  { id: 'sangli', mr: 'सांगली', en: 'Sangli', lat: 16.8524, lon: 74.5815 },
  { id: 'satara', mr: 'सातारा', en: 'Satara', lat: 17.6805, lon: 74.0183 },
  { id: 'sindhudurg', mr: 'सिंधुदुर्ग', en: 'Sindhudurg', lat: 16.13, lon: 73.68 },
  { id: 'solapur', mr: 'सोलापूर', en: 'Solapur', lat: 17.6599, lon: 75.9064 },
  { id: 'thane', mr: 'ठाणे', en: 'Thane', lat: 19.2183, lon: 72.9781 },
  { id: 'wardha', mr: 'वर्धा', en: 'Wardha', lat: 20.7453, lon: 78.6022 },
  { id: 'washim', mr: 'वाशिम', en: 'Washim', lat: 20.1118, lon: 77.1333 },
  { id: 'yavatmal', mr: 'यवतमाळ', en: 'Yavatmal', lat: 20.3888, lon: 78.1204 },
];

// Nashik: Maharashtra's onion heartland, and a sensible default before the farmer picks.
export const DEFAULT_LOCATION_ID = 'nashik';

export function findLocation(id: string | null | undefined): Location {
  return LOCATIONS.find((l) => l.id === id)
    ?? LOCATIONS.find((l) => l.id === DEFAULT_LOCATION_ID)!;
}
