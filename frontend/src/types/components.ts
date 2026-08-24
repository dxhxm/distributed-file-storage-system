/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Component Props & State Interfaces
 */

import type {
  ClusterStatusResponse,
  NodeInfo,
  FileInfo,
} from './api.ts';

export interface ClusterStatusProps {
  status: ClusterStatusResponse | null;
  isLoading: boolean;
  error?: string | null;
}

export interface HeartbeatRailProps {
  nodes: NodeInfo[];
  activeNodeId?: string | null;
  onSelectNode?: (nodeId: string) => void;
}

export interface NodeListProps {
  nodes: NodeInfo[];
  activeNodeId?: string | null;
  onHoverNode?: (nodeId: string | null) => void;
  onSelectNode?: (nodeId: string) => void;
}

export interface FilePanelProps {
  files: FileInfo[];
  totalFiles: number;
  totalSizeBytes: number;
  isLoading: boolean;
  onUpload?: (file: File) => void;
  onSync?: () => void;
}
