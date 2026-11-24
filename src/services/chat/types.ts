// Shared types for the chatbot service.
// Both the mock and the real Claude implementation share this contract.

export type ChatRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  text: string;
}

export interface ChatService {
  /**
   * Send the conversation so far plus the new user message; get the assistant's reply.
   * @param history all messages already in the conversation (including the new user one)
   * @param userText the latest user message text
   */
  sendMessage(history: ChatMessage[], userText: string): Promise<string>;
}
