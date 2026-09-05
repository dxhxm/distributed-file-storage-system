/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Component: FilePanel (Zone 3 Replicated File Storage)
 */

import type { FileInfo } from '../types/api.ts';
import { formatBytes } from '../tokens/index.ts';
import { formatTimeUTC } from './NodeList.ts';
import type { ViewState, UploadState, DownloadState, DeleteState } from '../types/components.ts';

export function hasReplica(replicas: string[] = [], targetNode: 'A' | 'B' | 'C'): boolean {
  return replicas.some(r => {
    const clean = r.toLowerCase().replace(/\s+/g, '').replace(/^node/i, '');
    if (targetNode === 'A') return clean === 'a' || clean === '1';
    if (targetNode === 'B') return clean === 'b' || clean === '2';
    if (targetNode === 'C') return clean === 'c' || clean === '3';
    return false;
  });
}

export interface ReplicaNodeInfo {
  id: string;
  isOnline: boolean;
  isLeader: boolean;
  state: string;
  status: string;
}

export function findNodeForTarget(
  nodes: Array<{ id: string; status?: string; state?: string; displayName?: string }> = [],
  target: 'A' | 'B' | 'C'
): ReplicaNodeInfo {
  const node = nodes.find(n => {
    const raw = (n.displayName || n.id).toLowerCase().replace(/\s+/g, '').replace(/^node/i, '');
    if (target === 'A') return raw === 'a' || raw === '1';
    if (target === 'B') return raw === 'b' || raw === '2';
    if (target === 'C') return raw === 'c' || raw === '3';
    return false;
  });

  const isOnline = node ? (node.status === 'ONLINE') : true;
  const state = node?.state || (target === 'A' ? 'LEADER' : 'FOLLOWER');
  const isLeader = state === 'LEADER';
  const status = node?.status || 'ONLINE';

  return {
    id: node?.displayName || node?.id || `Node ${target}`,
    isOnline,
    isLeader,
    state,
    status,
  };
}

export function renderClusterNoticeBanner(clusterState?: string | null): string {
  if (clusterState === 'NO MAJORITY') {
    return `
      <div class="cluster-notice-banner notice-down" id="cluster-notice-banner" role="status" aria-live="polite">
        <div class="cluster-notice-content">
          <span class="badge badge-down"><span class="status-dot dot-down"></span> CONSENSUS PAUSED</span>
          <span class="cluster-notice-text font-sans text-xs">
            <strong>Quorum majority lost (< 2/3 nodes online).</strong> Consensus replication and mutations are paused to prevent split-brain inconsistencies. Existing replicas on active nodes remain downloadable.
          </span>
        </div>
      </div>
    `;
  }
  if (clusterState === 'OPERATIONAL') {
    return `
      <div class="cluster-notice-banner notice-warn" id="cluster-notice-banner" role="status" aria-live="polite">
        <div class="cluster-notice-content">
          <span class="badge badge-warn"><span class="status-dot dot-warn"></span> QUORUM DEGRADED</span>
          <span class="cluster-notice-text font-sans text-xs">
            <strong>1 node offline (2/3 nodes online).</strong> Majority quorum preserved; consensus transactions remain active. Replicas hosted on the offline node are temporarily unreachable.
          </span>
        </div>
      </div>
    `;
  }
  return '';
}

export function renderFileRow(
  file: FileInfo,
  downloadState?: DownloadState | null,
  deleteState?: DeleteState | null,
  nodes?: Array<{ id: string; status?: string; state?: string; displayName?: string }>,
  clusterState?: string | null
): string {
  const nodeA = findNodeForTarget(nodes, 'A');
  const nodeB = findNodeForTarget(nodes, 'B');
  const nodeC = findNodeForTarget(nodes, 'C');

  const hasA = hasReplica(file.replicas, 'A');
  const hasB = hasReplica(file.replicas, 'B');
  const hasC = hasReplica(file.replicas, 'C');

  const storedReplicas: Array<{ target: 'A' | 'B' | 'C'; node: ReplicaNodeInfo }> = [];
  if (hasA) storedReplicas.push({ target: 'A', node: nodeA });
  if (hasB) storedReplicas.push({ target: 'B', node: nodeB });
  if (hasC) storedReplicas.push({ target: 'C', node: nodeC });

  const totalStored = storedReplicas.length;
  const reachableCount = storedReplicas.filter(r => r.node.isOnline).length;
  const offlineNodes = storedReplicas.filter(r => !r.node.isOnline);

  let badgeClass = 'badge-ok';
  let statusText = '';
  let statusTitle = '';

  if (file.status === 'CORRUPTED') {
    badgeClass = 'badge-down';
    statusText = `CORRUPTED (${reachableCount}/${totalStored || 3})`;
    statusTitle = 'Replica checksum mismatch detected';
  } else if (file.status === 'SYNCING') {
    badgeClass = 'badge-warn';
    statusText = `SYNCING (${reachableCount}/3)`;
    statusTitle = `Replication in progress: ${totalStored}/3 stored, awaiting peer sync`;
  } else if (reachableCount === 0 && totalStored > 0) {
    badgeClass = 'badge-down';
    statusText = `UNREACHABLE (0/${totalStored})`;
    statusTitle = `All nodes holding replicas (${offlineNodes.map(r => r.node.id).join(', ')}) are OFFLINE`;
  } else if (offlineNodes.length > 0) {
    badgeClass = 'badge-warn';
    statusText = `DEGRADED (${reachableCount}/3)`;
    statusTitle = `${totalStored}/3 stored cluster-wide, but ${offlineNodes.map(r => r.node.id).join(', ')} is OFFLINE`;
  } else if (totalStored === 3) {
    badgeClass = 'badge-ok';
    statusText = `REPLICATED (3/3)`;
    statusTitle = 'Target 3x replication factor achieved across active nodes';
  } else {
    badgeClass = 'badge-warn';
    statusText = `${file.status} (${reachableCount}/3)`;
    statusTitle = `${totalStored} of 3 target replicas exist; ${reachableCount} reachable`;
  }

  const renderReplicaPill = (target: 'A' | 'B' | 'C', has: boolean, node: ReplicaNodeInfo) => {
    if (!has) {
      return `<span class="replica-pill missing" title="Missing on ${node.id} — Target: 3x replication factor" style="opacity: 0.35;">-</span>`;
    }
    if (!node.isOnline) {
      return `<span class="replica-pill replica-offline" title="${node.id} (OFFLINE) — Replica stored but node unreachable"><span class="replica-node-dot dot-down"></span>${target}</span>`;
    }
    const leaderClass = node.isLeader ? 'replica-leader' : '';
    return `<span class="replica-pill active ${leaderClass}" title="${node.id} (${node.state}) — Active replica reachable"><span class="replica-node-dot dot-ok"></span>${target}</span>`;
  };

  const pillA = renderReplicaPill('A', hasA, nodeA);
  const pillB = renderReplicaPill('B', hasB, nodeB);
  const pillC = renderReplicaPill('C', hasC, nodeC);

  const timeStr = file.modified_at ? formatTimeUTC(file.modified_at) : '21:40:15 UTC';
  const isDownloading = Boolean(
    downloadState?.isDownloading &&
    (downloadState.fileId === file.file_id || downloadState.filename === file.name)
  );

  const isConfirmingDelete = Boolean(
    deleteState?.confirmingFileId === file.file_id || deleteState?.confirmingFileId === file.name
  );
  const isDeletingThisFile = Boolean(
    deleteState?.isDeleting &&
    (deleteState.fileId === file.file_id || deleteState.fileId === file.name)
  );

  const downloadDisabled = isDownloading || isDeletingThisFile || reachableCount === 0;
  const downloadTooltip = reachableCount === 0 ? 'All replica nodes are offline' : `Download ${file.name}`;

  const isConsensusPaused = clusterState === 'NO MAJORITY';
  const deleteDisabled = isDownloading || isDeletingThisFile || isConsensusPaused;
  const deleteTooltip = isConsensusPaused
    ? 'Mutations paused: Quorum majority lost'
    : `Delete ${file.name}`;

  return `
    <tr class="file-row" id="file-row-${file.file_id || encodeURIComponent(file.name)}">
      <td class="font-mono text-ink">${file.name}</td>
      <td class="font-mono">${formatBytes(file.size)}</td>
      <td title="${statusTitle}"><span class="badge ${badgeClass}">${statusText}</span></td>
      <td>
        <div class="replica-pills">
          ${pillA}
          ${pillB}
          ${pillC}
        </div>
      </td>
      <td class="font-mono text-xs text-muted">${timeStr}</td>
      <td>
        ${isConfirmingDelete ? `
          <div class="file-action-group confirm-delete-group">
            <span class="confirm-delete-prompt font-sans text-2xs text-warn">Delete?</span>
            <button
              type="button"
              class="btn-file-action btn-confirm-delete"
              data-file-id="${file.file_id || file.name}"
              data-filename="${file.name}"
              title="Confirm deletion"
            >
              Confirm
            </button>
            <button
              type="button"
              class="btn-file-action btn-cancel-delete"
              data-file-id="${file.file_id || file.name}"
              title="Cancel deletion"
            >
              Cancel
            </button>
          </div>
        ` : `
          <div class="file-action-group">
            <button
              type="button"
              class="btn-file-action btn-download-file"
              data-file-id="${file.file_id || file.name}"
              data-filename="${file.name}"
              title="${downloadTooltip}"
              ${downloadDisabled ? 'disabled' : ''}
            >
              ${isDownloading ? 'Downloading...' : 'Download'}
            </button>
            <button
              type="button"
              class="btn-file-action btn-delete-file"
              data-file-id="${file.file_id || file.name}"
              data-filename="${file.name}"
              title="${deleteTooltip}"
              ${deleteDisabled ? 'disabled' : ''}
            >
              ${isDeletingThisFile ? 'Deleting...' : 'Delete'}
            </button>
          </div>
        `}
      </td>
    </tr>
  `;
}

export function renderUploadProgress(uploadState?: UploadState | null): string {
  if (!uploadState) return '';

  if (uploadState.isUploading) {
    const loadedStr = formatBytes(uploadState.loadedBytes);
    const totalStr = formatBytes(uploadState.totalBytes);
    return `
      <div class="upload-progress-card" id="upload-progress-card" aria-live="polite">
        <div class="upload-progress-header">
          <div class="upload-progress-title-group">
            <span class="badge badge-info"><span class="status-dot dot-warn"></span> UPLOADING</span>
            <span class="font-mono text-ink text-xs upload-filename" title="${uploadState.filename}">${uploadState.filename}</span>
          </div>
          <span class="font-mono text-xs text-muted upload-percentage">${uploadState.percent}%</span>
        </div>
        <div class="upload-progress-track">
          <div class="upload-progress-bar" style="width: ${uploadState.percent}%;"></div>
        </div>
        <div class="upload-progress-footer">
          <span class="font-mono text-2xs text-muted upload-bytes">${loadedStr} / ${totalStr}</span>
          <span class="font-sans text-2xs text-muted">Streaming to cluster coordinator</span>
        </div>
      </div>
    `;
  }

  if (uploadState.error) {
    return `
      <div class="upload-error-card" id="upload-error-card" role="alert">
        <div class="upload-error-info">
          <span class="badge badge-down"><span class="status-dot dot-down"></span> UPLOAD FAILED</span>
          <span class="upload-error-message font-sans text-xs text-ink" title="${uploadState.error}">${uploadState.error}</span>
        </div>
        <div class="upload-error-actions">
          <button type="button" id="btn-retry-upload" class="btn-error-action" style="font-size: var(--text-2xs); padding: 2px 8px; border-color: var(--color-down-border); color: var(--color-down);">Retry</button>
          <button type="button" id="btn-dismiss-upload-error" class="btn-error-action" style="font-size: var(--text-2xs); padding: 2px 8px; border-color: var(--color-line); color: var(--color-muted);">Dismiss</button>
        </div>
      </div>
    `;
  }

  return '';
}

export function renderDownloadError(downloadState?: DownloadState | null): string {
  if (!downloadState?.error) return '';
  return `
    <div class="download-error-card" id="download-error-card" role="alert">
      <div class="download-error-info">
        <span class="badge badge-down"><span class="status-dot dot-down"></span> REPLICA ERROR</span>
        <span class="download-error-message font-sans text-xs text-ink" title="${downloadState.error}">${downloadState.error}</span>
      </div>
      <div class="download-error-actions">
        <button type="button" id="btn-dismiss-download-error" class="btn-error-action" style="font-size: var(--text-2xs); padding: 2px 8px; border-color: var(--color-line); color: var(--color-muted);">Dismiss</button>
      </div>
    </div>
  `;
}

export function renderDeleteError(deleteState?: DeleteState | null): string {
  if (!deleteState?.error) return '';
  return `
    <div class="delete-error-card" id="delete-error-card" role="alert">
      <div class="delete-error-info">
        <span class="badge badge-down"><span class="status-dot dot-down"></span> DELETE ERROR</span>
        <span class="delete-error-message font-sans text-xs text-ink" title="${deleteState.error}">${deleteState.error}</span>
      </div>
      <div class="delete-error-actions">
        <button type="button" id="btn-dismiss-delete-error" class="btn-error-action" style="font-size: var(--text-2xs); padding: 2px 8px; border-color: var(--color-line); color: var(--color-muted);">Dismiss</button>
      </div>
    </div>
  `;
}

export function renderFilePanelSkeleton(): string {
  return `
    <section class="zone-file-panel" id="zone-file-panel" aria-label="Replicated File Inventory">
      <div class="zone-header">
        <div class="zone-title-group">
          <h2 class="zone-title">Replicated Storage</h2>
          <span class="zone-count font-mono" id="file-panel-count">(INDEXING...)</span>
        </div>
        <span class="zone-caption">Scanning replica indices</span>
      </div>

      <div class="file-panel-toolbar">
        <div style="display: flex; gap: var(--space-2); flex: 1;">
          <input type="search" disabled placeholder="Filter filename..." style="width: 100%; max-width: 240px; font-size: var(--text-xs); opacity: 0.5;" aria-label="Filter files">
        </div>
        <div style="display: flex; gap: var(--space-2);">
          <button disabled style="font-size: var(--text-xs); padding: var(--space-1) var(--space-2-5); opacity: 0.5;">Trigger Sync</button>
          <button disabled style="font-size: var(--text-xs); padding: var(--space-1) var(--space-2-5); opacity: 0.5;">Upload File</button>
        </div>
      </div>

      <div class="file-dropzone" id="file-dropzone">
        <div class="file-table-container">
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Size</th>
                <th>Status</th>
                <th>Replicas</th>
                <th>Modified</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><span class="skeleton-bar" style="width: 140px;"></span></td>
                <td><span class="skeleton-bar" style="width: 60px;"></span></td>
                <td><span class="skeleton-bar" style="width: 80px;"></span></td>
                <td><span class="skeleton-bar" style="width: 50px;"></span></td>
                <td><span class="skeleton-bar" style="width: 75px;"></span></td>
                <td><span class="skeleton-bar" style="width: 60px;"></span></td>
              </tr>
              <tr>
                <td><span class="skeleton-bar" style="width: 120px;"></span></td>
                <td><span class="skeleton-bar" style="width: 55px;"></span></td>
                <td><span class="skeleton-bar" style="width: 80px;"></span></td>
                <td><span class="skeleton-bar" style="width: 50px;"></span></td>
                <td><span class="skeleton-bar" style="width: 75px;"></span></td>
                <td><span class="skeleton-bar" style="width: 60px;"></span></td>
              </tr>
              <tr>
                <td><span class="skeleton-bar" style="width: 160px;"></span></td>
                <td><span class="skeleton-bar" style="width: 70px;"></span></td>
                <td><span class="skeleton-bar" style="width: 80px;"></span></td>
                <td><span class="skeleton-bar" style="width: 50px;"></span></td>
                <td><span class="skeleton-bar" style="width: 75px;"></span></td>
                <td><span class="skeleton-bar" style="width: 60px;"></span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  `;
}

export function renderFilePanelEmpty(
  uploadState?: UploadState | null,
  downloadState?: DownloadState | null,
  deleteState?: DeleteState | null,
  clusterState?: string | null
): string {
  const uploadHtml = renderUploadProgress(uploadState);
  const downloadHtml = renderDownloadError(downloadState);
  const deleteHtml = renderDeleteError(deleteState);
  const bannerHtml = renderClusterNoticeBanner(clusterState);
  const isConsensusPaused = clusterState === 'NO MAJORITY';
  const uploadBtnTitle = isConsensusPaused ? 'Uploads paused: Quorum majority lost (< 2/3 nodes active)' : 'Upload file to cluster';
  const uploadBtnDisabled = isConsensusPaused ? 'disabled' : '';
  const uploadBtnStyle = isConsensusPaused ? 'opacity: 0.5; cursor: not-allowed;' : 'background-color: var(--color-surface-hover); border-color: var(--color-line-bright);';
  const dropOverlaySubtitle = isConsensusPaused ? 'Consensus paused: File uploads temporarily paused until quorum restored' : 'Release file to initiate 3x distributed replication';

  return `
    <section class="zone-file-panel" id="zone-file-panel" aria-label="Replicated File Inventory">
      <div class="zone-header">
        <div class="zone-title-group">
          <h2 class="zone-title">Replicated Storage</h2>
          <span class="zone-count font-mono" id="file-panel-count">(0 FILES &bull; 0 B)</span>
        </div>
        <span class="zone-caption">3x Target Replication Factor</span>
      </div>

      ${bannerHtml}

      <div class="file-panel-toolbar">
        <div style="display: flex; gap: var(--space-2); flex: 1;">
          <input
            type="search"
            id="file-search-input"
            placeholder="Filter filename..."
            disabled
            style="width: 100%; max-width: 240px; font-size: var(--text-xs); opacity: 0.6;"
            aria-label="Filter files"
          >
        </div>
        <div style="display: flex; gap: var(--space-2);">
          <button type="button" id="btn-trigger-sync" disabled style="font-size: var(--text-xs); padding: var(--space-1) var(--space-2-5); opacity: 0.5;">Trigger Sync</button>
          <button type="button" id="btn-upload-file" title="${uploadBtnTitle}" ${uploadBtnDisabled} style="font-size: var(--text-xs); padding: var(--space-1) var(--space-2-5); ${uploadBtnStyle}">Upload File</button>
        </div>
      </div>

      <input type="file" id="file-upload-input" style="display: none;" aria-hidden="true">

      <div class="upload-status-slot" id="upload-status-slot">
        ${uploadHtml}
        ${downloadHtml}
        ${deleteHtml}
      </div>

      <div class="file-dropzone" id="file-dropzone">
        <div class="file-drop-overlay" id="file-drop-overlay" aria-hidden="true">
          <span class="badge ${isConsensusPaused ? 'badge-down' : 'badge-ok'}"><span class="status-dot ${isConsensusPaused ? 'dot-down' : 'dot-ok'}"></span> ${isConsensusPaused ? 'CONSENSUS PAUSED' : 'DROP TO REPLICATE'}</span>
          <span class="font-sans text-xs text-ink" style="margin-top: 4px;">${dropOverlaySubtitle}</span>
        </div>

        <div class="state-panel empty-state-panel" id="file-panel-empty">
          <div class="state-header-group">
            <span class="badge badge-info">STORAGE EMPTY</span>
            <h3 class="state-title">No Files Stored in Cluster</h3>
          </div>
          <p class="state-message">
            No files stored in cluster. Upload a file above or drag and drop here to initiate 3x distributed replication across online nodes.
          </p>
          <div class="state-action-row">
            <button type="button" id="btn-empty-upload" title="${uploadBtnTitle}" ${uploadBtnDisabled} style="font-size: var(--text-xs); padding: var(--space-1) var(--space-3); ${uploadBtnStyle}">Upload First File</button>
          </div>
        </div>
      </div>
    </section>
  `;
}

export function renderFilePanelError(errorMsg?: string): string {
  const message = errorMsg || 'Unable to retrieve file ledger: Coordinator at port 8000 is unreachable or storage replica index is unavailable.';
  return `
    <section class="zone-file-panel" id="zone-file-panel" aria-label="Replicated File Inventory">
      <div class="zone-header">
        <div class="zone-title-group">
          <h2 class="zone-title">Replicated Storage</h2>
          <span class="zone-count font-mono text-down" id="file-panel-count">(LEDGER OFFLINE)</span>
        </div>
        <span class="zone-caption text-down">Storage index query error</span>
      </div>

      <div class="state-panel error-state-panel" id="file-panel-error">
        <div class="state-header-group">
          <span class="badge badge-down">REPLICA ERROR</span>
          <h3 class="state-title">Storage Ledger Unreachable</h3>
        </div>
        <p class="state-message">
          ${message}
        </p>
        <div class="state-action-row">
          <button type="button" id="btn-retry-files" style="font-size: var(--text-xs); padding: var(--space-1) var(--space-3); border-color: var(--color-down-border);">Retry Ledger Query</button>
        </div>
      </div>
    </section>
  `;
}

export function renderFilePanel(
  files: FileInfo[] = [],
  viewState: ViewState = 'normal',
  errorMessage?: string,
  totalFiles?: number,
  totalSizeBytes?: number,
  searchQuery: string = '',
  uploadState?: UploadState | null,
  downloadState?: DownloadState | null,
  deleteState?: DeleteState | null,
  nodes?: Array<{ id: string; status?: string; state?: string; displayName?: string }>,
  clusterState?: string | null
): string {
  if (viewState === 'loading') return renderFilePanelSkeleton();
  if (viewState === 'empty') return renderFilePanelEmpty(uploadState, downloadState, deleteState, clusterState);
  if (viewState === 'error') return renderFilePanelError(errorMessage);

  const effTotalFiles = totalFiles !== undefined ? totalFiles : files.length;
  const effTotalBytes = totalSizeBytes !== undefined ? totalSizeBytes : files.reduce((acc, f) => acc + f.size, 0);
  const totalSizeFormatted = formatBytes(effTotalBytes);

  let rowsHtml = '';
  if (files.length === 0) {
    if (searchQuery.trim().length > 0) {
      rowsHtml = `
        <tr>
          <td colspan="6" style="text-align: center; color: var(--color-muted); padding: var(--space-4); font-size: var(--text-xs);" class="font-mono">
            No files matching "${searchQuery}"
          </td>
        </tr>
      `;
    } else {
      return renderFilePanelEmpty(uploadState, downloadState, deleteState, clusterState);
    }
  } else {
    rowsHtml = files.map(file => renderFileRow(file, downloadState, deleteState, nodes, clusterState)).join('');
  }

  const bannerHtml = renderClusterNoticeBanner(clusterState);
  const uploadHtml = renderUploadProgress(uploadState);
  const downloadHtml = renderDownloadError(downloadState);
  const deleteHtml = renderDeleteError(deleteState);

  const isConsensusPaused = clusterState === 'NO MAJORITY';
  const uploadBtnTitle = isConsensusPaused ? 'Uploads paused: Quorum majority lost (< 2/3 nodes active)' : 'Upload file to cluster';
  const uploadBtnDisabled = isConsensusPaused ? 'disabled' : '';
  const uploadBtnStyle = isConsensusPaused ? 'opacity: 0.5; cursor: not-allowed;' : 'background-color: var(--color-surface-hover); border-color: var(--color-line-bright);';
  const dropOverlaySubtitle = isConsensusPaused ? 'Consensus paused: File uploads temporarily paused until quorum restored' : 'Release file to initiate 3x distributed replication';

  return `
    <section class="zone-file-panel" id="zone-file-panel" aria-label="Replicated File Inventory">
      <div class="zone-header">
        <div class="zone-title-group">
          <h2 class="zone-title">Replicated Storage</h2>
          <span class="zone-count font-mono" id="file-panel-count">(${effTotalFiles} FILES &bull; ${totalSizeFormatted})</span>
        </div>
        <span class="zone-caption">3x Target Replication Factor</span>
      </div>

      <div id="cluster-notice-slot">
        ${bannerHtml}
      </div>

      <div class="file-panel-toolbar">
        <div style="display: flex; gap: var(--space-2); flex: 1;">
          <input
            type="search"
            id="file-search-input"
            placeholder="Filter filename..."
            value="${searchQuery}"
            style="width: 100%; max-width: 240px; font-size: var(--text-xs);"
            aria-label="Filter files"
          >
        </div>
        <div style="display: flex; gap: var(--space-2);">
          <button type="button" id="btn-trigger-sync" style="font-size: var(--text-xs); padding: var(--space-1) var(--space-2-5);">Trigger Sync</button>
          <button type="button" id="btn-upload-file" title="${uploadBtnTitle}" ${uploadBtnDisabled} style="font-size: var(--text-xs); padding: var(--space-1) var(--space-2-5); ${uploadBtnStyle}">Upload File</button>
        </div>
      </div>

      <input type="file" id="file-upload-input" style="display: none;" aria-hidden="true">

      <div class="upload-status-slot" id="upload-status-slot">
        ${uploadHtml}
        ${downloadHtml}
        ${deleteHtml}
      </div>

      <div class="file-dropzone" id="file-dropzone">
        <div class="file-drop-overlay" id="file-drop-overlay" aria-hidden="true">
          <span class="badge ${isConsensusPaused ? 'badge-down' : 'badge-ok'}"><span class="status-dot ${isConsensusPaused ? 'dot-down' : 'dot-ok'}"></span> ${isConsensusPaused ? 'CONSENSUS PAUSED' : 'DROP TO REPLICATE'}</span>
          <span class="font-sans text-xs text-ink" style="margin-top: 4px;">${dropOverlaySubtitle}</span>
        </div>

        <div class="file-table-container">
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Size</th>
                <th>Status</th>
                <th>Replicas</th>
                <th>Modified</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody id="file-table-tbody">
              ${rowsHtml}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  `;
}

/**
 * High-performance in-place DOM updater for Zone 3 File Panel.
 * Updates file rows, counts, and upload/download progress without losing search input focus or resetting page DOM.
 */
export function updateFilePanelDOM(
  files: FileInfo[],
  totalFiles?: number,
  totalSizeBytes?: number,
  searchQuery: string = '',
  uploadState?: UploadState | null,
  downloadState?: DownloadState | null,
  deleteState?: DeleteState | null,
  nodes?: Array<{ id: string; status?: string; state?: string; displayName?: string }>,
  clusterState?: string | null
): void {
  const tbody = document.getElementById('file-table-tbody');
  const countEl = document.getElementById('file-panel-count');
  const searchInput = document.getElementById('file-search-input') as HTMLInputElement | null;
  const statusSlot = document.getElementById('upload-status-slot');
  const noticeSlot = document.getElementById('cluster-notice-slot');

  if (!tbody || !countEl) {
    const root = document.getElementById('file-panel-root');
    if (root) {
      root.innerHTML = renderFilePanel(files, 'normal', undefined, totalFiles, totalSizeBytes, searchQuery, uploadState, downloadState, deleteState, nodes, clusterState);
    }
    return;
  }

  const effTotalFiles = totalFiles !== undefined ? totalFiles : files.length;
  const effTotalBytes = totalSizeBytes !== undefined ? totalSizeBytes : files.reduce((acc, f) => acc + f.size, 0);

  countEl.textContent = `(${effTotalFiles} FILES • ${formatBytes(effTotalBytes)})`;

  if (searchInput && searchInput !== document.activeElement && searchInput.value !== searchQuery) {
    searchInput.value = searchQuery;
  }

  if (noticeSlot) {
    noticeSlot.innerHTML = renderClusterNoticeBanner(clusterState);
  }

  const uploadBtn = document.getElementById('btn-upload-file') as HTMLButtonElement | null;
  if (uploadBtn) {
    const isConsensusPaused = clusterState === 'NO MAJORITY';
    uploadBtn.disabled = isConsensusPaused;
    uploadBtn.title = isConsensusPaused
      ? 'Uploads paused: Quorum majority lost (< 2/3 nodes active)'
      : 'Upload file to cluster';
    uploadBtn.style.opacity = isConsensusPaused ? '0.5' : '1';
    uploadBtn.style.cursor = isConsensusPaused ? 'not-allowed' : 'pointer';
  }

  if (statusSlot) {
    const uploadHtml = renderUploadProgress(uploadState);
    const downloadHtml = renderDownloadError(downloadState);
    const deleteHtml = renderDeleteError(deleteState);
    statusSlot.innerHTML = `${uploadHtml}${downloadHtml}${deleteHtml}`;
  }

  if (files.length === 0) {
    if (searchQuery.trim().length > 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; color: var(--color-muted); padding: var(--space-4); font-size: var(--text-xs);" class="font-mono">
            No files matching "${searchQuery}"
          </td>
        </tr>
      `;
    } else {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; color: var(--color-muted); padding: var(--space-4); font-size: var(--text-xs);">
            No files stored in cluster.
          </td>
        </tr>
      `;
    }
    return;
  }

  tbody.innerHTML = files.map(file => renderFileRow(file, downloadState, deleteState, nodes, clusterState)).join('');
}
