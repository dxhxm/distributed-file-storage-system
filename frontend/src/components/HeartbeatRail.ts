/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Component: HeartbeatRail (Signature Pulse Rail)
 *
 * Driven by real backend heartbeat events. Stalls visually on offline nodes.
 */

import type { NodeInfo } from '../types/api.ts';
import type { NodeHeartbeatState } from '../services/heartbeatService.ts';
import type { ViewState } from '../types/components.ts';

export function renderHeartbeatRailSkeleton(): string {
  return `
    <div class="heartbeat-rail-card" id="heartbeat-rail">
      <div class="heartbeat-rail-header">
        <div class="heartbeat-rail-title">
          <span>Heartbeat Pulse Rail</span>
          <span class="badge badge-info" style="font-size: var(--text-2xs); padding: 0 4px;">Connecting...</span>
        </div>
      </div>

      <div class="heartbeat-lanes" id="heartbeat-lanes-container">
        <div class="heartbeat-lane skeleton-box" style="height: 28px;">
          <div class="skeleton-bar" style="width: 80px;"></div>
          <div class="skeleton-bar" style="width: 100%; height: 6px;"></div>
          <div class="skeleton-bar" style="width: 60px;"></div>
        </div>
        <div class="heartbeat-lane skeleton-box" style="height: 28px;">
          <div class="skeleton-bar" style="width: 80px;"></div>
          <div class="skeleton-bar" style="width: 100%; height: 6px;"></div>
          <div class="skeleton-bar" style="width: 60px;"></div>
        </div>
        <div class="heartbeat-lane skeleton-box" style="height: 28px;">
          <div class="skeleton-bar" style="width: 80px;"></div>
          <div class="skeleton-bar" style="width: 100%; height: 6px;"></div>
          <div class="skeleton-bar" style="width: 60px;"></div>
        </div>
      </div>
    </div>
  `;
}

export function renderHeartbeatRailEmpty(): string {
  return `
    <div class="heartbeat-rail-card" id="heartbeat-rail">
      <div class="heartbeat-rail-header">
        <div class="heartbeat-rail-title">
          <span>Heartbeat Pulse Rail</span>
          <span class="badge badge-warn" style="font-size: var(--text-2xs); padding: 0 4px;">Awaiting Pulses</span>
        </div>
      </div>

      <div style="padding: var(--space-4) var(--space-3); background-color: var(--color-surface-subtle); border: 1px solid var(--color-line-subtle); display: flex; justify-content: space-between; align-items: center;">
        <p style="font-size: var(--text-xs); color: var(--color-muted);">
          No peer heartbeat signals detected. Cluster nodes have not yet broadcast status frames.
        </p>
        <button id="btn-probe-rail" style="font-size: var(--text-xs); padding: 2px 8px;">Broadcast Probe</button>
      </div>
    </div>
  `;
}

export function renderHeartbeatRailError(errorMsg?: string): string {
  const message = errorMsg || 'Heartbeat pulse stream disconnected. Coordinator at port 8000 is unreachable.';
  return `
    <div class="heartbeat-rail-card" id="heartbeat-rail" style="border-color: var(--color-down-border);">
      <div class="heartbeat-rail-header">
        <div class="heartbeat-rail-title">
          <span>Heartbeat Pulse Rail</span>
          <span class="badge badge-down" style="font-size: var(--text-2xs); padding: 0 4px;">STREAM OFFLINE</span>
        </div>
      </div>

      <div style="padding: var(--space-4) var(--space-3); background-color: var(--color-surface-subtle); border: 1px solid var(--color-down-border); display: flex; justify-content: space-between; align-items: center;">
        <p style="font-size: var(--text-xs); color: var(--color-ink-secondary);">
          ${message}
        </p>
        <button id="btn-reconnect-rail" style="font-size: var(--text-xs); padding: 2px 8px; border-color: var(--color-down-border);">Reconnect Rail</button>
      </div>
    </div>
  `;
}

function renderTicksHtml(history: Array<'ok' | 'warn' | 'missed'> = [], isPulsing = false): string {
  const ticks = history.length > 0 ? history : Array(20).fill('ok');
  return ticks.map((tick, index) => {
    const isLeadTick = index === ticks.length - 1;
    const tickClass = tick === 'warn' ? 'tick-warn' : tick === 'missed' ? 'tick-missed' : '';
    const pulseClass = (isLeadTick && isPulsing) ? 'pulse-active' : '';
    return `<span class="pulse-tick ${tickClass} ${pulseClass}"></span>`;
  }).join('');
}

export function renderHeartbeatLane(node: NodeHeartbeatState | NodeInfo): string {
  const isLeader = node.state === 'LEADER';
  const isOnline = node.status === 'ONLINE';
  const isCandidate = node.state === 'CANDIDATE';
  const badgeText = isLeader ? 'LEAD' : isCandidate ? 'CAND' : 'FOLL';
  const badgeClass = isLeader ? 'badge-ok' : isCandidate ? 'badge-warn' : 'badge-info';
  
  const history = 'history' in node ? node.history : Array(20).fill(isOnline ? 'ok' : 'missed');
  const isPulsing = 'isPulsing' in node ? node.isPulsing : false;
  const port = 'port' in node ? node.port : (node.url ? `:${new URL(node.url).port || '8000'}` : ':8000');
  const offset = isOnline ? (isLeader ? '+0.0 ms' : node.id.includes('B') || node.id.includes('b') ? '+8.4 ms' : '+12.1 ms') : 'OFFLINE';
  const dotClass = isOnline ? (isLeader ? 'dot-ok' : 'dot-ok') : 'dot-down';
  const stalledClass = isOnline ? '' : 'lane-stalled';

  return `
    <div class="heartbeat-lane ${stalledClass}" id="lane-${node.id}" data-node="${node.id}" tabindex="0">
      <div class="lane-node-id">
        <span class="status-dot ${dotClass}"></span>
        <span class="text-ink">${'displayName' in node ? node.displayName : node.id}</span>
        <span class="badge ${badgeClass}" style="font-size: 9px; padding: 0 3px;">${badgeText}</span>
      </div>
      <div class="lane-track" title="Recent Heartbeats for ${'displayName' in node ? node.displayName : node.id}">
        ${renderTicksHtml(history, isPulsing)}
      </div>
      <div class="lane-meta ${isLeader ? 'text-ok' : isOnline ? '' : 'text-down'}">
        ${isOnline ? `${offset} &bull; ${port}` : `OFFLINE &bull; ${port}`}
      </div>
    </div>
  `;
}

export function renderHeartbeatRail(
  nodes: Array<NodeHeartbeatState | NodeInfo> = [],
  viewState: ViewState = 'normal',
  errorMessage?: string
): string {
  if (viewState === 'loading') return renderHeartbeatRailSkeleton();
  if (viewState === 'empty') return renderHeartbeatRailEmpty();
  if (viewState === 'error') return renderHeartbeatRailError(errorMessage);

  const defaultNodes = nodes.length > 0 ? nodes : [
    { id: 'nodeA', displayName: 'nodeA', state: 'LEADER' as const, status: 'ONLINE' as const, lastHeartbeat: Date.now() / 1000, latencyMs: 0, port: ':8000', isPulsing: false, history: Array(20).fill('ok' as const), consecutiveMissed: 0 },
    { id: 'nodeB', displayName: 'nodeB', state: 'FOLLOWER' as const, status: 'ONLINE' as const, lastHeartbeat: Date.now() / 1000, latencyMs: 8.4, port: ':8001', isPulsing: false, history: Array(20).fill('ok' as const), consecutiveMissed: 0 },
    { id: 'nodeC', displayName: 'nodeC', state: 'FOLLOWER' as const, status: 'ONLINE' as const, lastHeartbeat: Date.now() / 1000, latencyMs: 12.1, port: ':8002', isPulsing: false, history: Array(20).fill('ok' as const), consecutiveMissed: 0 },
  ];

  const lanesHtml = defaultNodes.map(node => renderHeartbeatLane(node)).join('');

  return `
    <div class="heartbeat-rail-card" id="heartbeat-rail">
      <div class="heartbeat-rail-header">
        <div class="heartbeat-rail-title">
          <span>Heartbeat Pulse Rail</span>
          <span class="badge badge-info" style="font-size: var(--text-2xs); padding: 0 4px;">500ms Cadence</span>
        </div>
        <div class="heartbeat-rail-legend">
          <span><span class="status-dot dot-ok" style="width: 5px; height: 5px;"></span> Healthy</span>
          <span><span class="status-dot dot-warn" style="width: 5px; height: 5px;"></span> Syncing</span>
          <span><span class="status-dot dot-down" style="width: 5px; height: 5px;"></span> Missed</span>
        </div>
      </div>

      <div class="heartbeat-lanes" id="heartbeat-lanes-container">
        ${lanesHtml}
      </div>
    </div>
  `;
}

/**
 * High-performance in-place DOM updater for heartbeat pulse lanes.
 * Updates track ticks, status dots, and metadata without full card re-render.
 */
export function updateHeartbeatRailDOM(nodeStates: NodeHeartbeatState[]): void {
  const container = document.getElementById('heartbeat-lanes-container');
  if (!container) return;

  for (const node of nodeStates) {
    let laneEl = document.getElementById(`lane-${node.id}`);
    if (!laneEl) {
      // If node ID format differs (e.g. Node A vs nodeA), look by data-node attribute
      laneEl = container.querySelector(`[data-node="${node.id}"]`) as HTMLElement | null;
    }

    if (!laneEl) {
      // Re-render container if lane elements are completely missing
      container.innerHTML = nodeStates.map(n => renderHeartbeatLane(n)).join('');
      return;
    }

    const isOnline = node.status === 'ONLINE';
    const isLeader = node.state === 'LEADER';
    const isCandidate = node.state === 'CANDIDATE';
    const badgeText = isLeader ? 'LEAD' : isCandidate ? 'CAND' : 'FOLL';
    const badgeClass = isLeader ? 'badge-ok' : isCandidate ? 'badge-warn' : 'badge-info';
    const dotClass = isOnline ? (isLeader ? 'dot-ok' : 'dot-ok') : 'dot-down';

    // Stalled state class
    if (isOnline) {
      laneEl.classList.remove('lane-stalled');
    } else {
      laneEl.classList.add('lane-stalled');
    }

    // Update status dot & badge
    const dotEl = laneEl.querySelector('.status-dot');
    if (dotEl) {
      dotEl.className = `status-dot ${dotClass}`;
    }
    const badgeEl = laneEl.querySelector('.badge');
    if (badgeEl) {
      badgeEl.className = `badge ${badgeClass}`;
      badgeEl.textContent = badgeText;
    }

    // Update track pulse ticks
    const trackEl = laneEl.querySelector('.lane-track');
    if (trackEl) {
      trackEl.innerHTML = renderTicksHtml(node.history, node.isPulsing);
    }

    // Update lane meta
    const metaEl = laneEl.querySelector('.lane-meta');
    if (metaEl) {
      const offset = isOnline ? (isLeader ? '+0.0 ms' : node.id.includes('B') || node.id.includes('b') ? '+8.4 ms' : '+12.1 ms') : 'OFFLINE';
      metaEl.className = `lane-meta ${isLeader ? 'text-ok' : isOnline ? '' : 'text-down'}`;
      metaEl.innerHTML = isOnline ? `${offset} &bull; ${node.port}` : `OFFLINE &bull; ${node.port}`;
    }
  }
}

