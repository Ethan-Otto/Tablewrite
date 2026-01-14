/**
 * Message handlers for Tablewrite.
 */

export { handleActorCreate, handleGetActor, handleUpdateActor, handleDeleteActor, handleListActors, handleGiveItems, handleAddCustomItems, handleRemoveActorItems, handleUpdateActorItem } from './actor.js';
export { handleGetJournal, handleJournalCreate, handleJournalDelete, handleListJournals, handleUpdateJournal } from './journal.js';
export { handleSceneCreate, handleGetScene, handleDeleteScene, handleListScenes } from './scene.js';
export { handleSearchItems, handleGetItem, handleListCompendiumItems } from './items.js';
export { handleListFiles, handleFileUpload } from './files.js';
export { handleGetOrCreateFolder, handleListFolders, handleDeleteFolder } from './folder.js';

import { handleActorCreate, handleGetActor, handleUpdateActor, handleDeleteActor, handleListActors, handleGiveItems, handleAddCustomItems, handleRemoveActorItems, handleUpdateActorItem } from './actor.js';
import { handleGetJournal, handleJournalCreate, handleJournalDelete, handleListJournals, handleUpdateJournal, JournalListResult, UpdateJournalResult } from './journal.js';
import { handleSceneCreate, handleGetScene, handleDeleteScene, handleListScenes } from './scene.js';
import { handleSearchItems, handleGetItem, handleListCompendiumItems } from './items.js';
import { handleListFiles, handleFileUpload } from './files.js';
import { handleGetOrCreateFolder, handleListFolders, handleDeleteFolder, FolderResult, ListFoldersResult, DeleteFolderResult } from './folder.js';

export type MessageType = 'actor' | 'journal' | 'get_journal' | 'delete_journal' | 'list_journals' | 'update_journal' | 'scene' | 'get_scene' | 'delete_scene' | 'list_scenes' | 'get_actor' | 'update_actor' | 'delete_actor' | 'list_actors' | 'give_items' | 'add_custom_items' | 'remove_actor_items' | 'update_actor_item' | 'search_items' | 'get_item' | 'list_compendium_items' | 'list_files' | 'upload_file' | 'get_or_create_folder' | 'list_folders' | 'delete_folder' | 'module_progress' | 'connected' | 'pong';

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

export interface SceneInfo {
  uuid: string;
  id: string;
  name: string;
  folder: string | null;
}

export interface SceneListResult {
  success: boolean;
  scenes?: SceneInfo[];
  error?: string;
}

export interface RemoveItemsResult {
  success: boolean;
  actor_uuid?: string;
  items_removed?: number;
  removed_names?: string[];
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

export interface FileUploadResult {
  success: boolean;
  path?: string;
  error?: string;
}

export interface MessageResult {
  responseType: string;
  request_id?: string;
  data?: CreateResult | GetResult | DeleteResult | ListResult | SceneListResult | GiveResult | RemoveItemsResult | SearchResult | FileListResult | FileUploadResult | FolderResult | ListFoldersResult | DeleteFolderResult | JournalListResult | UpdateJournalResult;
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
      return {
        responseType: 'actor_error',
        request_id: message.request_id,
        error: 'Missing data for actor creation'
      };
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
      return {
        responseType: 'journal_error',
        request_id: message.request_id,
        error: 'Missing data for journal creation'
      };
    case 'get_journal':
      if (message.data?.uuid) {
        const result = await handleGetJournal(message.data.uuid as string);
        return {
          responseType: result.success ? 'journal_data' : 'journal_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      return {
        responseType: 'journal_error',
        request_id: message.request_id,
        error: 'Missing uuid for get_journal'
      };
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
      return {
        responseType: 'journal_error',
        request_id: message.request_id,
        error: 'Missing uuid for journal deletion'
      };
    case 'list_journals': {
      const result = await handleListJournals();
      return {
        responseType: result.success ? 'journals_list' : 'journal_error',
        request_id: message.request_id,
        data: result,
        error: result.error
      };
    }
    case 'update_journal':
      if (message.data) {
        const result = await handleUpdateJournal(message.data as {
          uuid: string;
          updates: Record<string, unknown>;
        });
        return {
          responseType: result.success ? 'journal_updated' : 'journal_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      return {
        responseType: 'journal_error',
        request_id: message.request_id,
        error: 'Missing data for update_journal'
      };
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
      return {
        responseType: 'scene_error',
        request_id: message.request_id,
        error: 'Missing data for scene creation'
      };
    case 'get_scene':
      if (message.data?.uuid) {
        const result = await handleGetScene(message.data.uuid as string);
        return {
          responseType: result.success ? 'scene_data' : 'scene_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      return {
        responseType: 'scene_error',
        request_id: message.request_id,
        error: 'Missing uuid for get_scene'
      };
    case 'delete_scene':
      if (message.data?.uuid) {
        const result = await handleDeleteScene(message.data.uuid as string);
        return {
          responseType: result.success ? 'scene_deleted' : 'scene_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      return {
        responseType: 'scene_error',
        request_id: message.request_id,
        error: 'Missing uuid for delete_scene'
      };
    case 'list_scenes': {
      const result = await handleListScenes();
      return {
        responseType: result.success ? 'scenes_list' : 'scene_error',
        request_id: message.request_id,
        data: result,
        error: result.error
      };
    }
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
      return {
        responseType: 'actor_error',
        request_id: message.request_id,
        error: 'Missing uuid for get_actor'
      };
    case 'update_actor':
      if (message.data) {
        const result = await handleUpdateActor(message.data as {
          uuid: string;
          updates: Record<string, unknown>;
        });
        return {
          responseType: result.success ? 'actor_updated' : 'actor_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      return {
        responseType: 'actor_error',
        request_id: message.request_id,
        error: 'Missing data for update_actor'
      };
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
      return {
        responseType: 'actor_error',
        request_id: message.request_id,
        error: 'Missing uuid for delete_actor'
      };
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
      return {
        responseType: 'give_error',
        request_id: message.request_id,
        error: 'Missing data for give_items'
      };
    case 'add_custom_items':
      if (message.data) {
        const result = await handleAddCustomItems(message.data as {
          actor_uuid: string;
          items: Array<{
            name: string;
            type: 'weapon' | 'feat';
            description: string;
            damage_formula?: string;
            damage_type?: string;
            attack_bonus?: number;
            range?: number;
            activation?: string;
            save_dc?: number;
            save_ability?: string;
            aoe_type?: string;
            aoe_size?: number;
            on_save?: string;
          }>;
        });
        return {
          responseType: result.success ? 'custom_items_added' : 'custom_items_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      return {
        responseType: 'custom_items_error',
        request_id: message.request_id,
        error: 'Missing data for add_custom_items'
      };
    case 'remove_actor_items': {
      const result = await handleRemoveActorItems(message.data as { actor_uuid: string; item_names: string[] });
      return {
        responseType: result.success ? 'actor_items_removed' : 'actor_error',
        request_id: message.request_id,
        data: result,
        error: result.error
      };
    }
    case 'update_actor_item': {
      const result = await handleUpdateActorItem(message.data as {
        actor_uuid: string;
        item_name: string;
        updates: {
          name?: string;
          attack_bonus?: number;
          damage_formula?: string;
          damage_type?: string;
          damage_bonus?: string;
          description?: string;
          range?: number;
          range_long?: number;
          weapon_type?: string;
          properties?: Record<string, boolean>;
        };
      });
      return {
        responseType: result.success ? 'actor_item_updated' : 'actor_error',
        request_id: message.request_id,
        data: result,
        error: result.error
      };
    }
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
      return {
        responseType: 'search_error',
        request_id: message.request_id,
        error: 'Missing data for search_items'
      };
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
      return {
        responseType: 'item_error',
        request_id: message.request_id,
        error: 'Missing uuid for get_item'
      };
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
      return {
        responseType: 'files_error',
        request_id: message.request_id,
        error: 'Missing data for list_files'
      };
    case 'upload_file':
      if (message.data) {
        const result = await handleFileUpload(message.data as {
          filename: string;
          content: string;
          destination: string;
        });
        return {
          responseType: result.success ? 'file_uploaded' : 'file_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      return {
        responseType: 'file_error',
        request_id: message.request_id,
        error: 'Missing data for upload_file'
      };
    case 'get_or_create_folder':
      if (message.data) {
        const result = await handleGetOrCreateFolder(message.data as {
          name: string;
          type: string;
          parent?: string | null;
        });
        return {
          responseType: result.success ? 'folder_result' : 'folder_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      return {
        responseType: 'folder_error',
        request_id: message.request_id,
        error: 'Missing data for get_or_create_folder'
      };
    case 'list_folders': {
      const result = await handleListFolders(message.data as { type?: string } || {});
      return {
        responseType: result.success ? 'folders_list' : 'folder_error',
        request_id: message.request_id,
        data: result,
        error: result.error
      };
    }
    case 'delete_folder':
      if (message.data?.folder_id) {
        const result = await handleDeleteFolder(message.data as {
          folder_id: string;
          delete_contents?: boolean;
        });
        return {
          responseType: result.success ? 'folder_deleted' : 'folder_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      return {
        responseType: 'folder_error',
        request_id: message.request_id,
        error: 'Missing folder_id for delete_folder'
      };
    case 'module_progress':
      if (message.data) {
        // Emit a Foundry hook for UI components to listen to
        // Use 'on' to call all registered listeners for custom hooks
        (Hooks as any).callAll('tablewrite.moduleProgress', {
          stage: message.data.stage as string,
          message: message.data.message as string,
          progress: message.data.progress as number | undefined,
          module_name: message.data.module_name as string | undefined
        });
        console.log(`[Tablewrite] Progress: ${message.data.stage} - ${message.data.message}`);
      }
      return null;  // No response needed
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
