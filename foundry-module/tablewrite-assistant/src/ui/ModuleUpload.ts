/**
 * Module Upload component for importing D&D PDFs into FoundryVTT.
 * Handles PDF upload, processing options, progress display, and result presentation.
 */
interface ProgressEvent {
  stage: string;
  message: string;
  progress?: number;
  module_name?: string;
}

export class ModuleUpload {
  private container: HTMLElement;
  private backendUrl: string;
  private progressHookId: number | null = null;
  private isProcessing: boolean = false;

  constructor(container: HTMLElement, backendUrl: string) {
    this.container = container;
    this.backendUrl = backendUrl;
  }

  /**
   * Safely query a DOM element within the container.
   */
  private getElement<T extends HTMLElement>(selector: string): T | null {
    return this.container.querySelector(selector) as T | null;
  }

  render(): void {
    this.container.innerHTML = `
      <div class="module-upload">
        <h3>Import D&D Module</h3>

        <div class="upload-form">
          <div class="form-group">
            <label>Module PDF</label>
            <div class="file-drop-zone" id="module-drop-zone">
              <p>Drag & drop PDF here or click to browse</p>
              <input type="file" id="module-file" accept=".pdf" />
            </div>
            <div class="file-name-display" id="file-name-display"></div>
          </div>

          <div class="form-group">
            <label>Module Name</label>
            <input type="text" id="module-name" placeholder="Auto-derived from filename" />
          </div>

          <div class="form-group">
            <label>Processing Options</label>
            <div class="checkbox-list">
              <div class="checkbox-item">
                <label>
                  <input type="checkbox" id="opt-journal" checked />
                  Extract Journal
                </label>
              </div>
              <div class="checkbox-item">
                <label>
                  <input type="checkbox" id="opt-actors" checked />
                  Extract Actors
                </label>
              </div>
              <div class="checkbox-item">
                <label>
                  <input type="checkbox" id="opt-maps" checked />
                  Extract Battle Maps
                </label>
              </div>
              <div class="checkbox-item">
                <label>
                  <input type="checkbox" id="opt-artwork" checked />
                  Generate Scene Artwork
                </label>
              </div>
            </div>
          </div>

          <div class="button-group">
            <button id="import-module-btn" class="primary" disabled>Import Module</button>
            <button id="cancel-btn" class="secondary" style="display: none">Cancel</button>
          </div>
        </div>

        <div class="progress-container" style="display: none">
          <div class="progress-bar">
            <div class="progress-fill" id="progress-fill"></div>
          </div>
          <div class="progress-status" id="progress-status">Preparing...</div>
        </div>

        <div class="result-container" style="display: none">
          <div class="result-summary" id="result-summary"></div>
          <div class="result-details" id="result-details"></div>
          <button id="import-another-btn" class="primary">Import Another Module</button>
        </div>
      </div>
    `;

    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    const fileInput = this.container.querySelector('#module-file') as HTMLInputElement;
    const dropZone = this.container.querySelector('#module-drop-zone') as HTMLElement;
    const importBtn = this.container.querySelector('#import-module-btn') as HTMLButtonElement;
    const cancelBtn = this.container.querySelector('#cancel-btn') as HTMLButtonElement;
    const importAnotherBtn = this.container.querySelector('#import-another-btn') as HTMLButtonElement;

    // File input change
    fileInput?.addEventListener('change', () => this.handleFileSelect(fileInput));

    // Drag and drop events
    dropZone?.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add('dragover');
    });

    dropZone?.addEventListener('dragleave', (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove('dragover');
    });

    dropZone?.addEventListener('drop', (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove('dragover');
      const files = e.dataTransfer?.files;
      if (files && files.length > 0) {
        const file = files[0];
        if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
          // Set file to input programmatically
          const dt = new DataTransfer();
          dt.items.add(file);
          fileInput.files = dt.files;
          this.handleFileSelect(fileInput);
        } else {
          (globalThis as any).ui?.notifications?.error('Please select a PDF file');
        }
      }
    });

    // Click on drop zone triggers file input
    dropZone?.addEventListener('click', () => fileInput.click());

    // Button handlers
    importBtn?.addEventListener('click', () => this.handleImport());
    cancelBtn?.addEventListener('click', () => this.resetForm());
    importAnotherBtn?.addEventListener('click', () => this.resetForm());
  }

  private handleFileSelect(fileInput: HTMLInputElement): void {
    const file = fileInput.files?.[0];
    const fileNameDisplay = this.getElement<HTMLElement>('#file-name-display');
    const importBtn = this.getElement<HTMLButtonElement>('#import-module-btn');
    const moduleNameInput = this.getElement<HTMLInputElement>('#module-name');

    if (file) {
      // Show filename
      if (fileNameDisplay) {
        fileNameDisplay.textContent = file.name;
        fileNameDisplay.style.display = 'block';
      }

      // Auto-populate module name from filename (without extension)
      const nameWithoutExt = file.name.replace(/\.pdf$/i, '').replace(/_/g, ' ');
      if (moduleNameInput && !moduleNameInput.value) {
        moduleNameInput.value = nameWithoutExt;
      }

      // Enable import button
      if (importBtn) {
        importBtn.disabled = false;
      }
    } else {
      if (fileNameDisplay) {
        fileNameDisplay.textContent = '';
        fileNameDisplay.style.display = 'none';
      }
      if (importBtn) {
        importBtn.disabled = true;
      }
    }
  }

  private async handleImport(): Promise<void> {
    const fileInput = this.getElement<HTMLInputElement>('#module-file');
    const file = fileInput?.files?.[0];

    if (!file) {
      (globalThis as any).ui?.notifications?.error('Please select a PDF file');
      return;
    }

    const moduleNameInput = this.getElement<HTMLInputElement>('#module-name');
    const extractJournal = this.getElement<HTMLInputElement>('#opt-journal')?.checked ?? true;
    const extractActors = this.getElement<HTMLInputElement>('#opt-actors')?.checked ?? true;
    const extractMaps = this.getElement<HTMLInputElement>('#opt-maps')?.checked ?? true;
    const generateArtwork = this.getElement<HTMLInputElement>('#opt-artwork')?.checked ?? true;

    // Build FormData - field names must match backend FastAPI Form() parameters
    const formData = new FormData();
    formData.append('file', file);
    if (moduleNameInput?.value) {
      formData.append('module_name', moduleNameInput.value);
    }
    formData.append('extract_journal', extractJournal.toString());
    formData.append('extract_actors', extractActors.toString());
    formData.append('extract_battle_maps', extractMaps.toString());
    formData.append('generate_scene_artwork', generateArtwork.toString());

    this.showProgress('Uploading PDF...');
    this.startProgressListener();

    try {
      const response = await fetch(`${this.backendUrl}/api/modules/process`, {
        method: 'POST',
        body: formData,
      });

      // Stop progress immediately after response received
      this.stopProgressListener();

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      // Parse JSON with error handling
      let result;
      try {
        result = await response.json();
      } catch (parseError) {
        (globalThis as any).ui?.notifications?.error('Invalid response from server');
        this.hideProgress();
        return;
      }

      if (result.success) {
        this.showSuccess(result);
      } else {
        // result.error can be a string or {stage: string, message: string}
        const errorMsg = typeof result.error === 'object'
          ? (result.error?.message || JSON.stringify(result.error))
          : (result.error || 'Unknown error during processing');
        throw new Error(errorMsg);
      }
    } catch (error: any) {
      this.stopProgressListener();
      const msg = error?.message || String(error) || 'Unknown error';
      (globalThis as any).ui?.notifications?.error(`Failed to import module: ${msg}`);
      this.hideProgress();
    }
  }

  private startProgressListener(): void {
    this.isProcessing = true;

    // Register hook to receive real-time progress updates from WebSocket
    // Cast to any for custom hook registration - Foundry's Hooks.on returns number
    this.progressHookId = (Hooks as any).on('tablewrite.moduleProgress', (event: ProgressEvent) => {
      if (!this.isProcessing) return;

      // Use progress from event if available, otherwise estimate based on stage
      const progress = event.progress ?? this.estimateProgressFromStage(event.stage);
      this.updateProgress(progress, event.message);
    });
  }

  private estimateProgressFromStage(stage: string): number {
    // Fallback progress estimates based on stage name
    const stageProgress: Record<string, number> = {
      'uploading': 5,
      'splitting_pdf': 10,
      'extracting_text': 20,
      'processing_journal': 35,
      'extracting_actors': 50,
      'extracting_maps': 65,
      'generating_artwork': 75,
      'uploading_to_foundry': 85,
      'finalizing': 95,
      'complete': 100,
    };
    return stageProgress[stage] ?? 50;
  }

  private showProgress(message: string): void {
    const progressContainer = this.container.querySelector('.progress-container') as HTMLElement;
    const formContainer = this.container.querySelector('.upload-form') as HTMLElement;

    formContainer.style.display = 'none';
    progressContainer.style.display = 'block';

    this.updateProgress(5, message);
  }

  private updateProgress(percent: number, message: string): void {
    const progressFill = this.container.querySelector('#progress-fill') as HTMLElement;
    const progressStatus = this.container.querySelector('#progress-status') as HTMLElement;

    if (progressFill) {
      progressFill.style.width = `${percent}%`;
    }
    if (progressStatus) {
      progressStatus.textContent = message;
    }
  }

  private hideProgress(): void {
    this.stopProgressListener();

    const progressContainer = this.container.querySelector('.progress-container') as HTMLElement;
    const formContainer = this.container.querySelector('.upload-form') as HTMLElement;

    progressContainer.style.display = 'none';
    formContainer.style.display = 'block';
  }

  private stopProgressListener(): void {
    this.isProcessing = false;

    if (this.progressHookId !== null) {
      // Cast to any for custom hook deregistration
      (Hooks as any).off('tablewrite.moduleProgress', this.progressHookId);
      this.progressHookId = null;
    }
  }

  private showSuccess(result: any): void {
    this.stopProgressListener();

    const progressContainer = this.container.querySelector('.progress-container') as HTMLElement;
    const resultContainer = this.container.querySelector('.result-container') as HTMLElement;
    const resultSummary = this.container.querySelector('#result-summary') as HTMLElement;
    const resultDetails = this.container.querySelector('#result-details') as HTMLElement;

    progressContainer.style.display = 'none';
    resultContainer.style.display = 'block';

    // Build summary
    const summaryParts: string[] = [];
    if (result.journal_uuid) {
      summaryParts.push(`Journal created`);
    }
    if (result.actors && result.actors.length > 0) {
      summaryParts.push(`${result.actors.length} actors`);
    }
    if (result.scenes && result.scenes.length > 0) {
      summaryParts.push(`${result.scenes.length} scenes`);
    }

    resultSummary.innerHTML = `
      <h4>Import Complete!</h4>
      <p><strong>${result.name || 'Module'}</strong></p>
      <p>Created: ${summaryParts.join(', ') || 'No content'}</p>
    `;

    // Build details with collapsible sections
    let detailsHtml = '';

    // Journal link
    if (result.journal_uuid) {
      detailsHtml += `
        <div class="result-section">
          <div class="result-item">
            <span class="content-link" data-uuid="${result.journal_uuid}" data-tooltip="Click to open">
              Journal: ${result.journal_name || 'Module Journal'}
            </span>
          </div>
        </div>
      `;
    }

    // Actors section (collapsible)
    if (result.actors && result.actors.length > 0) {
      detailsHtml += `
        <div class="result-section collapsible collapsed">
          <div class="result-section-header" data-toggle="actors">
            Actors (${result.actors.length})
            <span class="collapse-icon">+</span>
          </div>
          <div class="result-section-content" id="actors-content">
            ${result.actors.map((actor: any) => `
              <div class="result-item">
                <span class="content-link" data-uuid="${actor.uuid}" data-tooltip="Click to open">
                  ${actor.name}
                </span>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    // Scenes section (collapsible)
    if (result.scenes && result.scenes.length > 0) {
      detailsHtml += `
        <div class="result-section collapsible collapsed">
          <div class="result-section-header" data-toggle="scenes">
            Scenes (${result.scenes.length})
            <span class="collapse-icon">+</span>
          </div>
          <div class="result-section-content" id="scenes-content">
            ${result.scenes.map((scene: any) => `
              <div class="result-item">
                <span class="content-link" data-uuid="${scene.uuid}" data-tooltip="Click to open">
                  ${scene.name}
                </span>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    resultDetails.innerHTML = detailsHtml;

    // Attach event listeners for collapsible sections
    this.attachCollapsibleListeners();

    // Attach click handlers for UUID links
    this.attachUuidClickHandlers();

    // Show notification
    (globalThis as any).ui?.notifications?.info(
      `Module imported: ${result.name || 'Module'} - ${summaryParts.join(', ')}`
    );
  }

  private attachCollapsibleListeners(): void {
    const headers = this.container.querySelectorAll('.result-section-header');
    headers.forEach(header => {
      header.addEventListener('click', () => {
        const section = header.parentElement as HTMLElement;
        const icon = header.querySelector('.collapse-icon');

        if (section.classList.contains('collapsed')) {
          section.classList.remove('collapsed');
          section.classList.add('expanded');
          if (icon) icon.textContent = '-';
        } else {
          section.classList.remove('expanded');
          section.classList.add('collapsed');
          if (icon) icon.textContent = '+';
        }
      });
    });
  }

  private attachUuidClickHandlers(): void {
    const links = this.container.querySelectorAll('.content-link[data-uuid]');
    links.forEach(link => {
      link.addEventListener('click', async () => {
        const uuid = (link as HTMLElement).dataset.uuid;
        if (!uuid) return;

        try {
          // Use Foundry's fromUuidSync for synchronous lookup or fromUuid for async
          const doc = await (globalThis as any).fromUuid?.(uuid);
          if (doc && 'sheet' in doc) {
            (doc as any).sheet.render(true);
          } else {
            (globalThis as any).ui?.notifications?.warn(`Could not find document: ${uuid}`);
          }
        } catch (error) {
          console.error('[Tablewrite] Failed to open document:', error);
          (globalThis as any).ui?.notifications?.error(`Failed to open: ${uuid}`);
        }
      });
    });
  }

  private resetForm(): void {
    // Stop any running progress listener when cancelling/resetting
    this.stopProgressListener();

    const resultContainer = this.getElement<HTMLElement>('.result-container');
    const progressContainer = this.getElement<HTMLElement>('.progress-container');
    const formContainer = this.getElement<HTMLElement>('.upload-form');

    if (resultContainer) resultContainer.style.display = 'none';
    if (progressContainer) progressContainer.style.display = 'none';
    if (formContainer) formContainer.style.display = 'block';

    // Clear form inputs
    const fileInput = this.getElement<HTMLInputElement>('#module-file');
    const moduleNameInput = this.getElement<HTMLInputElement>('#module-name');
    const fileNameDisplay = this.getElement<HTMLElement>('#file-name-display');
    const importBtn = this.getElement<HTMLButtonElement>('#import-module-btn');

    if (fileInput) fileInput.value = '';
    if (moduleNameInput) moduleNameInput.value = '';
    if (fileNameDisplay) {
      fileNameDisplay.textContent = '';
      fileNameDisplay.style.display = 'none';
    }
    if (importBtn) importBtn.disabled = true;

    // Reset checkboxes to default (all checked)
    const optJournal = this.getElement<HTMLInputElement>('#opt-journal');
    const optActors = this.getElement<HTMLInputElement>('#opt-actors');
    const optMaps = this.getElement<HTMLInputElement>('#opt-maps');
    const optArtwork = this.getElement<HTMLInputElement>('#opt-artwork');

    if (optJournal) optJournal.checked = true;
    if (optActors) optActors.checked = true;
    if (optMaps) optMaps.checked = true;
    if (optArtwork) optArtwork.checked = true;
  }
}
