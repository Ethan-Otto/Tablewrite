// foundry-module/tablewrite-assistant/tests/handlers/journal.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock Foundry JournalEntry class
const mockJournalEntry = {
  create: vi.fn().mockResolvedValue({ id: 'journal123', name: 'Test Journal' }),
};

// @ts-ignore
globalThis.JournalEntry = mockJournalEntry;

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
    // Reset the mock return value to default
    mockJournalEntry.create.mockResolvedValue({ id: 'journal123', name: 'Test Journal' });
  });

  it('calls JournalEntry.create with the data', async () => {
    const { handleJournalCreate } = await import('../../src/handlers/journal');
    const journalData = { name: 'Chapter 1', pages: [{ name: 'Page 1', type: 'text', text: { content: 'Hello' } }] };

    await handleJournalCreate(journalData);

    expect(mockJournalEntry.create).toHaveBeenCalledWith(journalData);
  });

  it('shows notification on success', async () => {
    const { handleJournalCreate } = await import('../../src/handlers/journal');

    await handleJournalCreate({ name: 'Chapter 1', uuid: 'JournalEntry.abc123' });

    expect(mockNotifications.info).toHaveBeenCalled();
  });

  it('shows notification with created journal name', async () => {
    mockJournalEntry.create.mockResolvedValue({ id: 'journal123', name: 'Chapter 1' });
    const { handleJournalCreate } = await import('../../src/handlers/journal');

    await handleJournalCreate({ name: 'Chapter 1', uuid: 'JournalEntry.abc123' });

    expect(mockI18n.format).toHaveBeenCalledWith(
      'TABLEWRITE_ASSISTANT.CreatedJournal',
      { name: 'Chapter 1' }
    );
  });

  it('shows error notification when create fails', async () => {
    mockJournalEntry.create.mockRejectedValue(new Error('Permission denied'));
    const { handleJournalCreate } = await import('../../src/handlers/journal');

    await handleJournalCreate({ name: 'Chapter 1' });

    expect(mockNotifications.error).toHaveBeenCalled();
  });

  it('does not show success notification when create returns null', async () => {
    mockJournalEntry.create.mockResolvedValue(null);
    const { handleJournalCreate } = await import('../../src/handlers/journal');

    await handleJournalCreate({ name: 'Chapter 1' });

    expect(mockNotifications.info).not.toHaveBeenCalled();
  });
});
