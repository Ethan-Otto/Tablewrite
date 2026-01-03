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

    console.log('[Tablewrite] Starting file upload:', filename, 'to', destination);

    // Decode base64 to binary
    const binaryString = atob(content);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    const blob = new Blob([bytes]);
    const file = new File([blob], filename);

    console.log('[Tablewrite] Created file blob, size:', blob.size, 'bytes');

    // Construct target path: worlds/<current-world>/<destination>/
    const worldPath = `worlds/${game.world.id}/${destination}`;
    console.log('[Tablewrite] Target path:', worldPath);

    // Ensure each directory level exists (createDirectory is not in types but exists in Foundry)
    const pathParts = destination.split('/');
    let currentPath = `worlds/${game.world.id}`;
    for (const part of pathParts) {
      currentPath = `${currentPath}/${part}`;
      try {
        await (FilePicker as any).createDirectory("data", currentPath);
        console.log('[Tablewrite] Created directory:', currentPath);
      } catch (dirError: any) {
        // Directory may already exist, which is fine - EEXIST error
        const errStr = String(dirError);
        if (!errStr.includes('EEXIST') && !errStr.includes('already exists')) {
          console.log('[Tablewrite] Directory creation note for', currentPath, ':', errStr);
        }
      }
    }

    // Upload using FilePicker
    const response = await FilePicker.upload(
      "data",
      worldPath,
      file,
      {}
    );

    console.log('[Tablewrite] FilePicker.upload response:', JSON.stringify(response));

    // Handle various response formats
    const uploadedPath = response?.path || (response as any)?.result?.path;

    if (!uploadedPath) {
      throw new Error(`Upload failed: no path in response. Full response: ${JSON.stringify(response)}`);
    }

    console.log('[Tablewrite] Uploaded file:', uploadedPath);

    return {
      success: true,
      path: uploadedPath
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to upload file:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}
