/**
 * API client for Module Assistant backend.
 */

import axios from 'axios';
import type { AxiosInstance } from 'axios';
import type { ChatRequest, ChatResponse } from './types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ModuleAssistantAPI {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Send a chat message to the backend.
   */
  async chat(request: ChatRequest): Promise<ChatResponse> {
    const response = await this.client.post<ChatResponse>('/api/chat', request);
    return response.data;
  }

  /**
   * Health check endpoint.
   */
  async health(): Promise<{ status: string; service: string }> {
    const response = await this.client.get('/health');
    return response.data;
  }
}

// Export singleton instance
export const api = new ModuleAssistantAPI();
