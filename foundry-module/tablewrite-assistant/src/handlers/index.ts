/**
 * Message handlers for Tablewrite.
 */

export { handleActorCreate } from './actor';
export { handleJournalCreate } from './journal';
export { handleSceneCreate } from './scene';

import { handleActorCreate } from './actor';
import { handleJournalCreate } from './journal';
import { handleSceneCreate } from './scene';

export type MessageType = 'actor' | 'journal' | 'scene' | 'connected' | 'pong';

export interface TablewriteMessage {
  type: MessageType;
  data?: Record<string, unknown>;
  client_id?: string;
}

/**
 * Route a message to the appropriate handler.
 */
export async function handleMessage(message: TablewriteMessage): Promise<void> {
  switch (message.type) {
    case 'actor':
      if (message.data) {
        await handleActorCreate(message.data);
      }
      break;
    case 'journal':
      if (message.data) {
        await handleJournalCreate(message.data);
      }
      break;
    case 'scene':
      if (message.data) {
        await handleSceneCreate(message.data);
      }
      break;
    case 'connected':
      console.log('[Tablewrite] Connected with client_id:', message.client_id);
      break;
    case 'pong':
      // Heartbeat response, no action needed
      break;
    default:
      console.warn('[Tablewrite] Unknown message type:', message.type);
  }
}
