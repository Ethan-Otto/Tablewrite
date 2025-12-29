// foundry-module/tablewrite-assistant/tests/handlers/journal.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock ui.notifications
const mockNotifications = {
  info: vi.fn(),
  error: vi.fn(),
};

// @ts-ignore
globalThis.ui = { notifications: mockNotifications };

// Mock game.i18n
const mockI18n = {
  format: vi.fn((key: string, data: { name: string }) => `Created journal: ${data.name}`),
};

// @ts-ignore
globalThis.game = { i18n: mockI18n };

describe('handleJournalCreate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows notification on success', async () => {
    const { handleJournalCreate } = await import('../../src/handlers/journal');

    await handleJournalCreate({ name: 'Chapter 1', uuid: 'JournalEntry.abc123' });

    expect(mockNotifications.info).toHaveBeenCalled();
  });

  it('shows notification with journal name', async () => {
    const { handleJournalCreate } = await import('../../src/handlers/journal');

    await handleJournalCreate({ name: 'Chapter 1', uuid: 'JournalEntry.abc123' });

    expect(mockI18n.format).toHaveBeenCalledWith(
      'TABLEWRITE_ASSISTANT.CreatedJournal',
      { name: 'Chapter 1' }
    );
  });
});
