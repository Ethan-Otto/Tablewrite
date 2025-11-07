import { useState, useCallback } from 'react';
import type { ChatMessage, ChatRequest } from '../lib/types';
import { ChatRole } from '../lib/types';
import { api } from '../lib/api';

interface UseChatReturn {
  messages: ChatMessage[];
  sendMessage: (content: string) => Promise<void>;
  isLoading: boolean;
  error: string | null;
  clearError: () => void;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: ChatRole.SYSTEM,
      content: 'Welcome to the D&D Module Assistant',
      timestamp: new Date().toISOString()
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;

    // Add user message
    const userMessage: ChatMessage = {
      role: ChatRole.USER,
      content,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);

    // Check if this might be an image generation request
    const isImageRequest = content.toLowerCase().match(/\b(generate|create|show|make).*(image|picture|photo|illustration)|image.*of/);

    // Check if this might be an actor creation request
    const isActorRequest = content.toLowerCase().match(/\b(create|make|generate|summon|spawn).*(actor|creature|monster|npc|character|goblin|dragon|kobold|orc|bugbear|beast)/);

    // Determine loading message
    let loadingContent = 'Fabricating....';
    if (isActorRequest && !isImageRequest) {
      loadingContent = 'Fabricating actor....';
    }

    // Add loading placeholder for image or actor requests
    if (isImageRequest || isActorRequest) {
      const loadingMessage: ChatMessage = {
        role: ChatRole.ASSISTANT,
        content: loadingContent,
        timestamp: new Date().toISOString(),
        type: 'loading'
      };
      setMessages(prev => [...prev, loadingMessage]);
    }

    setIsLoading(true);
    setError(null);

    try {
      // Prepare request with conversation history (last 10 messages)
      const request: ChatRequest = {
        message: content,
        context: {},
        conversation_history: messages.slice(-10)
      };

      // Call backend API
      const response = await api.chat(request);

      console.log('[DEBUG] API response:', response);

      // Add assistant response with optional scene data
      const assistantMessage: ChatMessage = {
        role: ChatRole.ASSISTANT,
        content: response.message,
        timestamp: new Date().toISOString(),
        type: response.type || 'text',
        data: response.data || null,
        scene: response.scene || null,  // Keep for backwards compatibility
      };
      console.log('[DEBUG] Assistant message:', assistantMessage);

      // Remove loading message and add real response
      setMessages(prev => {
        // Remove the loading message if it exists (for both image and actor requests)
        const filtered = (isImageRequest || isActorRequest) ? prev.filter(m => m.type !== 'loading') : prev;
        return [...filtered, assistantMessage];
      });

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to send message';
      setError(errorMessage);

      // Add error message to chat
      const errorChatMessage: ChatMessage = {
        role: ChatRole.SYSTEM,
        content: `Error: ${errorMessage}`,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => {
        // Remove loading message if it exists
        const filtered = prev.filter(m => m.type !== 'loading');
        return [...filtered, errorChatMessage];
      });
    } finally {
      setIsLoading(false);
    }
  }, [messages]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    messages,
    sendMessage,
    isLoading,
    error,
    clearError
  };
}
