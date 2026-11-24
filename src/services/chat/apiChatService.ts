import i18n from '@/i18n';
import { postForm } from '@/services/api';

import type { ChatMessage, ChatService } from './types';

// Chatbot via the FastAPI copilot (`POST /copilot/ask`).
// Sends the latest user text + current UI language; gets back the Marathi/Hindi/English reply.

interface CopilotResponse {
  reply_text: string;
  lang: string;
}

export const apiChatService: ChatService = {
  async sendMessage(_history: ChatMessage[], userText: string): Promise<string> {
    const form = new FormData();
    form.append('text', userText);
    form.append('lang', i18n.language || 'mr');

    const data = await postForm<CopilotResponse>('/copilot/ask', form);
    return data.reply_text;
  },
};
