/**
 * Handle journal messages from backend.
 *
 * Message format for create: {journal: {...}, name: string}
 * Message format for delete: {uuid: "JournalEntry.xyz"}
 */

import type { CreateResult, DeleteResult, GetResult } from './index.js';

export interface JournalInfo {
  uuid: string;
  id: string;
  name: string;
  folder: string | null;
}

export interface JournalListResult {
  success: boolean;
  journals?: JournalInfo[];
  error?: string;
}

export interface UpdateJournalResult {
  success: boolean;
  uuid?: string;
  id?: string;
  name?: string;
  error?: string;
}

/**
 * Handle get journal request - fetch a journal by UUID.
 */
export async function handleGetJournal(uuid: string): Promise<GetResult> {
  try {
    const journal = await fromUuid(uuid);

    if (!journal) {
      console.error('[Tablewrite] Journal not found:', uuid);
      return {
        success: false,
        error: `Journal not found: ${uuid}`
      };
    }

    // Convert to plain object for transmission
    const journalData = journal.toObject();
    console.log('[Tablewrite] Fetched journal:', journalData.name, uuid);

    return {
      success: true,
      entity: journalData as Record<string, unknown>
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to get journal:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}

export async function handleJournalCreate(data: Record<string, unknown>): Promise<CreateResult> {
  try {
    // Extract the journal data from the message
    const journalData = data.journal as Record<string, unknown>;
    if (!journalData) {
      console.error('[Tablewrite] No journal data in message:', data);
      ui.notifications?.error('Failed to create journal: No journal data received');
      return {
        success: false,
        error: 'No journal data in message'
      };
    }

    const journal = await JournalEntry.create(journalData);
    if (journal) {
      const message = game.i18n.format('TABLEWRITE_ASSISTANT.CreatedJournal', { name: journal.name });
      ui.notifications?.info(message);
      console.log('[Tablewrite] Created journal:', journal.name, journal.id);

      return {
        success: true,
        id: journal.id,
        uuid: `JournalEntry.${journal.id}`,
        name: journal.name ?? undefined
      };
    }

    return {
      success: false,
      error: 'JournalEntry.create returned null'
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to create journal:', error);
    ui.notifications?.error(`Failed to create journal: ${error}`);
    return {
      success: false,
      error: String(error)
    };
  }
}

export async function handleJournalDelete(uuid: string): Promise<DeleteResult> {
  try {
    const journal = await fromUuid(uuid);
    if (!journal) {
      return { success: false, error: `Journal not found: ${uuid}` };
    }

    const name = (journal as { name?: string }).name;
    await journal.delete();

    const message = game.i18n.format('TABLEWRITE_ASSISTANT.DeletedJournal', { name });
    ui.notifications?.info(message);
    console.log('[Tablewrite] Deleted journal:', name, uuid);

    return {
      success: true,
      uuid: uuid,
      name: name ?? undefined
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to delete journal:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}

/**
 * List all world journals.
 */
export async function handleListJournals(): Promise<JournalListResult> {
  try {
    const journals = (game as any).journal;
    if (!journals) {
      return {
        success: false,
        error: 'No journals collection available'
      };
    }

    const journalList = journals.map((journal: FoundryDocument) => {
      const journalData = journal as unknown as { folder: { _id: string } | string | null };
      let folderId: string | null = null;
      if (journalData.folder) {
        if (typeof journalData.folder === 'string') {
          folderId = journalData.folder;
        } else if (journalData.folder._id) {
          folderId = journalData.folder._id;
        }
      }
      return {
        uuid: `JournalEntry.${journal.id}`,
        id: journal.id as string,
        name: journal.name as string,
        folder: folderId
      };
    });

    console.log('[Tablewrite] Listed', journalList.length, 'world journals');

    return {
      success: true,
      journals: journalList
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to list journals:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}

/**
 * Update a journal's properties.
 */
export async function handleUpdateJournal(data: {
  uuid: string;
  updates: Record<string, unknown>;
}): Promise<UpdateJournalResult> {
  try {
    const { uuid, updates } = data;

    const journal = await fromUuid(uuid);
    if (!journal) {
      return {
        success: false,
        error: `Journal not found: ${uuid}`
      };
    }

    await (journal as any).update(updates);

    console.log('[Tablewrite] Updated journal:', (journal as any).name, uuid);

    return {
      success: true,
      uuid: uuid,
      id: (journal as any).id,
      name: (journal as any).name
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to update journal:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}
