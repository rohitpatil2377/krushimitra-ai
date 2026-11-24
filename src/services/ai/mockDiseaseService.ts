import type {
  CropImageInput,
  DiagnosisFeedback,
  DiseaseDiagnosis,
  DiseaseService,
} from './types';

// SAMPLE DATA — not analysis. The photo is never looked at; the result is a fixed per-crop
// demo value, so two different photos of the same crop give the same answer.
//
// It exists so the app is fully usable with no backend (the repo's mock-first convention) and
// so the farmer sees something rather than an error on a dead network. Its honesty contract is
// `modelVersion: 'mock-app'` → the screen shows the "नमुना माहिती" (sample data) badge.
// Marathi content mirrors the backend knowledge base so the demo stays consistent.

const MOCK_VERSION = 'mock-app';

const SAMPLES: Record<string, DiseaseDiagnosis> = {
  onion: {
    diseaseName: 'जांभळा करपा',
    diseaseNameEn: 'Purple Blotch',
    diseaseSlug: 'onion_purple_blotch',
    kind: 'fungal',
    confidence: 'medium',
    confidenceScore: 0.78,
    identified: true,
    cause:
      'अल्टरनेरिया पोरी नावाच्या बुरशीमुळे होतो. दमट हवामान, पानांवर साचलेले पाणी आणि रात्रीची जास्त आर्द्रता असल्यास झपाट्याने वाढतो.',
    treatment: [
      'मॅन्कोझेब किंवा क्लोरोथॅलोनिल या बुरशीनाशकाची प्रतिबंधात्मक फवारणी करा.',
      'रोग वाढला असल्यास टेब्युकोनॅझोल किंवा डायफेनोकोनॅझोलकडे वळा.',
      'फवारणीत चिकटद्रव्य (स्टिकर) मिसळा, नाहीतर औषध पानांवर टिकत नाही.',
    ],
    prevention: [
      'पिकाची फेरपालट करा — सलग त्याच जमिनीत कांदा लावू नका.',
      'दोन रोपांमध्ये योग्य अंतर ठेवा म्हणजे हवा खेळती राहील.',
      'सकाळी पाणी द्या; संध्याकाळी पाने ओली राहू देऊ नका.',
    ],
    chemicals: ['mancozeb', 'chlorothalonil', 'tebuconazole'],
    curable: true,
    severity: {
      level: 'moderate',
      severityPct: 23,
      riskLevel: 'medium',
      recommendedAction:
        'रोग पसरत आहे — २४ तासांत उपाय करा आणि रोगट भाग काढून नष्ट करा. ४–५ दिवसांनी पुन्हा फोटो काढून तपासा.',
      method: 'mock',
    },
    modelVersion: MOCK_VERSION,
    isMock: true,
  },
  soybean: {
    diseaseName: 'तांबेरा (रस्ट)',
    diseaseNameEn: 'Soybean Rust',
    diseaseSlug: 'soybean_rust',
    kind: 'fungal',
    confidence: 'medium',
    confidenceScore: 0.74,
    identified: true,
    cause:
      'फॅकोस्पोरा पॅकिऱ्हायझी या बुरशीमुळे होणारा तांबेरा. पानांच्या खालच्या बाजूस तांबूस पुटकुळ्या येतात आणि पाने गळतात.',
    treatment: [
      'हेक्साकोनॅझोल, प्रोपिकोनॅझोल किंवा टेब्युकोनॅझोल यांपैकी एकाची फवारणी करा.',
      'पहिली पुटकुळी दिसताच फवारणी करा — उशीर झाल्यास पाने वाचत नाहीत.',
      'फवारणी पानांच्या खालच्या बाजूवर पोहोचली पाहिजे.',
    ],
    prevention: [
      'शिफारशीत रोगप्रतिकारक वाण निवडा.',
      'शेतात पाणी साचू देऊ नका; निचरा चांगला ठेवा.',
      'दाट पेरणी टाळा म्हणजे पिकात हवा खेळेल.',
    ],
    chemicals: ['hexaconazole', 'propiconazole', 'tebuconazole'],
    curable: true,
    severity: {
      level: 'moderate',
      severityPct: 22,
      riskLevel: 'medium',
      recommendedAction:
        'रोग पसरत आहे — २४ तासांत उपाय करा आणि रोगट भाग काढून नष्ट करा. ४–५ दिवसांनी पुन्हा फोटो काढून तपासा.',
      method: 'mock',
    },
    modelVersion: MOCK_VERSION,
    isMock: true,
  },
  pomegranate: {
    diseaseName: 'तेल्या रोग',
    diseaseNameEn: 'Bacterial Blight (Telya)',
    diseaseSlug: 'pomegranate_bacterial_blight',
    kind: 'bacterial',
    confidence: 'high',
    confidenceScore: 0.83,
    identified: true,
    cause:
      'झँथोमोनास या जिवाणूमुळे होणारा तेल्या रोग. पाने व फळांवर तेलकट काळे डाग पडतात आणि फळांना तडे जातात.',
    treatment: [
      'कॉपर ऑक्सिक्लोराईड किंवा बोर्डो मिश्रणाची फवारणी हा पाया आहे.',
      'रोगट फांद्या निरोगी भागापर्यंत छाटून जाळून टाका.',
      'छाटणीची अवजारे प्रत्येक झाडानंतर निर्जंतुक करा — नाहीतर तुम्हीच रोग पसरवता.',
    ],
    prevention: [
      'रोगमुक्त, प्रमाणित कलमेच लावा.',
      'पावसाळी बहार (मृग बहार) टाळा.',
      'बाग स्वच्छ ठेवा; गळलेली पाने–फळे गोळा करून नष्ट करा.',
    ],
    chemicals: ['copper oxychloride', 'bordeaux mixture'],
    curable: false,
    note: 'तेल्या पूर्ण बरा होत नाही — एकात्मिक व्यवस्थापनाने आटोक्यात ठेवावा लागतो.',
    severity: {
      level: 'moderate',
      severityPct: 25,
      riskLevel: 'medium',
      recommendedAction:
        'फवारणीने हे बरे होणार नाही — रोगट झाडे काढणे, बागेची स्वच्छता आणि वाहक किडीचे नियंत्रण यावर भर द्या. ५ दिवसांनी पुन्हा तपासा.',
      method: 'mock',
    },
    modelVersion: MOCK_VERSION,
    isMock: true,
  },
};

// With no crop selected the mock can't even pretend — so it abstains, which is also what the
// real backend does when it isn't sure. Better a consistent "not sure" than a fake answer.
const UNSURE: DiseaseDiagnosis = {
  diseaseName: 'निदान निश्चित नाही',
  diseaseNameEn: 'Not identified',
  diseaseSlug: 'unknown',
  kind: 'none',
  confidence: 'low',
  confidenceScore: 0.3,
  identified: false,
  cause:
    'या फोटोवरून रोगाचे निदान खात्रीने करता आलेले नाही. चुकीचे निदान देण्यापेक्षा "माहीत नाही" सांगणे योग्य आहे.',
  treatment: [],
  prevention: [
    'तुमचे पीक वरून निवडा, मग पुन्हा फोटो काढा.',
    'रोगट भागाचा जवळून, स्पष्ट उजेडात फोटो काढा.',
    'पानाच्या वरच्या आणि खालच्या अशा दोन्ही बाजूंचे फोटो काढा.',
  ],
  chemicals: [],
  curable: false,
  note: 'निदान निश्चित नाही — कृपया पीक निवडा किंवा अधिक स्पष्ट फोटो काढा.',
  modelVersion: MOCK_VERSION,
  isMock: true,
};

export const mockDiseaseService: DiseaseService = {
  async analyzeCropImage(input: CropImageInput): Promise<DiseaseDiagnosis> {
    // Simulate a network round-trip so the loading state is visible.
    await new Promise((resolve) => setTimeout(resolve, 1500));
    return (input.cropId && SAMPLES[input.cropId]) || UNSURE;
  },

  async submitFeedback(_input: DiagnosisFeedback): Promise<boolean> {
    // Nothing to record against sample data — the screen hides the buttons in this case anyway,
    // since a mock result carries no diagnosisId.
    return false;
  },
};
