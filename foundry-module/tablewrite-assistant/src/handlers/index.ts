/**
 * Message handlers for Tablewrite.
 */

export { handleActorCreate, handleGetActor, handleDeleteActor, handleListActors, handleGiveItems } from './actor.js';
export { handleJournalCreate, handleJournalDelete } from './journal.js';
export { handleSceneCreate } from './scene.js';
export { handleSearchItems, handleGetItem, handleListCompendiumItems } from './items.js';
export { handleListFiles } from './files.js';

import { handleActorCreate, handleGetActor, handleDeleteActor, handleListActors, handleGiveItems } from './actor.js';
import { handleJournalCreate, handleJournalDelete } from './journal.js';
import { handleSceneCreate } from './scene.js';
import { handleSearchItems, handleGetItem, handleListCompendiumItems } from './items.js';
import { handleListFiles } from './files.js';

export type MessageType = 'actor' | 'journal' | 'delete_journal' | 'scene' | 'get_actor' | 'delete_actor' | 'list_actors' | 'give_items' | 'search_items' | 'get_item' | 'list_compendium_items' | 'list_files' | 'connected' | 'pong';

export interface TablewriteMessage {
  type: MessageType;
  data?: Record<string, unknown>;
  client_id?: string;
  request_id?: string;
}

export interface CreateResult {
  success: boolean;
  id?: string;
  uuid?: string;
  name?: string;
  error?: string;
}

export interface GetResult {
  success: boolean;
  entity?: Record<string, unknown>;
  error?: string;
}

export interface DeleteResult {
  success: boolean;
  uuid?: string;
  name?: string;
  error?: string;
}

export interface ActorInfo {
  uuid: string;
  id: string;
  name: string;
}

export interface ListResult {
  success: boolean;
  actors?: ActorInfo[];
  error?: string;
}

export interface GiveResult {
  success: boolean;
  actor_uuid?: string;
  items_added?: number;
  errors?: string[];
  error?: string;
}

export interface SearchResultItem {
  uuid: string;
  id: string;
  name: string;
  type?: string;
  img?: string;
  pack?: string;
  system?: {
    level?: number;
    school?: string;
  };
}

export interface SearchResult {
  success: boolean;
  results?: SearchResultItem[];
  error?: string;
}

export interface FileListResult {
  success: boolean;
  files?: string[];
  error?: string;
}

export interface MessageResult {
  responseType: string;
  request_id?: string;
  data?: CreateResult | GetResult | DeleteResult | ListResult | GiveResult | SearchResult | FileListResult;
  error?: string;
}

/**
 * Route a message to the appropriate handler.
 * Returns a result that should be sent back to the backend.
 */
export async function handleMessage(message: TablewriteMessage): Promise<MessageResult | null> {
  switch (message.type) {
    case 'actor':
      if (message.data) {
        const result = await handleActorCreate(message.data);
        return {
          responseType: result.success ? 'actor_created' : 'actor_error',
          request_id: message.request_id,
          data: result.success ? result : undefined,
          error: result.error
        };
      }
      break;
    case 'journal':
      if (message.data) {
        const result = await handleJournalCreate(message.data);
        return {
          responseType: result.success ? 'journal_created' : 'journal_error',
          request_id: message.request_id,
          data: result.success ? result : undefined,
          error: result.error
        };
      }
      break;
    case 'delete_journal':
      if (message.data?.uuid) {
        const result = await handleJournalDelete(message.data.uuid as string);
        return {
          responseType: result.success ? 'journal_deleted' : 'journal_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      break;
    case 'scene':
      if (message.data) {
        const result = await handleSceneCreate(message.data);
        return {
          responseType: result.success ? 'scene_created' : 'scene_error',
          request_id: message.request_id,
          data: result.success ? result : undefined,
          error: result.error
        };
      }
      break;
    case 'get_actor':
      if (message.data?.uuid) {
        const result = await handleGetActor(message.data.uuid as string);
        return {
          responseType: result.success ? 'actor_data' : 'actor_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      break;
    case 'delete_actor':
      if (message.data?.uuid) {
        const result = await handleDeleteActor(message.data.uuid as string);
        return {
          responseType: result.success ? 'actor_deleted' : 'actor_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      break;
    case 'list_actors': {
      const result = await handleListActors();
      return {
        responseType: result.success ? 'actors_list' : 'actor_error',
        request_id: message.request_id,
        data: result,
        error: result.error
      };
    }
    case 'give_items':
      if (message.data) {
        const result = await handleGiveItems(message.data as {
          actor_uuid: string;
          item_uuids: string[];
        });
        return {
          responseType: result.success ? 'items_given' : 'give_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      break;
    case 'search_items':
      if (message.data) {
        const result = await handleSearchItems(message.data as {
          query: string;
          documentType?: string;
          subType?: string;
        });
        return {
          responseType: result.success ? 'items_found' : 'search_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      break;
    case 'get_item':
      if (message.data?.uuid) {
        const result = await handleGetItem(message.data.uuid as string);
        return {
          responseType: result.success ? 'item_data' : 'item_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      break;
    case 'list_compendium_items': {
      const result = await handleListCompendiumItems(message.data as {
        documentType?: string;
        subType?: string;
      } || {});
      return {
        responseType: result.success ? 'compendium_items_list' : 'compendium_items_error',
        request_id: message.request_id,
        data: result,
        error: result.error
      };
    }
    case 'list_files':
      if (message.data) {
        const result = await handleListFiles(message.data as {
          path: string;
          source?: 'data' | 'public' | 's3';
          recursive?: boolean;
          extensions?: string[];
        });
        return {
          responseType: result.success ? 'files_list' : 'files_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      break;
    case 'connected':
      console.log('[Tablewrite] Connected with client_id:', message.client_id);
      return null;  // No response needed
    case 'pong':
      // Heartbeat response, no action needed
      return null;
    default:
      console.warn('[Tablewrite] Unknown message type:', message.type);
      return null;
  }
  return null;
}
