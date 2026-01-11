/**
 * Chat service for HTTP communication with backend.
 */

import { getBackendUrl, isTokenArtEnabled, getArtStyle } from '../settings.js';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date;
  type?: string;
  imageUrls?: string[];
}

export interface ChatResponse {
  message: string;
  type: string;
  data?: {
    image_urls?: string[];
    [key: string]: unknown;
  };
}

class ChatService {
  /**
   * Send a message to the backend chat endpoint.
   * @param message - The user's message
   * @param history - Previous conversation history (must NOT include the current message)
   * @returns The full response object including type and image data
   */
  async send(message: string, history: ChatMessage[]): Promise<ChatResponse> {
    const url = `${getBackendUrl()}/api/chat`;

    const conversationHistory = history.map(msg => ({
      role: msg.role,
      content: msg.content,
      timestamp: msg.timestamp?.toISOString() ?? new Date().toISOString()
    }));

    // Include user settings and game system in context
    const context = {
      settings: {
        tokenArtEnabled: isTokenArtEnabled(),
        artStyle: getArtStyle()
      },
      gameSystem: {
        id: (game as any).system?.id ?? 'unknown',
        title: (game as any).system?.title ?? 'Unknown System'
      }
    };

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        context,
        conversation_history: conversationHistory
      })
    });

    if (!response.ok) {
      throw new Error(`Chat request failed: ${response.status}`);
    }

    return await response.json();
  }
}

export const chatService = new ChatService();
