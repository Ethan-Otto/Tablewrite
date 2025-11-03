/**
 * TypeScript types for Module Assistant API.
 */

export enum ChatRole {
  USER = 'user',
  ASSISTANT = 'assistant',
  SYSTEM = 'system',
}

export interface Scene {
  section_path: string;
  name: string;
  description: string;
  location_type: string;
  xml_section_id?: string | null;
  image_url?: string | null;
}

export interface ChatMessage {
  role: ChatRole;
  content: string;
  timestamp: string;
  scene?: Scene | null;
}

export interface ChatRequest {
  message: string;
  context?: Record<string, any>;
  conversation_history?: ChatMessage[];
}

export interface ChatResponse {
  message: string;
  type: 'text' | 'scene' | 'list' | 'error';
  data?: Record<string, any> | null;
  scene?: any | null;
}
