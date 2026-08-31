/**
 * Unified Typed API Fetch Client for Distributed File Storage System (DFSS)
 * Adheres strictly to the backend API contract with zero `any` types.
 */

import type {
  HealthResponse,
  ClusterStatusResponse,
  NodesResponse,
  NodeDetailResponse,
  FilesResponse,
  UploadFileResponse,
  UploadOptions,
  RequestOptions,
  ClientConfig,
  ApiErrorResponse,
} from '../types/api.ts';

export const DEFAULT_BASE_URL = 'http://localhost:8000';
export const DEFAULT_TIMEOUT_MS = 5000;

/**
 * Custom Error for API client failures, capturing status codes, URLs, and server details.
 */
export class ApiClientError extends Error {
  public readonly status: number;
  public readonly url: string;
  public readonly errorData?: ApiErrorResponse;

  constructor(message: string, status: number, url: string, errorData?: ApiErrorResponse) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.url = url;
    this.errorData = errorData;

    // Set prototype explicitly for accurate instanceof checks in all environments
    Object.setPrototypeOf(this, ApiClientError.prototype);
  }
}

/**
 * Normalizes URL path combinations without duplicate slashes.
 */
function buildUrl(baseUrl: string, path: string): string {
  const normalizedBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

/**
 * Distributed Storage Client Class
 */
export class DistributedStorageClient {
  private readonly baseUrl: string;
  private readonly defaultTimeoutMs: number;
  private readonly fetchImpl: typeof fetch;

  constructor(config: ClientConfig = {}) {
    this.baseUrl = config.baseUrl ?? DEFAULT_BASE_URL;
    this.defaultTimeoutMs = config.defaultTimeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.fetchImpl = config.fetchImpl ?? (typeof fetch !== 'undefined' ? fetch.bind(globalThis) : globalThis.fetch);
  }

  /**
   * Internal generic request handler with strict typing and timeout control.
   */
  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const targetBaseUrl = options.baseUrl ?? this.baseUrl;
    const url = buildUrl(targetBaseUrl, path);
    const timeoutMs = options.timeoutMs ?? this.defaultTimeoutMs;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      controller.abort();
    }, timeoutMs);

    // If caller provided an external AbortSignal, forward its abort event
    if (options.signal) {
      options.signal.addEventListener('abort', () => {
        controller.abort();
      });
    }

    try {
      const response = await this.fetchImpl(url, {
        method: 'GET',
        headers: {
          Accept: 'application/json',
          ...options.headers,
        },
        signal: controller.signal,
      });

      if (!response.ok) {
        let errorData: ApiErrorResponse | undefined;
        try {
          const rawJson = (await response.json()) as unknown;
          if (rawJson && typeof rawJson === 'object') {
            errorData = rawJson as ApiErrorResponse;
          }
        } catch {
          // Non-JSON error body, fallback to status text
        }

        const errorMessage = errorData?.detail || errorData?.message || errorData?.error || response.statusText || `HTTP ${response.status}`;
        throw new ApiClientError(
          `Request to ${url} failed with status ${response.status}: ${errorMessage}`,
          response.status,
          url,
          errorData
        );
      }

      const jsonPayload = (await response.json()) as unknown;
      return jsonPayload as T;
    } catch (error: unknown) {
      if (error instanceof ApiClientError) {
        throw error;
      }

      if (error instanceof Error && error.name === 'AbortError') {
        throw new ApiClientError(`Request to ${url} timed out after ${timeoutMs}ms`, 408, url);
      }

      const networkErrorMessage = error instanceof Error ? error.message : 'Unknown network error';
      throw new ApiClientError(`Network request to ${url} failed: ${networkErrorMessage}`, 0, url);
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * GET /health
   * Retrieves individual node health, ID, and alive state.
   */
  public async getHealth(options?: RequestOptions): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health', options);
  }

  /**
   * GET /cluster/status
   * Retrieves aggregated cluster consensus state ('HEALTHY' | 'OPERATIONAL' | 'NO MAJORITY').
   */
  public async getClusterStatus(options?: RequestOptions): Promise<ClusterStatusResponse> {
    return this.request<ClusterStatusResponse>('/cluster/status', options);
  }

  /**
   * GET /nodes
   * Retrieves all cluster node statuses, roles, and last heartbeat timestamps.
   */
  public async getNodes(options?: RequestOptions): Promise<NodesResponse> {
    return this.request<NodesResponse>('/nodes', options);
  }

  /**
   * GET /nodes/{node_id}
   * Retrieves detailed information and telemetry for a specific node.
   */
  public async getNodeById(nodeId: string, options?: RequestOptions): Promise<NodeDetailResponse> {
    const encodedId = encodeURIComponent(nodeId);
    return this.request<NodeDetailResponse>(`/nodes/${encodedId}`, options);
  }

  /**
   * GET /files
   * Retrieves the catalog of replicated files with size, replicas, and replication status.
   */
  public async getFiles(options?: RequestOptions): Promise<FilesResponse> {
    return this.request<FilesResponse>('/files', options);
  }

  /**
   * POST /files/upload (with fallback to /upload)
   * Uploads a file with progress tracking and streaming support.
   */
  public async uploadFile(
    file: File | Blob,
    filenameOrOptions?: string | UploadOptions,
    options?: UploadOptions
  ): Promise<UploadFileResponse> {
    const filename = typeof filenameOrOptions === 'string'
      ? filenameOrOptions
      : (file instanceof File ? file.name : 'upload.bin');
    const opts = typeof filenameOrOptions === 'object' ? filenameOrOptions : (options ?? {});
    const targetBaseUrl = opts.baseUrl ?? this.baseUrl;
    const url = buildUrl(targetBaseUrl, '/files/upload');
    const timeoutMs = opts.timeoutMs ?? 30000;

    // Use XMLHttpRequest in browser runtime for accurate non-blocking upload progress
    if (typeof XMLHttpRequest !== 'undefined' && !opts.signal) {
      return new Promise<UploadFileResponse>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const formData = new FormData();
        formData.append('file', file, filename);

        xhr.open('POST', url, true);
        xhr.timeout = timeoutMs;
        xhr.responseType = 'json';

        if (opts.headers) {
          for (const [key, value] of Object.entries(opts.headers)) {
            xhr.setRequestHeader(key, value);
          }
        }

        if (xhr.upload && opts.onProgress) {
          xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) {
              const percent = Math.min(100, Math.round((event.loaded / event.total) * 100));
              opts.onProgress!(percent, event.loaded, event.total);
            }
          };
        }

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            const resp = (xhr.response && typeof xhr.response === 'object')
              ? xhr.response as UploadFileResponse
              : { message: 'File uploaded successfully', filename };
            if (opts.onProgress) opts.onProgress(100, file.size, file.size);
            resolve(resp);
          } else {
            let errorData: ApiErrorResponse | undefined;
            if (xhr.response && typeof xhr.response === 'object') {
              errorData = xhr.response as ApiErrorResponse;
            }
            const msg = errorData?.detail || errorData?.message || `Upload failed with status ${xhr.status}`;
            reject(new ApiClientError(`Request to ${url} failed with status ${xhr.status}: ${msg}`, xhr.status, url, errorData));
          }
        };

        xhr.onerror = () => {
          reject(new ApiClientError(`Network request to ${url} failed during upload`, 0, url));
        };

        xhr.ontimeout = () => {
          reject(new ApiClientError(`Request to ${url} timed out after ${timeoutMs}ms`, 408, url));
        };

        xhr.send(formData);
      });
    }

    // Fallback to fetchImpl (Node / tests)
    const formData = new FormData();
    formData.append('file', file, filename);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    if (opts.signal) {
      opts.signal.addEventListener('abort', () => controller.abort());
    }

    try {
      if (opts.onProgress) opts.onProgress(10, 0, file.size);
      const response = await this.fetchImpl(url, {
        method: 'POST',
        body: formData,
        headers: {
          Accept: 'application/json',
          ...opts.headers,
        },
        signal: controller.signal,
      });

      if (!response.ok) {
        let errorData: ApiErrorResponse | undefined;
        try {
          const rawJson = (await response.json()) as unknown;
          if (rawJson && typeof rawJson === 'object') {
            errorData = rawJson as ApiErrorResponse;
          }
        } catch {
          // non-json
        }
        const errorMessage = errorData?.detail || errorData?.message || response.statusText || `HTTP ${response.status}`;
        throw new ApiClientError(`Request to ${url} failed with status ${response.status}: ${errorMessage}`, response.status, url, errorData);
      }

      if (opts.onProgress) opts.onProgress(100, file.size, file.size);
      const jsonPayload = (await response.json()) as unknown;
      return jsonPayload as UploadFileResponse;
    } catch (error: unknown) {
      if (error instanceof ApiClientError) throw error;
      if (error instanceof Error && error.name === 'AbortError') {
        throw new ApiClientError(`Request to ${url} timed out after ${timeoutMs}ms`, 408, url);
      }
      const msg = error instanceof Error ? error.message : 'Unknown network error';
      throw new ApiClientError(`Network request to ${url} failed: ${msg}`, 0, url);
    } finally {
      clearTimeout(timeoutId);
    }
  }
}

/**
 * Default singleton client instance configured for localhost:8000.
 */
export const defaultClient = new DistributedStorageClient();

/**
 * Helper to normalize options argument when caller optionally supplies baseUrl string first.
 */
function resolveOptions(
  baseUrlOrOptions?: string | RequestOptions,
  extraOptions?: RequestOptions
): RequestOptions | undefined {
  if (typeof baseUrlOrOptions === 'string') {
    return { ...extraOptions, baseUrl: baseUrlOrOptions };
  }
  return baseUrlOrOptions;
}

/**
 * Factory function to instantiate a custom DistributedStorageClient.
 */
export function createClient(config?: ClientConfig): DistributedStorageClient {
  return new DistributedStorageClient(config);
}

/**
 * GET /health
 */
export async function getHealth(options?: RequestOptions): Promise<HealthResponse>;
export async function getHealth(baseUrl: string, options?: RequestOptions): Promise<HealthResponse>;
export async function getHealth(
  baseUrlOrOptions?: string | RequestOptions,
  extraOptions?: RequestOptions
): Promise<HealthResponse> {
  return defaultClient.getHealth(resolveOptions(baseUrlOrOptions, extraOptions));
}

/**
 * GET /cluster/status
 */
export async function getClusterStatus(options?: RequestOptions): Promise<ClusterStatusResponse>;
export async function getClusterStatus(baseUrl: string, options?: RequestOptions): Promise<ClusterStatusResponse>;
export async function getClusterStatus(
  baseUrlOrOptions?: string | RequestOptions,
  extraOptions?: RequestOptions
): Promise<ClusterStatusResponse> {
  return defaultClient.getClusterStatus(resolveOptions(baseUrlOrOptions, extraOptions));
}

/**
 * GET /nodes
 */
export async function getNodes(options?: RequestOptions): Promise<NodesResponse>;
export async function getNodes(baseUrl: string, options?: RequestOptions): Promise<NodesResponse>;
export async function getNodes(
  baseUrlOrOptions?: string | RequestOptions,
  extraOptions?: RequestOptions
): Promise<NodesResponse> {
  return defaultClient.getNodes(resolveOptions(baseUrlOrOptions, extraOptions));
}

/**
 * GET /nodes/{node_id}
 */
export async function getNodeById(nodeId: string, options?: RequestOptions): Promise<NodeDetailResponse>;
export async function getNodeById(nodeId: string, baseUrl: string, options?: RequestOptions): Promise<NodeDetailResponse>;
export async function getNodeById(
  nodeId: string,
  baseUrlOrOptions?: string | RequestOptions,
  extraOptions?: RequestOptions
): Promise<NodeDetailResponse> {
  return defaultClient.getNodeById(nodeId, resolveOptions(baseUrlOrOptions, extraOptions));
}

/**
 * GET /files
 */
export async function getFiles(options?: RequestOptions): Promise<FilesResponse>;
export async function getFiles(baseUrl: string, options?: RequestOptions): Promise<FilesResponse>;
export async function getFiles(
  baseUrlOrOptions?: string | RequestOptions,
  extraOptions?: RequestOptions
): Promise<FilesResponse> {
  return defaultClient.getFiles(resolveOptions(baseUrlOrOptions, extraOptions));
}

/**
 * POST /files/upload
 */
export async function uploadFile(
  file: File | Blob,
  options?: UploadOptions
): Promise<UploadFileResponse>;
export async function uploadFile(
  file: File | Blob,
  filename: string,
  options?: UploadOptions
): Promise<UploadFileResponse>;
export async function uploadFile(
  file: File | Blob,
  filenameOrOptions?: string | UploadOptions,
  options?: UploadOptions
): Promise<UploadFileResponse> {
  return defaultClient.uploadFile(file, filenameOrOptions, options);
}
