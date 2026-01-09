/**
 * Tablewrite sidebar tab - chat UI for AI assistant.
 */

import { chatService, ChatMessage, ChatResponse } from './chat-service.js';
import { BattleMapUpload } from './BattleMapUpload.js';
import { ModuleUpload } from './ModuleUpload.js';
import { getBackendUrl, isTokenArtEnabled, setTokenArtEnabled, getArtStyle, setArtStyle } from '../settings.js';

// Foundry global declarations
declare const ImagePopout: new (src: string, options?: { title?: string }) => { render(force?: boolean): void };

export class TablewriteTab {
  private container: HTMLElement;
  private messages: ChatMessage[] = [];
  private isLoading: boolean = false;
  private battleMapUpload: BattleMapUpload | null = null;
  private moduleUpload: ModuleUpload | null = null;
  private settingsOpen: boolean = false;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  render(): void {
    this.container.innerHTML = `
      <div class="tablewrite-container">
        <div class="tablewrite-tabs">
          <button class="tab-btn active" data-tab="chat">Chat</button>
          <button class="tab-btn" data-tab="battlemap">Battle Map</button>
          <button class="tab-btn" data-tab="module">Module</button>
          <button class="settings-btn" title="${game.i18n.localize('TABLEWRITE_ASSISTANT.Settings')}">
            <i class="fas fa-cog"></i>
          </button>
        </div>

        <div class="tablewrite-settings-panel" style="display: none;">
          <div class="settings-row">
            <label>
              <input type="checkbox" id="token-art-toggle" ${isTokenArtEnabled() ? 'checked' : ''} />
              ${game.i18n.localize('TABLEWRITE_ASSISTANT.SettingsTokenArtEnabled')}
            </label>
          </div>
          <div class="settings-row">
            <label for="art-style-select">${game.i18n.localize('TABLEWRITE_ASSISTANT.SettingsArtStyle')}</label>
            <select id="art-style-select">
              <option value="watercolor" ${getArtStyle() === 'watercolor' ? 'selected' : ''}>
                ${game.i18n.localize('TABLEWRITE_ASSISTANT.StyleWatercolor')}
              </option>
              <option value="oil" ${getArtStyle() === 'oil' ? 'selected' : ''}>
                ${game.i18n.localize('TABLEWRITE_ASSISTANT.StyleOil')}
              </option>
            </select>
          </div>
        </div>

        <div class="tab-content" id="chat-tab">
          <div class="tablewrite-chat">
            <div class="tablewrite-messages"></div>
            <form class="tablewrite-input-form">
              <textarea
                class="tablewrite-input"
                placeholder="${game.i18n.localize('TABLEWRITE_ASSISTANT.Placeholder')}"
              ></textarea>
            </form>
          </div>
        </div>

        <div class="tab-content" id="battlemap-tab" style="display: none">
          <!-- BattleMapUpload renders here -->
        </div>

        <div class="tab-content" id="module-tab" style="display: none">
          <!-- ModuleUpload renders here -->
        </div>
      </div>
    `;

    // Initialize BattleMapUpload
    const battlemapContainer = this.container.querySelector('#battlemap-tab') as HTMLElement;
    this.battleMapUpload = new BattleMapUpload(battlemapContainer, getBackendUrl());
    this.battleMapUpload.render();

    // Initialize ModuleUpload
    const moduleContainer = this.container.querySelector('#module-tab') as HTMLElement;
    this.moduleUpload = new ModuleUpload(moduleContainer, getBackendUrl());
    this.moduleUpload.render();

    // Attach tab switching listeners
    this.attachTabListeners();

    // Existing chat setup
    this.activateListeners();

    // Attach settings panel listeners
    this.attachSettingsListeners();
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

  private attachTabListeners(): void {
    const tabBtns = this.container.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const tabId = (btn as HTMLElement).dataset.tab;

        // Update active tab button
        tabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Show/hide tab content (use 'flex' not 'block' to preserve flexbox layout)
        this.container.querySelectorAll('.tab-content').forEach(c => {
          (c as HTMLElement).style.display = c.id === `${tabId}-tab` ? 'flex' : 'none';
        });

        // When switching to chat tab, scroll messages to bottom
        if (tabId === 'chat') {
          const messagesContainer = this.container.querySelector('.tablewrite-messages');
          if (messagesContainer) {
            this.scrollToBottom(messagesContainer);
          }
        }
      });
    });
  }

  private attachSettingsListeners(): void {
    const settingsBtn = this.container.querySelector('.settings-btn');
    const settingsPanel = this.container.querySelector('.tablewrite-settings-panel') as HTMLElement;
    const tokenArtToggle = this.container.querySelector('#token-art-toggle') as HTMLInputElement;
    const artStyleSelect = this.container.querySelector('#art-style-select') as HTMLSelectElement;

    // Toggle settings panel
    settingsBtn?.addEventListener('click', () => {
      this.settingsOpen = !this.settingsOpen;
      settingsPanel.style.display = this.settingsOpen ? 'block' : 'none';
      settingsBtn.classList.toggle('active', this.settingsOpen);
    });

    // Handle token art toggle
    tokenArtToggle?.addEventListener('change', async () => {
      await setTokenArtEnabled(tokenArtToggle.checked);
      // Disable style select when art is disabled
      artStyleSelect.disabled = !tokenArtToggle.checked;
    });

    // Handle art style change
    artStyleSelect?.addEventListener('change', async () => {
      await setArtStyle(artStyleSelect.value);
    });

    // Set initial disabled state
    if (artStyleSelect && tokenArtToggle) {
      artStyleSelect.disabled = !tokenArtToggle.checked;
    }
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
      const response: ChatResponse = await chatService.send(content, historyBeforeSend);

      // Handle image responses
      const imageUrls = response.type === 'image' && response.data?.image_urls
        ? response.data.image_urls
        : undefined;

      this.messages.push({
        role: 'assistant',
        content: response.message,
        timestamp: new Date(),
        type: response.type,
        imageUrls
      });
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

    container.innerHTML = this.messages.map(msg => {
      let imagesHtml = '';
      if (msg.imageUrls && msg.imageUrls.length > 0) {
        const backendUrl = getBackendUrl();
        imagesHtml = `
          <div class="tablewrite-images">
            ${msg.imageUrls.map(url => {
              // Convert relative URL to absolute
              const fullUrl = url.startsWith('/') ? `${backendUrl}${url}` : url;
              return `<img src="${fullUrl}" alt="Generated image" class="tablewrite-generated-image" data-src="${fullUrl}" />`;
            }).join('')}
          </div>
        `;
      }

      return `
        <div class="tablewrite-message tablewrite-message--${msg.role}">
          <div class="tablewrite-message-content">${this.formatContent(msg.content)}</div>
          ${imagesHtml}
        </div>
      `;
    }).join('');

    // Add click handlers for image popout
    this.attachImageClickHandlers(container);

    // Add click handlers for content links (actor/item links)
    this.attachContentLinkHandlers(container);

    // Scroll to bottom after DOM update
    this.scrollToBottom(container);

    // Also scroll when images finish loading (they change container height)
    const images = container.querySelectorAll('.tablewrite-generated-image');
    images.forEach(img => {
      img.addEventListener('load', () => this.scrollToBottom(container));
    });
  }

  private scrollToBottom(container: Element): void {
    // Use requestAnimationFrame to ensure DOM has updated
    requestAnimationFrame(() => {
      container.scrollTop = container.scrollHeight;
    });
  }

  private attachImageClickHandlers(container: Element): void {
    const images = container.querySelectorAll('.tablewrite-generated-image');
    images.forEach(img => {
      img.addEventListener('click', (e) => {
        const target = e.target as HTMLImageElement;
        const src = target.dataset.src || target.src;
        // Use Foundry's ImagePopout to display the image
        new ImagePopout(src, { title: 'Generated Image' }).render(true);
      });
    });
  }

  private attachContentLinkHandlers(container: Element): void {
    const links = container.querySelectorAll('.content-link[data-uuid]');
    links.forEach(link => {
      link.addEventListener('click', async () => {
        const uuid = (link as HTMLElement).dataset.uuid;
        if (!uuid) return;

        try {
          // Use Foundry's fromUuid to get the document and open its sheet
          const doc = await fromUuid(uuid);
          if (doc && 'sheet' in doc) {
            (doc as any).sheet.render(true);
          } else {
            ui.notifications?.warn(`Could not find document: ${uuid}`);
          }
        } catch (error) {
          console.error('[Tablewrite] Failed to open document:', error);
          ui.notifications?.error(`Failed to open: ${uuid}`);
        }
      });
    });
  }

  private formatContent(content: string): string {
    // First escape HTML entities to prevent XSS
    const escaped = content
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');

    // Then apply markdown transformations: **bold**, *italic*, `code`
    let formatted = escaped
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');

    // Convert @UUID[Type.id]{Label} to clickable spans (not <a> to avoid navigation)
    // Match pattern: @UUID[Actor.xxx]{Name} or @UUID[Item.xxx]{Name} etc.
    formatted = formatted.replace(
      /@UUID\[([^\]]+)\]\{([^}]+)\}/g,
      '<span class="content-link" data-uuid="$1" data-tooltip="Click to open">$2</span>'
    );

    // Apply code formatting for non-UUID code blocks
    formatted = formatted.replace(/`(.*?)`/g, '<code>$1</code>');

    return formatted;
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
