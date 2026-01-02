/**
 * Handle file system browsing messages from backend.
 */

import type { FileListResult, FileUploadResult } from './index.js';

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

/**
 * Upload a file to FoundryVTT world folder.
 *
 * Uses FilePicker.upload() for proper Foundry integration.
 */
export async function handleFileUpload(data: {
  filename: string;
  content: string;      // base64 encoded
  destination: string;  // relative path like "uploaded-maps"
}): Promise<FileUploadResult> {
  try {
    const { filename, content, destination } = data;

    // Decode base64 to binary
    const binaryString = atob(content);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    const blob = new Blob([bytes]);
    const file = new File([blob], filename);

    // Construct target path: worlds/<current-world>/<destination>/
    const worldPath = `worlds/${game.world.id}/${destination}`;

    // Upload using FilePicker (creates folder if needed)
    const response = await FilePicker.upload(
      "data",
      worldPath,
      file,
      {}
    );

    if (!response.path) {
      throw new Error("Upload failed: no path returned");
    }

    console.log('[Tablewrite] Uploaded file:', response.path);

    return {
      success: true,
      path: response.path
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to upload file:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}
