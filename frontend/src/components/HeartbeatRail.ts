/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Component: HeartbeatRail (Signature Pulse Rail)
 */

import type { NodeInfo } from '../types/api.ts';
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

export function renderHeartbeatRail(
  nodes: NodeInfo[] = [],
  viewState: ViewState = 'normal',
  errorMessage?: string
): string {
  if (viewState === 'loading') return renderHeartbeatRailSkeleton();
  if (viewState === 'empty') return renderHeartbeatRailEmpty();
  if (viewState === 'error') return renderHeartbeatRailError(errorMessage);

  const defaultNodes: NodeInfo[] = nodes.length > 0 ? nodes : [
    { id: 'nodeA', state: 'LEADER', status: 'ONLINE', last_heartbeat: Date.now() / 1000, url: 'http://localhost:8000' },
    { id: 'nodeB', state: 'FOLLOWER', status: 'ONLINE', last_heartbeat: Date.now() / 1000, url: 'http://localhost:8001' },
    { id: 'nodeC', state: 'FOLLOWER', status: 'ONLINE', last_heartbeat: Date.now() / 1000, url: 'http://localhost:8002' },
  ];

  const lanesHtml = defaultNodes.map(node => {
    const isLeader = node.state === 'LEADER';
    const isOnline = node.status === 'ONLINE';
    const badgeText = isLeader ? 'LEAD' : 'FOLL';
    const badgeClass = isLeader ? 'badge-ok' : 'badge-info';
    const port = node.url ? `:${new URL(node.url).port || '8000'}` : ':8000';
    const offset = isLeader ? '+0.0 ms' : node.id === 'nodeB' ? '+8.4 ms' : '+12.1 ms';
    const dotClass = isOnline ? (isLeader ? 'dot-ok' : 'dot-ok') : 'dot-down';

    return `
      <div class="heartbeat-lane" id="lane-${node.id}" data-node="${node.id}" tabindex="0">
        <div class="lane-node-id">
          <span class="status-dot ${dotClass}"></span>
          <span class="text-ink">${node.id}</span>
          <span class="badge ${badgeClass}" style="font-size: 9px; padding: 0 3px;">${badgeText}</span>
        </div>
        <div class="lane-track" title="Recent Heartbeats for ${node.id}">
          <span class="pulse-tick"></span>
          <span class="pulse-tick"></span>
          <span class="pulse-tick"></span>
          <span class="pulse-tick"></span>
          <span class="pulse-tick"></span>
          <span class="pulse-tick"></span>
          <span class="pulse-tick"></span>
          <span class="pulse-tick ${node.id === 'nodeC' ? 'tick-warn' : ''}"></span>
          <span class="pulse-tick"></span>
          <span class="pulse-tick"></span>
          <span class="pulse-tick"></span>
          <span class="pulse-tick"></span>
          <span class="pulse-tick"></span>
          <span class="pulse-tick"></span>
          <span class="pulse-tick"></span>
          <span class="pulse-tick"></span>
          <span class="pulse-tick"></span>
          <span class="pulse-tick"></span>
          <span class="pulse-tick"></span>
          <span class="pulse-tick"></span>
        </div>
        <div class="lane-meta ${isLeader ? 'text-ok' : ''}">${offset} &bull; ${port}</div>
      </div>
    `;
  }).join('');

  return `
    <div class="heartbeat-rail-card" id="heartbeat-rail">
      <div class="heartbeat-rail-header">
        <div class="heartbeat-rail-title">
          <span>Heartbeat Pulse Rail</span>
          <span class="badge badge-info" style="font-size: var(--text-2xs); padding: 0 4px;">500ms Interval</span>
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
