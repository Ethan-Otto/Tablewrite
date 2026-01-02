/**
 * Chat service for HTTP communication with backend.
 */

import { getBackendUrl } from '../settings.js';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date;
}

interface ChatResponse {
  message: string;
  type: string;
  data?: Record<string, unknown>;
}

class ChatService {
  /**
   * Send a message to the backend chat endpoint.
   * @param message - The user's message
   * @param history - Full conversation history (current message is last item)
   * @returns The assistant's response message
   */
  async send(message: string, history: ChatMessage[]): Promise<string> {
    const url = `${getBackendUrl()}/api/chat`;

    // Exclude the current message from history if it's the last item
    // (the UI may add the user message to history before calling send)
    const lastMessage = history[history.length - 1];
    const shouldExcludeLast = lastMessage?.content === message && lastMessage?.role === 'user';
    const historyToSend = shouldExcludeLast ? history.slice(0, -1) : history;

    const conversationHistory = historyToSend.map(msg => ({
      role: msg.role,
      content: msg.content,
      timestamp: msg.timestamp?.toISOString() ?? new Date().toISOString()
    }));

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        context: {},
        conversation_history: conversationHistory
      })
    });

    if (!response.ok) {
      throw new Error(`Chat request failed: ${response.status}`);
    }

    const data: ChatResponse = await response.json();
    return data.message;
  }
}

export const chatService = new ChatService();
