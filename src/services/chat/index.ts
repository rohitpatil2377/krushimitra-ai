import { isApiConfigured } from '@/config';

import { apiChatService } from './apiChatService';
import { mockChatService } from './mockChatService';
import type { ChatMessage, ChatService } from './types';

export type { ChatMessage, ChatRole, ChatService } from './types';

/**
 * Returns the chat service to use.
 *  - No backend URL    -> offline mock.
 *  - Backend reachable -> FastAPI /copilot/ask; on failure fall back to the mock.
 */
export function getChatService(): ChatService {
  if (!isApiConfigured) {
    return mockChatService;
  }

  return {
    async sendMessage(history: ChatMessage[], userText: string): Promise<string> {
      try {
        return await apiChatService.sendMessage(history, userText);
      } catch (error) {
        console.warn('[chat] backend failed, using mock instead:', error);
        return mockChatService.sendMessage(history, userText);
      }
    },
  };
}
