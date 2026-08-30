/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Component: FilePanel (Zone 3 Replicated File Storage)
 */

import type { FileInfo } from '../types/api.ts';
import { formatBytes } from '../tokens/index.ts';
import { formatTimeUTC } from './NodeList.ts';
import type { ViewState } from '../types/components.ts';

export function hasReplica(replicas: string[] = [], targetNode: 'A' | 'B' | 'C'): boolean {
  return replicas.some(r => {
    const clean = r.toLowerCase().replace(/\s+/g, '').replace(/^node/i, '');
    if (targetNode === 'A') return clean === 'a' || clean === '1';
    if (targetNode === 'B') return clean === 'b' || clean === '2';
    if (targetNode === 'C') return clean === 'c' || clean === '3';
    return false;
  });
}

export function renderFileRow(file: FileInfo): string {
  const isReplicated = file.status === 'REPLICATED';
  const isSyncing = file.status === 'SYNCING';
  const isDegraded = file.status === 'DEGRADED';
  const badgeClass = isReplicated ? 'badge-ok' : (isSyncing || isDegraded) ? 'badge-warn' : 'badge-down';
  const statusText = `${file.status} (${file.replicas.length}/3)`;

  const hasA = hasReplica(file.replicas, 'A');
  const hasB = hasReplica(file.replicas, 'B');
  const hasC = hasReplica(file.replicas, 'C');

  const pillA = hasA
    ? `<span class="replica-pill active" title="Replica stored on Node A">A</span>`
    : `<span class="replica-pill" style="opacity: 0.35;">-</span>`;
  const pillB = hasB
    ? `<span class="replica-pill active" title="Replica stored on Node B">B</span>`
    : `<span class="replica-pill" style="opacity: 0.35;">-</span>`;
  const pillC = hasC
    ? `<span class="replica-pill active" title="Replica stored on Node C">C</span>`
    : (isSyncing
      ? `<span class="replica-pill" style="color: var(--color-warn); border-color: var(--color-warn-border);" title="Syncing to Node C">C</span>`
      : `<span class="replica-pill" style="opacity: 0.35;" title="Missing on Node C">-</span>`);

  const timeStr = file.modified_at ? formatTimeUTC(file.modified_at) : '21:40:15 UTC';

  return `
    <tr class="file-row" id="file-row-${file.file_id || encodeURIComponent(file.name)}">
      <td class="font-mono text-ink">${file.name}</td>
      <td class="font-mono">${formatBytes(file.size)}</td>
      <td><span class="badge ${badgeClass}">${statusText}</span></td>
      <td>
        <div class="replica-pills">
          ${pillA}
          ${pillB}
          ${pillC}
        </div>
      </td>
      <td class="font-mono text-xs text-muted">${timeStr}</td>
    </tr>
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

      <div class="file-table-container">
        <table>
          <thead>
            <tr>
              <th>Filename</th>
              <th>Size</th>
              <th>Status</th>
              <th>Replicas</th>
              <th>Modified</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><span class="skeleton-bar" style="width: 140px;"></span></td>
              <td><span class="skeleton-bar" style="width: 60px;"></span></td>
              <td><span class="skeleton-bar" style="width: 80px;"></span></td>
              <td><span class="skeleton-bar" style="width: 50px;"></span></td>
              <td><span class="skeleton-bar" style="width: 75px;"></span></td>
            </tr>
            <tr>
              <td><span class="skeleton-bar" style="width: 120px;"></span></td>
              <td><span class="skeleton-bar" style="width: 55px;"></span></td>
              <td><span class="skeleton-bar" style="width: 80px;"></span></td>
              <td><span class="skeleton-bar" style="width: 50px;"></span></td>
              <td><span class="skeleton-bar" style="width: 75px;"></span></td>
            </tr>
            <tr>
              <td><span class="skeleton-bar" style="width: 160px;"></span></td>
              <td><span class="skeleton-bar" style="width: 70px;"></span></td>
              <td><span class="skeleton-bar" style="width: 80px;"></span></td>
              <td><span class="skeleton-bar" style="width: 50px;"></span></td>
              <td><span class="skeleton-bar" style="width: 75px;"></span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  `;
}

export function renderFilePanelEmpty(): string {
  return `
    <section class="zone-file-panel" id="zone-file-panel" aria-label="Replicated File Inventory">
      <div class="zone-header">
        <div class="zone-title-group">
          <h2 class="zone-title">Replicated Storage</h2>
          <span class="zone-count font-mono" id="file-panel-count">(0 FILES &bull; 0 B)</span>
        </div>
        <span class="zone-caption">Empty cluster ledger</span>
      </div>

      <div class="file-panel-toolbar">
        <div style="display: flex; gap: var(--space-2); flex: 1;">
          <input type="search" id="file-search-input" placeholder="Filter filename..." style="width: 100%; max-width: 240px; font-size: var(--text-xs);" aria-label="Filter files">
        </div>
        <div style="display: flex; gap: var(--space-2);">
          <button id="btn-trigger-sync" style="font-size: var(--text-xs); padding: var(--space-1) var(--space-2-5);">Trigger Sync</button>
          <button id="btn-upload-file" style="font-size: var(--text-xs); padding: var(--space-1) var(--space-2-5); background-color: var(--color-surface-hover); border-color: var(--color-line-bright);">Upload File</button>
        </div>
      </div>

      <div class="state-panel empty-state-panel" id="file-panel-empty">
        <div class="state-header-group">
          <span class="badge badge-info">STORAGE EMPTY</span>
          <h3 class="state-title">No Files Stored in Cluster</h3>
        </div>
        <p class="state-message">
          No files stored in cluster. Upload a file above to initiate 3x distributed replication across online nodes.
        </p>
        <div class="state-action-row">
          <button id="btn-empty-upload" style="font-size: var(--text-xs); padding: var(--space-1) var(--space-3); background-color: var(--color-surface-hover); border-color: var(--color-line-bright);">Upload First File</button>
        </div>
      </div>
    </section>
  `;
}

export function renderFilePanelError(errorMsg?: string): string {
  const message = errorMsg || 'Unable to retrieve file ledger. Storage replica index unavailable or quorum lost.';
  return `
    <section class="zone-file-panel" id="zone-file-panel" aria-label="Replicated File Inventory">
      <div class="zone-header">
        <div class="zone-title-group">
          <h2 class="zone-title">Replicated Storage</h2>
          <span class="zone-count font-mono text-down" id="file-panel-count">(LEDGER OFFLINE)</span>
        </div>
        <span class="zone-caption text-down">Index query error</span>
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
          <button id="btn-retry-files" style="font-size: var(--text-xs); padding: var(--space-1) var(--space-3); border-color: var(--color-down-border);">Retry Ledger Query</button>
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
  searchQuery: string = ''
): string {
  if (viewState === 'loading') return renderFilePanelSkeleton();
  if (viewState === 'empty') return renderFilePanelEmpty();
  if (viewState === 'error') return renderFilePanelError(errorMessage);

  const effTotalFiles = totalFiles !== undefined ? totalFiles : files.length;
  const effTotalBytes = totalSizeBytes !== undefined ? totalSizeBytes : files.reduce((acc, f) => acc + f.size, 0);
  const totalSizeFormatted = formatBytes(effTotalBytes);

  let rowsHtml = '';
  if (files.length === 0) {
    if (searchQuery.trim().length > 0) {
      rowsHtml = `
        <tr>
          <td colspan="5" style="text-align: center; color: var(--color-muted); padding: var(--space-4); font-size: var(--text-xs);" class="font-mono">
            No files matching "${searchQuery}"
          </td>
        </tr>
      `;
    } else {
      return renderFilePanelEmpty();
    }
  } else {
    rowsHtml = files.map(file => renderFileRow(file)).join('');
  }

  return `
    <section class="zone-file-panel" id="zone-file-panel" aria-label="Replicated File Inventory">
      <div class="zone-header">
        <div class="zone-title-group">
          <h2 class="zone-title">Replicated Storage</h2>
          <span class="zone-count font-mono" id="file-panel-count">(${effTotalFiles} FILES &bull; ${totalSizeFormatted})</span>
        </div>
        <span class="zone-caption">3x Target Replication Factor</span>
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
          <button type="button" id="btn-upload-file" style="font-size: var(--text-xs); padding: var(--space-1) var(--space-2-5); background-color: var(--color-surface-hover); border-color: var(--color-line-bright);">Upload File</button>
        </div>
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
            </tr>
          </thead>
          <tbody id="file-table-tbody">
            ${rowsHtml}
          </tbody>
        </table>
      </div>
    </section>
  `;
}

/**
 * High-performance in-place DOM updater for Zone 3 File Panel.
 * Updates file rows and counts without losing search input focus or resetting page DOM.
 */
export function updateFilePanelDOM(
  files: FileInfo[],
  totalFiles?: number,
  totalSizeBytes?: number,
  searchQuery: string = ''
): void {
  const tbody = document.getElementById('file-table-tbody');
  const countEl = document.getElementById('file-panel-count');
  const searchInput = document.getElementById('file-search-input') as HTMLInputElement | null;

  if (!tbody || !countEl) {
    const root = document.getElementById('file-panel-root');
    if (root) {
      root.innerHTML = renderFilePanel(files, 'normal', undefined, totalFiles, totalSizeBytes, searchQuery);
    }
    return;
  }

  const effTotalFiles = totalFiles !== undefined ? totalFiles : files.length;
  const effTotalBytes = totalSizeBytes !== undefined ? totalSizeBytes : files.reduce((acc, f) => acc + f.size, 0);

  countEl.textContent = `(${effTotalFiles} FILES • ${formatBytes(effTotalBytes)})`;

  if (searchInput && searchInput !== document.activeElement && searchInput.value !== searchQuery) {
    searchInput.value = searchQuery;
  }

  if (files.length === 0) {
    if (searchQuery.trim().length > 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; color: var(--color-muted); padding: var(--space-4); font-size: var(--text-xs);" class="font-mono">
            No files matching "${searchQuery}"
          </td>
        </tr>
      `;
    } else {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; color: var(--color-muted); padding: var(--space-4); font-size: var(--text-xs);">
            No files stored in cluster.
          </td>
        </tr>
      `;
    }
    return;
  }

  tbody.innerHTML = files.map(file => renderFileRow(file)).join('');
}
