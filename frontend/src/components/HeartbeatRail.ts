/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Component: HeartbeatRail (Signature Pulse Rail)
 */

import type { NodeInfo } from '../types/api.ts';

export function renderHeartbeatRail(nodes: NodeInfo[] = []): string {
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
