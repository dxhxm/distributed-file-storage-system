/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Component Props & State Interfaces
 */

import type {
  ClusterStatusResponse,
  NodeInfo,
  NodeDetailResponse,
  FileInfo,
} from './api.ts';

export type ViewState = 'normal' | 'loading' | 'empty' | 'error';

export interface ClusterStatusProps {
  status: ClusterStatusResponse | null;
  state?: ViewState;
  errorMessage?: string;
  isLoading?: boolean;
}

export interface HeartbeatRailProps {
  nodes?: NodeInfo[];
  state?: ViewState;
  errorMessage?: string;
  activeNodeId?: string | null;
  onSelectNode?: (nodeId: string) => void;
}

export interface NodeListProps {
  nodes?: NodeInfo[];
  state?: ViewState;
  errorMessage?: string;
  activeNodeId?: string | null;
  onHoverNode?: (nodeId: string | null) => void;
  onSelectNode?: (nodeId: string) => void;
}

export interface UploadState {
  isUploading: boolean;
  filename: string;
  percent: number;
  loadedBytes: number;
  totalBytes: number;
  error: string | null;
  lastFailedFile?: File | null;
}

export interface DownloadState {
  isDownloading: boolean;
  fileId?: string;
  filename?: string;
  error?: string | null;
}

export interface DeleteState {
  confirmingFileId?: string | null;
  isDeleting?: boolean;
  fileId?: string;
  error?: string | null;
}

export interface FilePanelProps {
  files?: FileInfo[];
  state?: ViewState;
  errorMessage?: string;
  totalFiles?: number;
  totalSizeBytes?: number;
  isLoading?: boolean;
  uploadState?: UploadState | null;
  downloadState?: DownloadState | null;
  deleteState?: DeleteState | null;
  searchQuery?: string;
  nodes?: Array<NodeInfo | { id: string; status: string; state?: string }>;
  clusterState?: string | null;
  onUpload?: (file: File) => void;
  onDownload?: (fileId: string, filename?: string) => void;
  onDelete?: (fileId: string) => void;
  onSync?: () => void;
}

export interface NodeDetailProps {
  nodeId: string | null;
  nodeDetail: NodeDetailResponse | null;
  latencyMs?: number;
  isOpen: boolean;
  state?: ViewState;
  errorMessage?: string;
  onClose?: () => void;
  onRefresh?: () => void;
}
