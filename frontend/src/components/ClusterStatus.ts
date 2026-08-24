/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Component: ClusterStatus (Zone 1 Header)
 */

import type { ClusterStatusResponse } from '../types/api.ts';
import type { ConnectivityStatus } from '../services/healthService.ts';
import type { ViewState } from '../types/components.ts';

export function renderClusterStatusSkeleton(): string {
  return `
    <div class="cluster-header-strip" id="cluster-header-strip">
      <div class="cluster-title-group">
        <h1 class="cluster-brand">DFSS</h1>
        <span class="cluster-subtitle">Distributed Fault-Tolerant File Storage System</span>
      </div>

      <div class="cluster-telemetry-strip">
        <div class="telemetry-item">
          <span class="telemetry-label">Status</span>
          <span class="skeleton-bar" style="width: 80px;"></span>
        </div>
        <div class="telemetry-divider" aria-hidden="true"></div>
        <div class="telemetry-item">
          <span class="telemetry-label">Leader</span>
          <span class="skeleton-bar" style="width: 50px;"></span>
        </div>
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
        <div class="telemetry-item">
          <span class="telemetry-label">Status</span>
          <span class="badge badge-warn">
            <span class="status-dot dot-warn"></span> BOOTSTRAPPING
          </span>
        </div>
        <div class="telemetry-divider" aria-hidden="true"></div>
        <div class="telemetry-item">
          <span class="telemetry-label">Leader</span>
          <span class="telemetry-value text-muted">NONE</span>
        </div>
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
        <div class="telemetry-item">
          <span class="telemetry-label">Status</span>
          <span class="badge badge-down" id="cluster-state-badge">
            <span class="status-dot dot-down"></span> DISCONNECTED
          </span>
        </div>
        <div class="telemetry-divider" aria-hidden="true"></div>
        <div class="telemetry-item">
          <span class="telemetry-label">Leader</span>
          <span class="telemetry-value text-down">UNAVAILABLE</span>
        </div>
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
  const leaderId = status?.leader_id ?? 'nodeA';
  const term = status?.term ?? 4;
  const commitIndex = status?.commit_index ?? 1042;
  const activeNodes = status?.active_nodes ?? 3;
  const totalNodes = status?.total_nodes ?? 3;

  const isHealthy = clusterState === 'HEALTHY';
  const badgeClass = isHealthy ? 'badge-ok' : clusterState === 'OPERATIONAL' ? 'badge-warn' : 'badge-down';
  const dotClass = isHealthy ? 'dot-ok' : clusterState === 'OPERATIONAL' ? 'dot-warn' : 'dot-down';

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
        <div class="telemetry-item">
          <span class="telemetry-label">Status</span>
          <span class="badge ${badgeClass}" id="cluster-state-badge">
            <span class="status-dot ${dotClass}"></span> ${clusterState}
          </span>
        </div>

        <div class="telemetry-divider" aria-hidden="true"></div>

        <div class="telemetry-item">
          <span class="telemetry-label">Leader</span>
          <span class="telemetry-value text-ok" id="cluster-leader-val">${leaderId}</span>
        </div>

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
          <span class="telemetry-value text-ok" id="cluster-quorum-val">${activeNodes}/${totalNodes}</span>
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
