/**
 * Tablewrite sidebar tab - chat UI for AI assistant.
 */

import { chatService, ChatMessage } from './chat-service.js';

export class TablewriteTab {
  private container: HTMLElement;
  private messages: ChatMessage[] = [];
  private isLoading: boolean = false;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  render(): void {
    this.container.innerHTML = `
      <div class="tablewrite-chat">
        <div class="tablewrite-messages"></div>
        <form class="tablewrite-input-form">
          <textarea
            class="tablewrite-input"
            placeholder="${game.i18n.localize('TABLEWRITE_ASSISTANT.Placeholder')}"
          ></textarea>
        </form>
      </div>
    `;
    this.activateListeners();
  }

  private activateListeners(): void {
    const form = this.container.querySelector('.tablewrite-input-form');
    const input = this.container.querySelector('.tablewrite-input') as HTMLTextAreaElement;

    form?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.sendMessage(input.value);
      input.value = '';
    });

    // Enter to send, Shift+Enter for new line
    input?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        form?.dispatchEvent(new Event('submit'));
      }
    });

    // Drag and drop support for future file uploads
    input?.addEventListener('dragover', (e) => {
      e.preventDefault();
      input.classList.add('dragover');
    });

    input?.addEventListener('dragleave', () => {
      input.classList.remove('dragover');
    });

    input?.addEventListener('drop', (e) => {
      e.preventDefault();
      input.classList.remove('dragover');
      const files = e.dataTransfer?.files;
      if (files && files.length > 0) {
        // TODO: Handle file upload
        ui.notifications?.info(`File upload coming soon: ${files[0].name}`);
      }
    });
  }

  async sendMessage(content: string): Promise<void> {
    if (!content.trim() || this.isLoading) return;

    // Capture history before adding current message (API contract requirement)
    const historyBeforeSend = [...this.messages];

    // Add user message and render immediately for responsive UI
    this.messages.push({ role: 'user', content, timestamp: new Date() });
    this.renderMessages();

    // Send to backend with prior history (excludes current message)
    this.isLoading = true;
    this.updateLoadingState();

    try {
      const response = await chatService.send(content, historyBeforeSend);
      this.messages.push({ role: 'assistant', content: response, timestamp: new Date() });
    } catch (error) {
      ui.notifications?.error(game.i18n.localize('TABLEWRITE_ASSISTANT.ChatError'));
      this.messages.push({
        role: 'assistant',
        content: '**Error:** Could not reach backend. Is the server running?',
        timestamp: new Date()
      });
    }

    this.isLoading = false;
    this.renderMessages();
    this.updateLoadingState();
  }

  private renderMessages(): void {
    const container = this.container.querySelector('.tablewrite-messages');
    if (!container) return;

    container.innerHTML = this.messages.map(msg => `
      <div class="tablewrite-message tablewrite-message--${msg.role}">
        <div class="tablewrite-message-content">${this.formatContent(msg.content)}</div>
      </div>
    `).join('');

    container.scrollTop = container.scrollHeight;
  }

  private formatContent(content: string): string {
    // First escape HTML entities to prevent XSS
    const escaped = content
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');

    // Then apply markdown transformations: **bold**, *italic*, `code`
    return escaped
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br>');
  }

  private updateLoadingState(): void {
    const input = this.container.querySelector('.tablewrite-input') as HTMLTextAreaElement;
    if (input) {
      input.disabled = this.isLoading;
      input.placeholder = this.isLoading
        ? game.i18n.localize('TABLEWRITE_ASSISTANT.Loading')
        : game.i18n.localize('TABLEWRITE_ASSISTANT.Placeholder');
    }
  }
}
