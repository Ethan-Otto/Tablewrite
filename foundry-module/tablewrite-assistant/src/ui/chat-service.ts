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
   * @param history - Previous conversation history (must NOT include the current message)
   * @returns The assistant's response message
   */
  async send(message: string, history: ChatMessage[]): Promise<string> {
    const url = `${getBackendUrl()}/api/chat`;

    const conversationHistory = history.map(msg => ({
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
