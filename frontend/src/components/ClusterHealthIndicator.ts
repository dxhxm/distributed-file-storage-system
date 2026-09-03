/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Component: ClusterHealthIndicator (Primary Health & Leader Telemetry)
 *
 * Locked Design Language:
 * - Low-saturation earth/slate tones (Zero neon, zero traffic-light saturation)
 * - Single accent shift carries the meaning:
 *   - HEALTHY: Muted Forest Green (#5FB88A)
 *   - OPERATIONAL: Muted Amber (#D9A441)
 *   - NO MAJORITY: Muted Terracotta/Crimson (#C15B4A)
 * - Leader node ID prominently coupled beside the status indicator
 * - Flash-free in-place DOM transitions
 */

import type { ClusterState } from '../types/api.ts';
import type { ViewState } from '../types/components.ts';

export interface HealthIndicatorStyle {
  clusterState: ClusterState | string;
  badgeClass: string;
  dotClass: string;
  leaderClass: string;
  displayLeader: string;
  tooltip: string;
  explanation: string;
}

/**
 * Resolves token styling and leader presentation for any cluster consensus state.
 */
export function resolveHealthIndicatorStyle(
  state: ClusterState | string | null | undefined,
  leaderId: string | null | undefined
): HealthIndicatorStyle {
  const normalizedState = state ?? 'HEALTHY';
  const hasLeader = leaderId && leaderId.trim() !== '' && leaderId !== 'NONE';

  if (normalizedState === 'HEALTHY') {
    return {
      clusterState: 'HEALTHY',
      badgeClass: 'badge-ok',
      dotClass: 'dot-ok',
      leaderClass: hasLeader ? 'text-ok' : 'text-muted',
      displayLeader: leaderId || 'NONE',
      tooltip: 'Consensus quorum healthy: All nodes responding and log replication active.',
      explanation: 'Quorum Healthy',
    };
  }

  if (normalizedState === 'OPERATIONAL') {
    return {
      clusterState: 'OPERATIONAL',
      badgeClass: 'badge-warn',
      dotClass: 'dot-warn',
      leaderClass: hasLeader ? 'text-ok' : 'text-muted',
      displayLeader: leaderId || 'NONE',
      tooltip: 'Quorum Degraded: 1 node offline (2/3 active). Consensus operations continue with remaining failure tolerance 0.',
      explanation: 'Quorum Degraded (Single fault tolerance remaining)',
    };
  }

  if (normalizedState === 'NO MAJORITY') {
    return {
      clusterState: 'NO MAJORITY',
      badgeClass: 'badge-down',
      dotClass: 'dot-down',
      leaderClass: 'text-muted',
      displayLeader: leaderId || 'NONE',
      tooltip: 'Consensus Paused: Quorum majority lost (< 2/3 nodes active). Election and state machine replication paused until peers reconnect. Active nodes serve local reads.',
      explanation: 'Consensus Paused (Quorum Lost — Not System Down)',
    };
  }

  // Fallback / Disconnected
  return {
    clusterState: normalizedState,
    badgeClass: 'badge-down',
    dotClass: 'dot-down',
    leaderClass: 'text-muted',
    displayLeader: leaderId || 'UNAVAILABLE',
    tooltip: 'Coordinator Unreachable: Cannot connect to nodeA on port 8000. Ensure node processes are running.',
    explanation: 'Coordinator Unreachable',
  };
}

/**
 * Renders the health indicator skeleton for initial loading.
 */
export function renderClusterHealthSkeleton(): string {
  return `
    <div class="health-indicator-group" id="cluster-health-indicator" role="status" aria-live="polite">
      <div class="telemetry-item health-status-item">
        <span class="telemetry-label">Status</span>
        <span class="skeleton-bar" style="width: 84px; height: 18px;"></span>
      </div>
      <div class="telemetry-divider" aria-hidden="true"></div>
      <div class="telemetry-item health-leader-item" id="cluster-leader-group">
        <span class="telemetry-label">Leader</span>
        <span class="skeleton-bar" style="width: 54px; height: 18px;"></span>
      </div>
    </div>
  `;
}

/**
 * Renders the health indicator for empty / bootstrapping state.
 */
export function renderClusterHealthEmpty(): string {
  return `
    <div class="health-indicator-group" id="cluster-health-indicator" role="status" aria-live="polite">
      <div class="telemetry-item health-status-item">
        <span class="telemetry-label">Status</span>
        <span class="badge badge-warn" id="cluster-state-badge">
          <span class="status-dot dot-warn" aria-hidden="true"></span>
          <span id="cluster-state-label">BOOTSTRAPPING</span>
        </span>
      </div>
      <div class="telemetry-divider" aria-hidden="true"></div>
      <div class="telemetry-item health-leader-item" id="cluster-leader-group">
        <span class="telemetry-label">Leader</span>
        <span class="telemetry-value text-muted" id="cluster-leader-val">NONE</span>
      </div>
    </div>
  `;
}

/**
 * Renders the health indicator for error / disconnected state.
 */
export function renderClusterHealthError(): string {
  return `
    <div class="health-indicator-group" id="cluster-health-indicator" role="status" aria-live="polite">
      <div class="telemetry-item health-status-item">
        <span class="telemetry-label">Status</span>
        <span class="badge badge-down" id="cluster-state-badge">
          <span class="status-dot dot-down" aria-hidden="true"></span>
          <span id="cluster-state-label">DISCONNECTED</span>
        </span>
      </div>
      <div class="telemetry-divider" aria-hidden="true"></div>
      <div class="telemetry-item health-leader-item" id="cluster-leader-group">
        <span class="telemetry-label">Leader</span>
        <span class="telemetry-value text-down" id="cluster-leader-val">UNAVAILABLE</span>
      </div>
    </div>
  `;
}

/**
 * Primary health indicator markup generator.
 */
export function renderClusterHealthIndicator(
  state: ClusterState | string | null | undefined,
  leaderId: string | null | undefined,
  viewState: ViewState = 'normal'
): string {
  if (viewState === 'loading') return renderClusterHealthSkeleton();
  if (viewState === 'empty') return renderClusterHealthEmpty();
  if (viewState === 'error') return renderClusterHealthError();

  const style = resolveHealthIndicatorStyle(state, leaderId);

  return `
    <div class="health-indicator-group" id="cluster-health-indicator" role="status" aria-live="polite">
      <div class="telemetry-item health-status-item">
        <span class="telemetry-label">Status</span>
        <span class="badge ${style.badgeClass} health-status-badge" id="cluster-state-badge" title="${style.tooltip}">
          <span class="status-dot ${style.dotClass}" aria-hidden="true"></span>
          <span id="cluster-state-label">${style.clusterState}</span>
        </span>
      </div>

      <div class="telemetry-divider" aria-hidden="true"></div>

      <div class="telemetry-item health-leader-item" id="cluster-leader-group">
        <span class="telemetry-label">Leader</span>
        <span class="telemetry-value ${style.leaderClass}" id="cluster-leader-val" title="${style.displayLeader === 'NONE' ? 'No leader elected while consensus is paused' : `Current Raft Leader: ${style.displayLeader}`}">${style.displayLeader}</span>
      </div>
    </div>
  `;
}

/**
 * Zero-jank in-place DOM updater for state transitions.
 * Mutates attributes directly to prevent layout thrashing and visual flash.
 */
export function updateClusterHealthIndicatorDOM(
  state: ClusterState | string | null | undefined,
  leaderId: string | null | undefined
): void {
  const badgeEl = document.getElementById('cluster-state-badge');
  const labelEl = document.getElementById('cluster-state-label');
  const leaderValEl = document.getElementById('cluster-leader-val');

  if (!badgeEl || !leaderValEl) {
    const root = document.getElementById('cluster-health-indicator');
    if (root) {
      root.outerHTML = renderClusterHealthIndicator(state, leaderId, 'normal');
    }
    return;
  }

  const style = resolveHealthIndicatorStyle(state, leaderId);

  // Update badge styling classes and tooltip
  badgeEl.className = `badge ${style.badgeClass} health-status-badge`;
  badgeEl.title = style.tooltip;
  if (labelEl) {
    labelEl.textContent = style.clusterState;
    const dot = badgeEl.querySelector('.status-dot');
    if (dot) {
      dot.className = `status-dot ${style.dotClass}`;
    }
  } else {
    badgeEl.innerHTML = `<span class="status-dot ${style.dotClass}" aria-hidden="true"></span><span id="cluster-state-label">${style.clusterState}</span>`;
  }

  // Update leader element and tooltip
  leaderValEl.className = `telemetry-value ${style.leaderClass}`;
  leaderValEl.textContent = style.displayLeader;
  leaderValEl.title = style.displayLeader === 'NONE'
    ? 'No leader elected while consensus is paused'
    : `Current Raft Leader: ${style.displayLeader}`;
}

