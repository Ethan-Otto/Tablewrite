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

export interface ImageData {
  image_urls: string[];
  prompt: string;
}

export interface SceneData {
  scene: Scene;
}

export interface ChatMessage {
  role: ChatRole;
  content: string;
  timestamp: string;
  type?: string;  // NEW: response type
  data?: ImageData | SceneData | Record<string, any> | null;  // NEW: tool-specific data
  scene?: Scene | null;  // Keep for backwards compatibility
}

export interface ChatRequest {
  message: string;
  context?: Record<string, any>;
  conversation_history?: ChatMessage[];
}

export interface ChatResponse {
  message: string;
  type: 'text' | 'image' | 'scene' | 'actor' | 'error';
  data?: ImageData | SceneData | Record<string, any> | null;
  scene?: any | null;
}
