/**
 * Handle journal creation messages from backend.
 */

export async function handleJournalCreate(data: Record<string, unknown>): Promise<void> {
  try {
    const journal = await JournalEntry.create(data);
    if (journal) {
      const message = game.i18n.format('TABLEWRITE_ASSISTANT.CreatedJournal', { name: journal.name });
      ui.notifications?.info(message);
    }
  } catch (error) {
    console.error('[Tablewrite] Failed to create journal:', error);
    ui.notifications?.error(`Failed to create journal: ${error}`);
  }
}
