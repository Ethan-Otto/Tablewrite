/**
 * Handle journal creation messages from backend.
 *
 * Message format: {journal: {...}, name: string}
 */

import type { CreateResult } from './index.js';

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
