/**
 * Handle file system browsing messages from backend.
 */

import type { FileListResult } from './index.js';

/**
 * List files in a directory using FilePicker.browse.
 */
export async function handleListFiles(data: {
  path: string;
  source?: 'data' | 'public' | 's3';
  recursive?: boolean;
  extensions?: string[];
}): Promise<FileListResult> {
  try {
    const { path, source = 'public', recursive = false, extensions } = data;

    const allFiles: string[] = [];

    async function browseDir(dirPath: string): Promise<void> {
      const result = await FilePicker.browse(source, dirPath, { extensions });

      allFiles.push(...result.files);

      if (recursive) {
        for (const subDir of result.dirs) {
          await browseDir(subDir);
        }
      }
    }

    await browseDir(path);

    console.log('[Tablewrite] Listed', allFiles.length, 'files from:', path);

    return {
      success: true,
      files: allFiles
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to list files:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}
