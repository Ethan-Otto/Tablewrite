/**
 * Foundry VTT type declarations for the module.
 * Minimal types for the Foundry globals we use.
 */

// Make this a module
export {};

// Foundry VTT global types
declare global {
  interface SettingOptions {
    name: string;
    hint?: string;
    default: unknown;
    type: typeof String | typeof Number | typeof Boolean | typeof Object | typeof Array;
    config: boolean;
    scope: 'world' | 'client';
    onChange?: (value: unknown) => void;
  }

  interface ClientSettings {
    register(module: string, key: string, options: SettingOptions): void;
    get(module: string, key: string): unknown;
    set(module: string, key: string, value: unknown): Promise<unknown>;
  }

  interface Localization {
    format(key: string, data?: Record<string, unknown>): string;
    localize(key: string): string;
  }

  interface Notifications {
    info(message: string, options?: { localize?: boolean }): void;
    warn(message: string, options?: { localize?: boolean }): void;
    error(message: string, options?: { localize?: boolean }): void;
  }

  interface UI {
    notifications?: Notifications;
  }

  // Application base class (minimal definition for renderSidebar hook)
  interface Application {
    id: string;
  }

  interface CompendiumCollection {
    get(key: string): Compendium | undefined;
    filter(fn: (pack: Compendium) => boolean): Compendium[];
  }

  interface Compendium {
    documentName: string;
    metadata: { label: string; packageType: string; packageName: string };
    index: { contents: CompendiumIndexEntry[] } | null;
    getIndex(options?: { fields?: string[] }): Promise<{ contents: CompendiumIndexEntry[] }>;
    getDocument(id: string): Promise<FoundryDocument | null>;
  }

  interface CompendiumIndexEntry {
    _id: string;
    name: string;
    type?: string;
    img?: string;
    uuid: string;
  }

  interface World {
    id: string;
  }

  interface FolderCollection {
    find(fn: (folder: FoundryDocument) => boolean): FoundryDocument | undefined;
    map<T>(fn: (folder: FoundryDocument) => T): T[];
  }

  interface Game {
    settings: ClientSettings;
    i18n: Localization;
    actors: ActorCollection | null;
    folders: FolderCollection | null;
    packs: CompendiumCollection;
    world: World;
  }

  interface ActorCollection {
    map<T>(fn: (actor: FoundryDocument) => T): T[];
  }

  // Foundry globals
  const game: Game;
  const ui: UI;

  // Foundry Hooks
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const Hooks: {
    once(hook: string, callback: (...args: any[]) => void): void;
    on(hook: string, callback: (...args: any[]) => void): void;
  };

  // Foundry Document classes
  const Actor: {
    create(data: Record<string, unknown>): Promise<{ id: string; name: string } | null>;
  };

  const JournalEntry: {
    create(data: Record<string, unknown>): Promise<{ id: string; name: string } | null>;
  };

  const Scene: {
    create(data: Record<string, unknown>): Promise<{ id: string; name: string } | null>;
  };

  const Folder: {
    create(data: Record<string, unknown>): Promise<{ id: string; name: string } | null>;
  };

  // FoundryVTT Document interface (for fetched documents)
  interface FoundryDocument {
    id: string;
    name: string;
    toObject(): Record<string, unknown>;
    delete(): Promise<void>;
    createEmbeddedDocuments(type: string, data: Record<string, unknown>[]): Promise<unknown[]>;
  }

  // Global function to fetch any document by UUID
  function fromUuid(uuid: string): Promise<FoundryDocument | null>;

  // FilePicker for browsing file system
  interface FilePickerOptions {
    bucket?: string;
    source?: 'data' | 'public' | 's3';
    target?: string;
  }

  interface BrowseResult {
    target: string;
    files: string[];
    dirs: string[];
  }

  interface UploadResult {
    path: string;
    message?: string;
  }

  const FilePicker: {
    browse(
      source: 'data' | 'public' | 's3',
      target: string,
      options?: { extensions?: string[] }
    ): Promise<BrowseResult>;
    upload(
      source: 'data' | 'public' | 's3',
      path: string,
      file: File,
      options?: Record<string, unknown>
    ): Promise<UploadResult>;
  };

  // Foundry utils namespace
  const foundry: {
    utils: {
      randomID(length?: number): string;
    };
  };
}
