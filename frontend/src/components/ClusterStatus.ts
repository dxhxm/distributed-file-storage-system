/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Component: ClusterStatus (Zone 1 Header)
 */

import type { ClusterStatusResponse } from '../types/api.ts';
import type { ConnectivityStatus } from '../services/healthService.ts';
import type { ViewState } from '../types/components.ts';
import {
  renderClusterHealthIndicator,
  renderClusterHealthSkeleton,
  renderClusterHealthEmpty,
  renderClusterHealthError,
  updateClusterHealthIndicatorDOM,
} from './ClusterHealthIndicator.ts';

export function renderClusterStatusSkeleton(): string {
  return `
    <div class="cluster-header-strip" id="cluster-header-strip">
      <div class="cluster-title-group">
        <h1 class="cluster-brand">DFSS</h1>
        <span class="cluster-subtitle">Distributed Fault-Tolerant File Storage System</span>
      </div>

      <div class="cluster-telemetry-strip">
        ${renderClusterHealthSkeleton()}
        <div class="telemetry-divider" aria-hidden="true"></div>
        <div class="telemetry-item">
          <span class="telemetry-label">Term</span>
          <span class="skeleton-bar" style="width: 30px;"></span>
        </div>
        <div class="telemetry-divider" aria-hidden="true"></div>
        <div class="telemetry-item">
          <span class="telemetry-label">Commit</span>
          <span class="skeleton-bar" style="width: 45px;"></span>
        </div>
        <div class="telemetry-divider" aria-hidden="true"></div>
        <div class="telemetry-item">
          <span class="telemetry-label">Quorum</span>
          <span class="skeleton-bar" style="width: 35px;"></span>
        </div>
        <div class="telemetry-divider" aria-hidden="true"></div>
        <div class="telemetry-item">
          <span class="telemetry-label">Storage</span>
          <span class="skeleton-bar" style="width: 110px;"></span>
        </div>
        <div class="telemetry-divider" aria-hidden="true"></div>
        <div class="telemetry-item">
          <span class="skeleton-bar" style="width: 70px;"></span>
        </div>
      </div>
    </div>
  `;
}

export function renderClusterStatusEmpty(): string {
  return `
    <div class="cluster-header-strip" id="cluster-header-strip">
      <div class="cluster-title-group">
        <h1 class="cluster-brand">DFSS</h1>
        <span class="cluster-subtitle">Distributed Fault-Tolerant File Storage System</span>
      </div>

      <div class="cluster-telemetry-strip">
        ${renderClusterHealthEmpty()}
        <div class="telemetry-divider" aria-hidden="true"></div>
        <div class="telemetry-item">
          <span class="telemetry-label">Term</span>
          <span class="telemetry-value text-muted">#0</span>
        </div>
        <div class="telemetry-divider" aria-hidden="true"></div>
        <div class="telemetry-item">
          <span class="telemetry-label">Commit</span>
          <span class="telemetry-value text-muted">#0</span>
        </div>
        <div class="telemetry-divider" aria-hidden="true"></div>
        <div class="telemetry-item">
          <span class="telemetry-label">Quorum</span>
          <span class="telemetry-value text-warn">0/3</span>
        </div>
        <div class="telemetry-divider" aria-hidden="true"></div>
        <div class="telemetry-item">
          <span class="telemetry-label">Storage</span>
          <span class="telemetry-value text-muted">0 B / 10.00 GB</span>
        </div>
        <div class="telemetry-divider" aria-hidden="true"></div>
        <div class="telemetry-item">
          <span class="badge badge-warn"><span class="status-dot dot-warn"></span> AWAITING PEERS</span>
        </div>
      </div>
    </div>
  `;
}

export function renderClusterStatusError(errorMsg?: string): string {
  const message = errorMsg || 'Connection refused to coordinator on port 8000. 0/3 nodes reporting.';
  return `
    <div class="cluster-header-strip" id="cluster-header-strip">
      <div class="cluster-title-group">
        <h1 class="cluster-brand">DFSS</h1>
        <span class="cluster-subtitle">Distributed Fault-Tolerant File Storage System</span>
      </div>

      <div class="cluster-telemetry-strip">
        ${renderClusterHealthError()}
        <div class="telemetry-divider" aria-hidden="true"></div>
        <div class="telemetry-item">
          <span class="telemetry-label">Quorum</span>
          <span class="telemetry-value text-down">0/3 (NO MAJORITY)</span>
        </div>
        <div class="telemetry-divider" aria-hidden="true"></div>
        <div class="telemetry-item" id="backend-connectivity-item">
          <span class="badge badge-down" title="${message}"><span class="status-dot dot-down"></span> OFFLINE</span>
        </div>
      </div>
    </div>
  `;
}

export function renderClusterStatus(
  status: ClusterStatusResponse | null,
  connectivity: ConnectivityStatus = 'CONNECTED',
  latencyMs: number = 0,
  viewState: ViewState = 'normal',
  errorMessage?: string
): string {
  if (viewState === 'loading') return renderClusterStatusSkeleton();
  if (viewState === 'empty') return renderClusterStatusEmpty();
  if (viewState === 'error') return renderClusterStatusError(errorMessage);

  const clusterState = status?.cluster_state ?? 'HEALTHY';
  const leaderId = status ? (status.leader_id ?? 'NONE') : 'nodeA';
  const term = status?.term ?? 4;
  const commitIndex = status?.commit_index ?? 1042;
  const activeNodes = status?.active_nodes ?? 3;
  const totalNodes = status?.total_nodes ?? 3;

  const isHealthy = clusterState === 'HEALTHY';
  const quorumClass = isHealthy ? 'text-ok' : clusterState === 'OPERATIONAL' ? 'text-warn' : 'text-down';

  const connBadge = connectivity === 'CONNECTED'
    ? `<span class="badge badge-ok" title="Backend reached (+${latencyMs}ms)"><span class="status-dot dot-ok"></span> API LIVE</span>`
    : connectivity === 'DEGRADED'
    ? `<span class="badge badge-warn"><span class="status-dot dot-warn"></span> HIGH LATENCY</span>`
    : `<span class="badge badge-down"><span class="status-dot dot-down"></span> OFFLINE</span>`;

  return `
    <div class="cluster-header-strip" id="cluster-header-strip">
      <div class="cluster-title-group">
        <h1 class="cluster-brand">DFSS</h1>
        <span class="cluster-subtitle">Distributed Fault-Tolerant File Storage System</span>
      </div>

      <div class="cluster-telemetry-strip">
        ${renderClusterHealthIndicator(clusterState, leaderId, viewState)}

        <div class="telemetry-divider" aria-hidden="true"></div>

        <div class="telemetry-item">
          <span class="telemetry-label">Term</span>
          <span class="telemetry-value" id="cluster-term-val">#${term}</span>
        </div>

        <div class="telemetry-divider" aria-hidden="true"></div>

        <div class="telemetry-item">
          <span class="telemetry-label">Commit</span>
          <span class="telemetry-value" id="cluster-commit-val">#${commitIndex}</span>
        </div>

        <div class="telemetry-divider" aria-hidden="true"></div>

        <div class="telemetry-item">
          <span class="telemetry-label">Quorum</span>
          <span class="telemetry-value ${quorumClass}" id="cluster-quorum-val">${activeNodes}/${totalNodes}</span>
        </div>

        <div class="telemetry-divider" aria-hidden="true"></div>

        <div class="telemetry-item">
          <span class="telemetry-label">Storage</span>
          <span class="telemetry-value">1.57 GB / 10.00 GB</span>
        </div>

        <div class="telemetry-divider" aria-hidden="true"></div>

        <div class="telemetry-item" id="backend-connectivity-item">
          ${connBadge}
        </div>
      </div>
    </div>
  `;
}

/**
 * High-performance in-place DOM updater for Zone 1 cluster telemetry.
 * Avoids DOM re-creation and flickering during high-frequency polling.
 */
export function updateClusterStatusDOM(
  status: ClusterStatusResponse | null,
  connectivity: ConnectivityStatus = 'CONNECTED',
  latencyMs: number = 0
): void {
  const termEl = document.getElementById('cluster-term-val');
  const commitEl = document.getElementById('cluster-commit-val');
  const quorumEl = document.getElementById('cluster-quorum-val');
  const connEl = document.getElementById('backend-connectivity-item');

  if (!termEl || !commitEl || !quorumEl) {
    // If element structure is missing (e.g. state switch), re-render container
    const root = document.getElementById('cluster-status-root');
    if (root) {
      root.innerHTML = renderClusterStatus(status, connectivity, latencyMs, 'normal');
    }
    return;
  }

  const clusterState = status?.cluster_state ?? 'HEALTHY';
  const leaderId = status ? (status.leader_id ?? 'NONE') : 'nodeA';
  const term = status?.term ?? 4;
  const commitIndex = status?.commit_index ?? 1042;
  const activeNodes = status?.active_nodes ?? 3;
  const totalNodes = status?.total_nodes ?? 3;

  // In-place update of the primary health indicator and leader
  updateClusterHealthIndicatorDOM(clusterState, leaderId);

  const isHealthy = clusterState === 'HEALTHY';
  const quorumClass = isHealthy ? 'text-ok' : clusterState === 'OPERATIONAL' ? 'text-warn' : 'text-down';

  termEl.textContent = `#${term}`;
  commitEl.textContent = `#${commitIndex}`;

  quorumEl.className = `telemetry-value ${quorumClass}`;
  quorumEl.textContent = `${activeNodes}/${totalNodes}`;

  if (connEl) {
    const connBadge = connectivity === 'CONNECTED'
      ? `<span class="badge badge-ok" title="Backend reached (+${latencyMs}ms)"><span class="status-dot dot-ok"></span> API LIVE</span>`
      : connectivity === 'DEGRADED'
      ? `<span class="badge badge-warn"><span class="status-dot dot-warn"></span> HIGH LATENCY</span>`
      : `<span class="badge badge-down"><span class="status-dot dot-down"></span> OFFLINE</span>`;
    connEl.innerHTML = connBadge;
  }
}


