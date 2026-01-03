/**
 * Battle Map Upload component for creating FoundryVTT scenes from images.
 */
export class BattleMapUpload {
  private container: HTMLElement;
  private backendUrl: string;
  private progressInterval: ReturnType<typeof setInterval> | null = null;

  constructor(container: HTMLElement, backendUrl: string) {
    this.container = container;
    this.backendUrl = backendUrl;
  }

  render(): void {
    this.container.innerHTML = `
      <div class="battlemap-upload">
        <h3>Create Scene from Battle Map</h3>

        <div class="upload-form">
          <div class="form-group">
            <label>Battle Map Image</label>
            <input type="file" id="battlemap-file" accept="image/*" />
          </div>

          <div class="form-group">
            <label>Scene Name (optional)</label>
            <input type="text" id="scene-name" placeholder="Auto-derived from filename" />
          </div>

          <div class="form-group">
            <label>Grid Size</label>
            <select id="grid-size-mode">
              <option value="auto">Auto-detect</option>
              <option value="manual">Manual</option>
            </select>
            <input type="number" id="grid-size" placeholder="100" style="display: none" />
          </div>

          <div class="form-group">
            <label>
              <input type="checkbox" id="skip-walls" />
              Skip wall detection
            </label>
          </div>

          <button id="create-scene-btn" class="primary">Create Scene</button>
        </div>

        <div class="progress-container" style="display: none">
          <div class="progress-bar">
            <div class="progress-fill"></div>
          </div>
          <div class="progress-status">Preparing...</div>
        </div>

        <div class="result-container" style="display: none">
          <div class="success-message"></div>
          <button id="open-scene-btn">Open Scene</button>
          <button id="reset-btn">Create Another</button>
        </div>
      </div>
    `;

    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    const gridModeSelect = this.container.querySelector('#grid-size-mode');
    const createBtn = this.container.querySelector('#create-scene-btn');
    const resetBtn = this.container.querySelector('#reset-btn');

    gridModeSelect?.addEventListener('change', (e) => {
      const target = e.target as HTMLSelectElement;
      const gridSizeInput = this.container.querySelector('#grid-size') as HTMLInputElement;
      gridSizeInput.style.display = target.value === 'manual' ? 'block' : 'none';
    });

    createBtn?.addEventListener('click', () => this.handleCreateScene());
    resetBtn?.addEventListener('click', () => this.resetForm());
  }

  private async handleCreateScene(): Promise<void> {
    const fileInput = this.container.querySelector('#battlemap-file') as HTMLInputElement;
    const file = fileInput.files?.[0];

    if (!file) {
      (globalThis as any).ui?.notifications?.error('Please select a battle map image');
      return;
    }

    this.showProgress('Uploading image...');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const nameInput = this.container.querySelector('#scene-name') as HTMLInputElement;
      if (nameInput.value) {
        formData.append('name', nameInput.value);
      }

      const skipWalls = (this.container.querySelector('#skip-walls') as HTMLInputElement).checked;
      formData.append('skip_walls', skipWalls.toString());

      const gridMode = (this.container.querySelector('#grid-size-mode') as HTMLSelectElement).value;
      if (gridMode === 'manual') {
        const gridSize = (this.container.querySelector('#grid-size') as HTMLInputElement).value;
        if (gridSize) {
          formData.append('grid_size', gridSize);
        }
      }

      this.simulateProgress();

      const response = await fetch(`${this.backendUrl}/api/scenes/create-from-map`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      const result = await response.json();

      if (result.success) {
        this.showSuccess(result);
      } else {
        throw new Error(result.error || 'Unknown error');
      }
    } catch (error: any) {
      (globalThis as any).ui?.notifications?.error(`Failed to create scene: ${error.message}`);
      this.hideProgress();
    }
  }

  private simulateProgress(): void {
    const stages = [
      { pct: 10, msg: 'Saving image...' },
      { pct: 20, msg: 'Detecting walls (this may take a minute)...' },
      { pct: 60, msg: 'Processing wall geometry...' },
      { pct: 75, msg: 'Detecting grid...' },
      { pct: 85, msg: 'Uploading to Foundry...' },
      { pct: 95, msg: 'Creating scene...' },
    ];

    let i = 0;
    this.progressInterval = setInterval(() => {
      if (i < stages.length) {
        this.updateProgress(stages[i].pct, stages[i].msg);
        i++;
      }
    }, 8000);
  }

  private showProgress(message: string): void {
    const progressContainer = this.container.querySelector('.progress-container') as HTMLElement;
    const formContainer = this.container.querySelector('.upload-form') as HTMLElement;

    formContainer.style.display = 'none';
    progressContainer.style.display = 'block';

    this.updateProgress(5, message);
  }

  private updateProgress(percent: number, message: string): void {
    const progressFill = this.container.querySelector('.progress-fill') as HTMLElement;
    const progressStatus = this.container.querySelector('.progress-status') as HTMLElement;

    progressFill.style.width = `${percent}%`;
    progressStatus.textContent = message;
  }

  private hideProgress(): void {
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
      this.progressInterval = null;
    }

    const progressContainer = this.container.querySelector('.progress-container') as HTMLElement;
    const formContainer = this.container.querySelector('.upload-form') as HTMLElement;

    progressContainer.style.display = 'none';
    formContainer.style.display = 'block';
  }

  private showSuccess(result: any): void {
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
      this.progressInterval = null;
    }

    const progressContainer = this.container.querySelector('.progress-container') as HTMLElement;
    const resultContainer = this.container.querySelector('.result-container') as HTMLElement;
    const successMessage = this.container.querySelector('.success-message') as HTMLElement;

    progressContainer.style.display = 'none';
    resultContainer.style.display = 'block';

    successMessage.innerHTML = `
      <p><strong>Scene created!</strong></p>
      <p>Name: ${result.name}</p>
      <p>Walls: ${result.wall_count}</p>
      <p>Grid: ${result.grid_size || 'None detected'}px</p>
    `;

    const openBtn = this.container.querySelector('#open-scene-btn');
    openBtn?.addEventListener('click', async () => {
      const scene = await (globalThis as any).fromUuid?.(result.uuid);
      if (scene) {
        scene.view();
      }
    });

    (globalThis as any).ui?.notifications?.info(
      `Created scene: ${result.name} with ${result.wall_count} walls`
    );
  }

  private resetForm(): void {
    const resultContainer = this.container.querySelector('.result-container') as HTMLElement;
    const formContainer = this.container.querySelector('.upload-form') as HTMLElement;

    resultContainer.style.display = 'none';
    formContainer.style.display = 'block';

    // Clear form
    (this.container.querySelector('#battlemap-file') as HTMLInputElement).value = '';
    (this.container.querySelector('#scene-name') as HTMLInputElement).value = '';
    (this.container.querySelector('#skip-walls') as HTMLInputElement).checked = false;
    (this.container.querySelector('#grid-size-mode') as HTMLSelectElement).value = 'auto';
    (this.container.querySelector('#grid-size') as HTMLInputElement).style.display = 'none';
  }
}
