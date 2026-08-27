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

export interface FilePanelProps {
  files?: FileInfo[];
  state?: ViewState;
  errorMessage?: string;
  totalFiles?: number;
  totalSizeBytes?: number;
  isLoading?: boolean;
  onUpload?: (file: File) => void;
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
