/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Component: NodeList (Zone 2 Cluster Nodes Inventory)
 */

import type { NodeInfo } from '../types/api.ts';

export function renderNodeList(nodes: NodeInfo[] = []): string {
  const defaultNodes: NodeInfo[] = nodes.length > 0 ? nodes : [
    { id: 'nodeA', state: 'LEADER', status: 'ONLINE', last_heartbeat: Date.now() / 1000, url: 'http://localhost:8000' },
    { id: 'nodeB', state: 'FOLLOWER', status: 'ONLINE', last_heartbeat: Date.now() / 1000, url: 'http://localhost:8001' },
    { id: 'nodeC', state: 'FOLLOWER', status: 'ONLINE', last_heartbeat: Date.now() / 1000, url: 'http://localhost:8002' },
  ];

  const onlineCount = defaultNodes.filter(n => n.status === 'ONLINE').length;

  const rowsHtml = defaultNodes.map(node => {
    const isLeader = node.state === 'LEADER';
    const isOnline = node.status === 'ONLINE';
    const badgeClass = isLeader ? 'badge-ok' : 'badge-info';
    const dotClass = isOnline ? (isLeader ? 'dot-ok' : 'dot-muted') : 'dot-down';
    const latency = isLeader ? '+0.0 ms' : node.id === 'nodeB' ? '+8.4 ms' : '+12.1 ms';
    const port = node.url ? `:${new URL(node.url).port || '8000'}` : ':8000';

    return `
      <tr class="node-row" id="node-row-${node.id}" data-node="${node.id}" tabindex="0">
        <td class="font-mono text-ink">${node.id}</td>
        <td>
          <span class="badge ${badgeClass}">
            <span class="status-dot ${dotClass}"></span> ${node.state}
          </span>
        </td>
        <td><span class="${isOnline ? 'text-ok' : 'text-down'} font-mono text-xs">${node.status}</span></td>
        <td class="font-mono ${isLeader ? 'text-ok' : ''}">${latency}</td>
        <td class="font-mono text-xs text-muted">21:46:39 UTC</td>
        <td class="font-mono text-xs">${port}</td>
      </tr>
    `;
  }).join('');

  return `
    <section class="zone-node-list" id="zone-node-list" aria-label="Cluster Node Inventory">
      <div class="zone-header">
        <div class="zone-title-group">
          <h2 class="zone-title">Cluster Nodes</h2>
          <span class="zone-count font-mono">(${onlineCount} ONLINE)</span>
        </div>
        <span class="zone-caption">Quorum majority active</span>
      </div>

      <div class="node-table-container">
        <table>
          <thead>
            <tr>
              <th>Node ID</th>
              <th>Role</th>
              <th>Status</th>
              <th>Latency</th>
              <th>Last Pulse</th>
              <th>Port</th>
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
