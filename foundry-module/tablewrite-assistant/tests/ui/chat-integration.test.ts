import { describe, it, expect, beforeAll } from 'vitest';

/**
 * Integration test - requires backend running at localhost:8000
 *
 * Run with: npm test -- tests/ui/chat-integration.test.ts
 *
 * Prerequisites:
 * 1. Start backend: cd ui/backend && uvicorn app.main:app --reload --port 8000
 */
describe('Chat Integration', () => {
  const BACKEND_URL = 'http://localhost:8000';

  // Check if backend is available
  let backendAvailable = false;

  beforeAll(async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/health`);
      backendAvailable = response.ok;
    } catch {
      backendAvailable = false;
    }
  });

  it('can send message to /api/chat and receive response', async () => {
    if (!backendAvailable) {
      console.warn('Backend not available - skipping integration test');
      return;
    }

    const response = await fetch(`${BACKEND_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: '/help',
        context: {},
        conversation_history: []
      })
    });

    expect(response.ok).toBe(true);

    const data = await response.json();
    expect(data.message).toBeTruthy();
    expect(data.type).toBe('text');
    expect(data.message).toContain('Available Commands');
  });

  it('handles conversation history correctly', async () => {
    if (!backendAvailable) {
      console.warn('Backend not available - skipping integration test');
      return;
    }

    const response = await fetch(`${BACKEND_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: 'What did I just ask?',
        context: {},
        conversation_history: [
          { role: 'user', content: 'What is a goblin?', timestamp: new Date().toISOString() },
          { role: 'assistant', content: 'A goblin is a small humanoid creature...', timestamp: new Date().toISOString() }
        ]
      })
    });

    expect(response.ok).toBe(true);

    const data = await response.json();
    expect(data.message).toBeTruthy();
    // Response should reference the previous question about goblins
    // (exact content depends on Gemini but it should acknowledge context)
  });
});
