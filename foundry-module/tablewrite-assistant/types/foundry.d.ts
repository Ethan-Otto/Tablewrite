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

  interface Game {
    settings: ClientSettings;
    i18n: Localization;
    actors: ActorCollection | null;
    packs: CompendiumCollection;
  }

  interface ActorCollection {
    map<T>(fn: (actor: FoundryDocument) => T): T[];
  }

  // Foundry globals
  const game: Game;
  const ui: UI;

  // Foundry Hooks
  const Hooks: {
    once(hook: string, callback: (...args: unknown[]) => void): void;
    on(hook: string, callback: (...args: unknown[]) => void): void;
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

  // FoundryVTT Document interface (for fetched documents)
  interface FoundryDocument {
    id: string;
    name: string;
    toObject(): Record<string, unknown>;
    delete(): Promise<void>;
  }

  // Global function to fetch any document by UUID
  function fromUuid(uuid: string): Promise<FoundryDocument | null>;
}
