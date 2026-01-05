/**
 * Handle folder operations - get or create folders by name and type.
 */

export interface FolderResult {
  success: boolean;
  folder_id?: string;
  folder_uuid?: string;
  name?: string;
  error?: string;
}

export interface DeleteFolderResult {
  success: boolean;
  deleted_count?: number;
  folder_name?: string;
  error?: string;
}

export interface FolderInfo {
  id: string;
  name: string;
  type: string;
  parent: string | null;
}

export interface ListFoldersResult {
  success: boolean;
  folders?: FolderInfo[];
  error?: string;
}

/**
 * List all folders, optionally filtered by type.
 */
export async function handleListFolders(data: {
  type?: string;
}): Promise<ListFoldersResult> {
  try {
    if (!game.folders) {
      return {
        success: false,
        error: 'No folders collection available'
      };
    }

    // Map all folders
    const allFolders = game.folders.map((f: FoundryDocument) => {
      const folderData = f as unknown as { type: string; folder: { _id: string } | string | null };
      // folder can be a string ID, a folder object with _id, or null
      let parentId: string | null = null;
      if (folderData.folder) {
        if (typeof folderData.folder === 'string') {
          parentId = folderData.folder;
        } else if (folderData.folder._id) {
          parentId = folderData.folder._id;
        }
      }
      return {
        id: f.id as string,
        name: f.name as string,
        type: folderData.type,
        parent: parentId
      };
    });

    // Filter by type if specified
    const folders = data.type
      ? allFolders.filter((f: FolderInfo) => f.type === data.type)
      : allFolders;

    console.log('[Tablewrite] Listed', folders.length, 'folders');

    return {
      success: true,
      folders
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to list folders:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}

/**
 * Get or create a folder by name and document type.
 *
 * @param data.name - Folder name (e.g., "Tablewrite")
 * @param data.type - Document type: "Actor", "Scene", "JournalEntry", "Item"
 * @param data.parent - Optional parent folder ID for nested folders
 */
export async function handleGetOrCreateFolder(data: {
  name: string;
  type: string;
  parent?: string | null;
}): Promise<FolderResult> {
  try {
    const { name, type, parent } = data;

    if (!name || !type) {
      return {
        success: false,
        error: 'Missing name or type'
      };
    }

    // Check if folder already exists (matching name, type, and parent)
    const existingFolder = game.folders?.find(
      (f: FoundryDocument) => {
        const folderData = f as unknown as { type: string; folder: { _id: string } | string | null };
        const matchesName = f.name === name;
        const matchesType = folderData.type === type;

        // Get the parent ID from folder data (can be string, object with _id, or null)
        let folderParentId: string | null = null;
        if (folderData.folder) {
          if (typeof folderData.folder === 'string') {
            folderParentId = folderData.folder;
          } else if (folderData.folder._id) {
            folderParentId = folderData.folder._id;
          }
        }

        const matchesParent = parent
          ? folderParentId === parent
          : !folderParentId;
        return matchesName && matchesType && matchesParent;
      }
    );

    if (existingFolder) {
      console.log(`[Tablewrite] Found existing folder: ${name} (${type})${parent ? ` in parent ${parent}` : ''}`);
      return {
        success: true,
        folder_id: existingFolder.id,
        folder_uuid: `Folder.${existingFolder.id}`,
        name: existingFolder.name
      };
    }

    // Create new folder
    // Foundry uses "folder" property for parent folder, not "parent"
    const folder = await Folder.create({
      name: name,
      type: type,
      folder: parent || null
    });

    if (folder) {
      console.log(`[Tablewrite] Created folder: ${name} (${type})${parent ? ` in parent ${parent}` : ''}`);
      return {
        success: true,
        folder_id: folder.id,
        folder_uuid: `Folder.${folder.id}`,
        name: folder.name
      };
    }

    return {
      success: false,
      error: 'Folder.create returned null'
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to get/create folder:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}

/**
 * Delete a folder and optionally all its contents.
 *
 * @param data.folder_id - Folder ID to delete
 * @param data.delete_contents - If true, delete all documents in the folder first (default: true)
 */
export async function handleDeleteFolder(data: {
  folder_id: string;
  delete_contents?: boolean;
}): Promise<DeleteFolderResult> {
  try {
    const { folder_id, delete_contents = true } = data;

    if (!folder_id) {
      return {
        success: false,
        error: 'Missing folder_id'
      };
    }

    // Find the folder
    const folders = game.folders as any;
    const folder = folders?.get(folder_id);
    if (!folder) {
      return {
        success: false,
        error: `Folder not found: ${folder_id}`
      };
    }

    const folderName = folder.name;
    const folderData = folder as unknown as { type: string };
    const folderType = folderData.type;
    let deletedCount = 0;

    // Delete contents if requested
    if (delete_contents) {
      // Get the appropriate collection based on folder type
      let collection: any;
      switch (folderType) {
        case 'Actor':
          collection = game.actors;
          break;
        case 'Scene':
          collection = (game as any).scenes;
          break;
        case 'JournalEntry':
          collection = (game as any).journal;
          break;
        case 'Item':
          collection = (game as any).items;
          break;
      }

      if (collection) {
        // Find all documents in this folder
        const docsInFolder = collection.filter((doc: FoundryDocument) => {
          const docData = doc as unknown as { folder: { _id: string } | string | null };
          if (!docData.folder) return false;
          const docFolderId = typeof docData.folder === 'string'
            ? docData.folder
            : docData.folder._id;
          return docFolderId === folder_id;
        });

        // Delete each document
        for (const doc of docsInFolder) {
          await doc.delete();
          deletedCount++;
        }
        console.log(`[Tablewrite] Deleted ${deletedCount} ${folderType}(s) from folder ${folderName}`);
      }

      // Also delete any child folders recursively
      const childFolders = folders?.filter((f: FoundryDocument) => {
        const fData = f as unknown as { folder: { _id: string } | string | null };
        if (!fData.folder) return false;
        const parentId = typeof fData.folder === 'string'
          ? fData.folder
          : fData.folder._id;
        return parentId === folder_id;
      }) || [];

      for (const childFolder of childFolders) {
        // Recursively delete child folder
        await handleDeleteFolder({ folder_id: childFolder.id as string, delete_contents: true });
      }
    }

    // Delete the folder itself
    await folder.delete();
    console.log(`[Tablewrite] Deleted folder: ${folderName} (${folder_id})`);

    return {
      success: true,
      deleted_count: deletedCount,
      folder_name: folderName
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to delete folder:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}
