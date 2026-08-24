/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Component: FilePanel (Zone 3 Replicated File Storage)
 */

import type { FileInfo } from '../types/api.ts';
import { formatBytes } from '../tokens/index.ts';

export function renderFilePanel(files: FileInfo[] = []): string {
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
