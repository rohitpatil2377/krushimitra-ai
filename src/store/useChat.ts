import { create } from 'zustand';

import type { ChatMessage, ChatRole } from '@/services/chat';

interface ChatState {
  messages: ChatMessage[];
  /** Add a message; generates the id automatically. */
  addMessage: (role: ChatRole, text: string) => void;
  clear: () => void;
}

let counter = 0;
function nextId(): string {
  counter += 1;
  return `${Date.now()}-${counter}`;
}

export const useChat = create<ChatState>((set) => ({
  messages: [],
  addMessage: (role, text) =>
    set((state) => ({
      messages: [...state.messages, { id: nextId(), role, text }],
    })),
  clear: () => set({ messages: [] }),
}));
