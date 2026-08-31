/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Service: FileService (Zone 3 Replicated Storage Ledger & Upload Manager)
 *
 * Requirements & DoD:
 * - Polls and queries GET /files to provide live replicated file ledger.
 * - Manages real-time search filtering.
 * - Handles non-blocking uploads with progress and status broadcasting.
 * - Manages upload failure states with inline error display and retry capability.
 */

import { apiService } from './apiService.ts';
import type { FileInfo, FilesResponse, UploadFileResponse, UploadProgressCallback } from '../types/api.ts';
import type { UploadState } from '../types/components.ts';

export interface FileServiceResult {
  files: FileInfo[];
  totalFiles: number;
  totalSizeBytes: number;
  reachable: boolean;
  timestamp: number;
  error: string | null;
  searchQuery: string;
  uploadState: UploadState | null;
}

export type FileServiceListener = (result: FileServiceResult) => void;

export interface FilePollingConfig {
  intervalMs?: number;
  requestTimeoutMs?: number;
}

export class FileService {
  private files: FileInfo[] = [];
  private totalFiles = 0;
  private totalSizeBytes = 0;
  private reachable = false;
  private lastError: string | null = null;
  private lastTimestamp = Date.now();
  private searchQuery = '';
  private uploadState: UploadState | null = null;

  private listeners: Set<FileServiceListener> = new Set();
  private timerId: ReturnType<typeof setTimeout> | null = null;
  private abortController: AbortController | null = null;
  private isPolling = false;

  private intervalMs = 3000;
  private requestTimeoutMs = 5000;

  constructor() {
    this.lastTimestamp = Date.now();
  }

  /**
   * Fetches latest /files ledger from coordinator backend.
   */
  public async fetchFiles(): Promise<FileServiceResult> {
    this.abortController = new AbortController();

    try {
      const response: FilesResponse = await apiService.getFiles({
        timeoutMs: this.requestTimeoutMs,
        signal: this.abortController.signal,
      });

      this.files = response.files || [];
      this.totalFiles = response.total_files ?? this.files.length;
      this.totalSizeBytes = response.total_size_bytes ?? this.files.reduce((acc, f) => acc + (f.size || 0), 0);
      this.reachable = true;
      this.lastError = null;
      this.lastTimestamp = Date.now();
    } catch (err: unknown) {
      this.reachable = false;
      this.lastError = err instanceof Error ? err.message : 'Failed to query file ledger';
      this.lastTimestamp = Date.now();
    } finally {
      this.abortController = null;
    }

    const currentResult = this.getResult();
    this.notifyListeners(currentResult);
    return currentResult;
  }

  /**
   * Force an immediate refresh of the files ledger.
   */
  public async refreshFiles(): Promise<FileServiceResult> {
    return this.fetchFiles();
  }

  /**
   * Set filename search filter query.
   */
  public setSearchQuery(query: string): void {
    this.searchQuery = query;
    this.notifyListeners(this.getResult());
  }

  public getSearchQuery(): string {
    return this.searchQuery;
  }

  /**
   * Returns files matching current search query.
   */
  public getFilteredFiles(): FileInfo[] {
    const q = this.searchQuery.trim().toLowerCase();
    if (!q) return this.files;
    return this.files.filter(f => f.name.toLowerCase().includes(q));
  }

  /**
   * Upload a file with progress broadcasting and refresh ledger on success.
   */
  public async uploadFile(
    file: File | Blob,
    filename?: string,
    onProgress?: UploadProgressCallback
  ): Promise<UploadFileResponse> {
    const name = filename || (file instanceof File ? file.name : 'upload.bin');
    const totalBytes = file.size;

    this.uploadState = {
      isUploading: true,
      filename: name,
      percent: 0,
      loadedBytes: 0,
      totalBytes,
      error: null,
      lastFailedFile: file instanceof File ? file : null,
    };
    this.notifyListeners(this.getResult());

    try {
      const res = await apiService.uploadFile(file, name, {
        onProgress: (percent, loaded, total) => {
          if (this.uploadState && this.uploadState.isUploading) {
            this.uploadState.percent = percent;
            this.uploadState.loadedBytes = loaded;
            this.uploadState.totalBytes = total;
            this.notifyListeners(this.getResult());
          }
          if (onProgress) {
            onProgress(percent, loaded, total);
          }
        },
      });

      this.uploadState = {
        isUploading: false,
        filename: name,
        percent: 100,
        loadedBytes: totalBytes,
        totalBytes,
        error: null,
      };
      this.notifyListeners(this.getResult());

      // Refresh files immediately after upload completes
      await this.refreshFiles();

      // Clear successful upload progress card after a short timeout
      setTimeout(() => {
        if (this.uploadState && !this.uploadState.isUploading && !this.uploadState.error) {
          this.uploadState = null;
          this.notifyListeners(this.getResult());
        }
      }, 1200);

      return res;
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Upload failed: coordinator unreachable';
      this.uploadState = {
        isUploading: false,
        filename: name,
        percent: 0,
        loadedBytes: 0,
        totalBytes,
        error: errorMsg,
        lastFailedFile: file instanceof File ? file : null,
      };
      this.notifyListeners(this.getResult());
      throw err;
    }
  }

  /**
   * Dismiss current upload error banner.
   */
  public dismissUploadError(): void {
    if (this.uploadState?.error) {
      this.uploadState = null;
      this.notifyListeners(this.getResult());
    }
  }

  /**
   * Retry the last failed upload if available.
   */
  public async retryLastUpload(): Promise<UploadFileResponse | undefined> {
    if (this.uploadState?.lastFailedFile) {
      const fileToRetry = this.uploadState.lastFailedFile;
      return this.uploadFile(fileToRetry);
    }
    return undefined;
  }

  public getUploadState(): UploadState | null {
    return this.uploadState;
  }

  /**
   * Starts periodic polling loop for files ledger.
   */
  public startPolling(config: FilePollingConfig | number = 3000): void {
    if (typeof config === 'number') {
      this.intervalMs = config;
    } else if (config) {
      this.intervalMs = config.intervalMs ?? 3000;
      this.requestTimeoutMs = config.requestTimeoutMs ?? 5000;
    }

    this.stopPolling();
    this.isPolling = true;

    const executeLoop = async () => {
      if (!this.isPolling) return;
      await this.fetchFiles();
      if (!this.isPolling) return;

      this.timerId = setTimeout(() => {
        void executeLoop();
      }, this.intervalMs);
    };

    void executeLoop();
  }

  /**
   * Stops polling, clears timers, and aborts any active fetch request.
   */
  public stopPolling(): void {
    this.isPolling = false;

    if (this.timerId !== null) {
      clearTimeout(this.timerId);
      this.timerId = null;
    }

    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  /**
   * Subscribes a listener to file ledger updates.
   */
  public subscribe(listener: FileServiceListener): () => void {
    this.listeners.add(listener);
    listener(this.getResult());
    return () => {
      this.listeners.delete(listener);
    };
  }

  public getResult(): FileServiceResult {
    return {
      files: this.getFilteredFiles(),
      totalFiles: this.totalFiles,
      totalSizeBytes: this.totalSizeBytes,
      reachable: this.reachable,
      timestamp: this.lastTimestamp,
      error: this.lastError,
      searchQuery: this.searchQuery,
      uploadState: this.uploadState,
    };
  }

  public getAllRawFiles(): FileInfo[] {
    return this.files;
  }

  public isRunning(): boolean {
    return this.isPolling;
  }

  public reset(): void {
    this.stopPolling();
    this.files = [];
    this.totalFiles = 0;
    this.totalSizeBytes = 0;
    this.searchQuery = '';
    this.uploadState = null;
    this.reachable = false;
    this.lastError = null;
    this.listeners.clear();
  }

  private notifyListeners(result: FileServiceResult): void {
    for (const listener of this.listeners) {
      try {
        listener(result);
      } catch (err) {
        console.error('Error in fileService listener:', err);
      }
    }
  }
}

export const fileService = new FileService();
export default fileService;
