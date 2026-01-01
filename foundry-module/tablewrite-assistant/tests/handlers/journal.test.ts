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

  it('calls JournalEntry.create with the journal data from message', async () => {
    const { handleJournalCreate } = await import('../../src/handlers/journal');
    const journalData = { name: 'Chapter 1', pages: [{ name: 'Page 1', type: 'text', text: { content: 'Hello' } }] };
    // New message format wraps journal data
    const message = { journal: journalData, name: 'Chapter 1' };

    const result = await handleJournalCreate(message);

    expect(mockJournalEntry.create).toHaveBeenCalledWith(journalData);
    expect(result.success).toBe(true);
  });

  it('returns success result with uuid on success', async () => {
    mockJournalEntry.create.mockResolvedValue({ id: 'journal456', name: 'Chapter 1' });
    const { handleJournalCreate } = await import('../../src/handlers/journal');

    const result = await handleJournalCreate({ journal: { name: 'Chapter 1' }, name: 'Chapter 1' });

    expect(result.success).toBe(true);
    expect(result.uuid).toBe('JournalEntry.journal456');
    expect(result.id).toBe('journal456');
    expect(result.name).toBe('Chapter 1');
  });

  it('shows notification on success', async () => {
    const { handleJournalCreate } = await import('../../src/handlers/journal');

    await handleJournalCreate({ journal: { name: 'Chapter 1' }, name: 'Chapter 1' });

    expect(mockNotifications.info).toHaveBeenCalled();
  });

  it('shows notification with created journal name', async () => {
    mockJournalEntry.create.mockResolvedValue({ id: 'journal123', name: 'Chapter 1' });
    const { handleJournalCreate } = await import('../../src/handlers/journal');

    await handleJournalCreate({ journal: { name: 'Chapter 1' }, name: 'Chapter 1' });

    expect(mockI18n.format).toHaveBeenCalledWith(
      'TABLEWRITE_ASSISTANT.CreatedJournal',
      { name: 'Chapter 1' }
    );
  });

  it('returns error result when create fails', async () => {
    mockJournalEntry.create.mockRejectedValue(new Error('Permission denied'));
    const { handleJournalCreate } = await import('../../src/handlers/journal');

    const result = await handleJournalCreate({ journal: { name: 'Chapter 1' }, name: 'Chapter 1' });

    expect(result.success).toBe(false);
    expect(result.error).toContain('Permission denied');
    expect(mockNotifications.error).toHaveBeenCalled();
  });

  it('returns error when no journal data in message', async () => {
    const { handleJournalCreate } = await import('../../src/handlers/journal');

    const result = await handleJournalCreate({ name: 'Chapter 1' }); // Missing 'journal' property

    expect(result.success).toBe(false);
    expect(result.error).toBe('No journal data in message');
    expect(mockNotifications.error).toHaveBeenCalled();
    expect(mockJournalEntry.create).not.toHaveBeenCalled();
  });
});
