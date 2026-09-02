/**
 * API Contract Types for the Distributed File Storage System (DFSS)
 * Strictly mirrors backend REST endpoints and domain models.
 */

/**
 * Cluster overall health and consensus state.
 * - `HEALTHY`: All cluster nodes are online with an elected leader.
 * - `OPERATIONAL`: Quorum majority is available with an elected leader (degraded tolerance).
 * - `NO MAJORITY`: Quorum is lost or election is actively undecided.
 */
export type ClusterState = 'HEALTHY' | 'OPERATIONAL' | 'NO MAJORITY';

/**
 * Raft node lifecycle role.
 */
export type NodeState = 'LEADER' | 'FOLLOWER' | 'CANDIDATE';

/**
 * Network / heartbeat reachability status.
 */
export type NodeStatus = 'ONLINE' | 'OFFLINE';

/**
 * Storage replication status of a file across the cluster.
 */
export type FileStatus = 'REPLICATED' | 'SYNCING' | 'DEGRADED' | 'CORRUPTED';

/**
 * Response schema for `GET /health`
 */
export interface HealthResponse {
  status: string;
  message: string;
  node_id: string;
  timestamp: number;
}

/**
 * Response schema for `GET /cluster/status`
 */
export interface ClusterStatusResponse {
  cluster_state: ClusterState;
  leader_id: string | null;
  term: number;
  commit_index: number;
  active_nodes: number;
  total_nodes: number;
  timestamp: number;
}

/**
 * Node telemetry and membership representation.
 */
export interface NodeInfo {
  id: string;
  state: NodeState;
  last_heartbeat: number;
  status: NodeStatus;
  url?: string;
}

/**
 * Response schema for `GET /nodes`
 */
export interface NodesResponse {
  nodes: NodeInfo[];
}

/**
 * Response schema for `GET /nodes/{node_id}`
 */
export interface NodeDetailResponse extends NodeInfo {
  term?: number;
  commit_index?: number;
  peers?: string[];
}

/**
 * Replicated file metadata and storage placement.
 */
export interface FileInfo {
  file_id: string;
  name: string;
  size: number;
  replicas: string[];
  status: FileStatus;
  checksum?: string;
  modified_at?: number;
}

/**
 * Response schema for `GET /files`
 */
export interface FilesResponse {
  files: FileInfo[];
  total_files: number;
  total_size_bytes: number;
}

/**
 * Response schema for `POST /upload`
 */
export interface UploadFileResponse {
  message: string;
  filename: string;
}

/**
 * Standard backend error payload schema.
 */
export interface ApiErrorResponse {
  detail?: string;
  error?: string;
  message?: string;
  status_code?: number;
}

export interface DownloadFileResult {
  blob: Blob;
  filename: string;
}

export interface DeleteFileResponse {
  message: string;
  filename: string;
  file_id: string;
}

/**
 * Upload progress callback signature.
 */
export type UploadProgressCallback = (percent: number, loaded: number, total: number) => void;

/**
 * Options for file upload requests.
 */
export interface UploadOptions extends RequestOptions {
  onProgress?: UploadProgressCallback;
}

/**
 * Per-request configuration options for the API fetch client.
 */
export interface RequestOptions {
  baseUrl?: string;
  timeoutMs?: number;
  signal?: AbortSignal;
  headers?: Record<string, string>;
  method?: string;
}

/**
 * Global client initialization configuration.
 */
export interface ClientConfig {
  baseUrl?: string;
  defaultTimeoutMs?: number;
  fetchImpl?: typeof fetch;
}
