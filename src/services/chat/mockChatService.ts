import type { ChatMessage, ChatService } from './types';

// Offline mock chatbot. Gives helpful Marathi answers based on simple keyword matching.
// Used until the Claude Edge Function is deployed. Keeps the UX fully working with no key.

interface Rule {
  keywords: string[];
  reply: string;
}

const RULES: Rule[] = [
  {
    keywords: ['पाणी', 'सिंचन', 'ठिबक', 'water'],
    reply:
      'पाणी पिकानुसार आणि हवामानानुसार द्यावे. जमिनीत ओलावा बोटाने तपासा — वरचा ५ सें.मी. थर कोरडा वाटल्यास पाणी द्या. शक्यतो सकाळी लवकर किंवा संध्याकाळी पाणी द्या आणि ठिबक सिंचन वापरल्यास पाण्याची बचत होते.',
  },
  {
    keywords: ['रोग', 'कीड', 'किडे', 'ठिपके', 'बुरशी', 'disease'],
    reply:
      'रोग ओळखण्यासाठी "रोग ओळख" मध्ये पिकाचा फोटो काढा. सर्वसाधारणपणे रोगट पाने काढून नष्ट करा, झाडांमध्ये हवा खेळती राहील असे अंतर ठेवा आणि गरज पडल्यास योग्य बुरशीनाशकाची फवारणी करा.',
  },
  {
    keywords: ['खत', 'fertilizer', 'युरिया', 'खते'],
    reply:
      'खताचे प्रमाण माती परीक्षणावर अवलंबून असते. नत्र (N), स्फुरद (P) आणि पालाश (K) यांचा समतोल ठेवा. सेंद्रिय खत (शेणखत/कंपोस्ट) वापरल्यास जमिनीची सुपीकता वाढते. रासायनिक खत टप्प्याटप्प्याने द्या.',
  },
  {
    keywords: ['हवामान', 'पाऊस', 'weather', 'rain'],
    reply:
      '"हवामान" मध्ये तुमच्या भागातील अंदाज पाहा. पाऊस येणार असल्यास फवारणी व पाणी देणे टाळा. उन्हाची तीव्रता जास्त असल्यास पिकाला पुरेसे पाणी मिळेल याची काळजी घ्या.',
  },
  {
    keywords: ['भाव', 'बाजार', 'दर', 'price', 'market', 'मंडई'],
    reply:
      '"बाजारभाव" मध्ये जवळच्या बाजारातील ताजे दर पाहा. भाव चांगला असताना विक्री करा आणि शक्य असल्यास एकाच वेळी सर्व माल विकण्याऐवजी टप्प्याटप्प्याने विका.',
  },
];

const GREETING =
  'नमस्कार! 🙏 मी कृषीमित्र आहे. पिकाचे रोग, पाणी, खत, हवामान किंवा बाजारभाव — यापैकी कशाबद्दलही विचारा.';

const FALLBACK =
  'मला तुमचा प्रश्न नीट समजला नाही. कृपया पिकाचे नाव आणि अडचण थोडक्यात सांगा. उदा. "टोमॅटोच्या पानांवर ठिपके आहेत, काय करू?"';

function findReply(userText: string): string {
  const text = userText.toLowerCase();
  if (/नमस्कार|नमस्ते|hello|hi|हाय/.test(text)) {
    return GREETING;
  }
  for (const rule of RULES) {
    if (rule.keywords.some((k) => text.includes(k.toLowerCase()))) {
      return rule.reply;
    }
  }
  return FALLBACK;
}

export const mockChatService: ChatService = {
  async sendMessage(_history: ChatMessage[], userText: string): Promise<string> {
    // Simulate "thinking" so the typing indicator is visible.
    await new Promise((resolve) => setTimeout(resolve, 900));
    return findReply(userText);
  },
};
