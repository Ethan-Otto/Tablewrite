/**
 * Handle journal creation messages from backend.
 */

export async function handleJournalCreate(data: Record<string, unknown>): Promise<void> {
  try {
    const name = data.name as string;

    if (name) {
      const message = game.i18n.format('TABLEWRITE_ASSISTANT.CreatedJournal', { name });
      ui.notifications?.info(message);
    }
  } catch (error) {
    console.error('[Tablewrite] Failed to handle journal create:', error);
    ui.notifications?.error(`Failed to create journal: ${error}`);
  }
}
