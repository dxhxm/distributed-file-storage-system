/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Component: FilePanel (Zone 3 Replicated File Storage)
 */

import type { FileInfo } from '../types/api.ts';
import { formatBytes } from '../tokens/index.ts';
import type { ViewState } from '../types/components.ts';

export function renderFilePanelSkeleton(): string {
  return `
    <section class="zone-file-panel" id="zone-file-panel" aria-label="Replicated File Inventory">
      <div class="zone-header">
        <div class="zone-title-group">
          <h2 class="zone-title">Replicated Storage</h2>
          <span class="zone-count font-mono">(INDEXING...)</span>
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
          <span class="zone-count font-mono">(0 FILES &bull; 0 B)</span>
        </div>
        <span class="zone-caption">Empty cluster ledger</span>
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
          <span class="zone-count font-mono text-down">(LEDGER OFFLINE)</span>
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
  errorMessage?: string
): string {
  if (viewState === 'loading') return renderFilePanelSkeleton();
  if (viewState === 'empty') return renderFilePanelEmpty();
  if (viewState === 'error') return renderFilePanelError(errorMessage);

  const defaultFiles: FileInfo[] = files.length > 0 ? files : [
    { file_id: '1', name: 'distributed_dataset.tar.gz', size: 1116691497, replicas: ['nodeA', 'nodeB', 'nodeC'], status: 'REPLICATED', modified_at: Date.now() },
    { file_id: '2', name: 'wal_journal_09.log', size: 536870912, replicas: ['nodeA', 'nodeB', 'nodeC'], status: 'REPLICATED', modified_at: Date.now() },
    { file_id: '3', name: 'system_kernel.img', size: 14973824, replicas: ['nodeA', 'nodeB'], status: 'SYNCING', modified_at: Date.now() },
    { file_id: '4', name: 'cluster_config.json', size: 4300, replicas: ['nodeA', 'nodeB'], status: 'DEGRADED', modified_at: Date.now() },
  ];

  const totalFiles = defaultFiles.length;
  const totalBytes = defaultFiles.reduce((acc, f) => acc + f.size, 0);
  const totalSizeFormatted = formatBytes(totalBytes);

  const rowsHtml = defaultFiles.map(file => {
    const isReplicated = file.status === 'REPLICATED';
    const isSyncing = file.status === 'SYNCING';
    const isDegraded = file.status === 'DEGRADED';
    const badgeClass = isReplicated ? 'badge-ok' : (isSyncing || isDegraded) ? 'badge-warn' : 'badge-down';
    const statusText = `${file.status} (${file.replicas.length}/3)`;

    const pillA = file.replicas.includes('nodeA')
      ? `<span class="replica-pill active" title="Replica stored on nodeA">A</span>`
      : `<span class="replica-pill" style="opacity: 0.35;">-</span>`;
    const pillB = file.replicas.includes('nodeB')
      ? `<span class="replica-pill active" title="Replica stored on nodeB">B</span>`
      : `<span class="replica-pill" style="opacity: 0.35;">-</span>`;
    const pillC = file.replicas.includes('nodeC')
      ? `<span class="replica-pill active" title="Replica stored on nodeC">C</span>`
      : (isSyncing
        ? `<span class="replica-pill" style="color: var(--color-warn); border-color: var(--color-warn-border);" title="Syncing to nodeC">C</span>`
        : `<span class="replica-pill" style="opacity: 0.35;" title="Missing on nodeC">-</span>`);

    return `
      <tr>
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
        <td class="font-mono text-xs text-muted">21:40:15 UTC</td>
      </tr>
    `;
  }).join('');

  return `
    <section class="zone-file-panel" id="zone-file-panel" aria-label="Replicated File Inventory">
      <div class="zone-header">
        <div class="zone-title-group">
          <h2 class="zone-title">Replicated Storage</h2>
          <span class="zone-count font-mono">(${totalFiles} FILES &bull; ${totalSizeFormatted})</span>
        </div>
        <span class="zone-caption">3x Target Replication Factor</span>
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
            ${rowsHtml}
          </tbody>
        </table>
      </div>
    </section>
  `;
}
