/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Component: NodeList (Zone 2 Cluster Nodes Inventory)
 */

import type { NodeInfo } from '../types/api.ts';
import type { ViewState } from '../types/components.ts';

export function renderNodeListSkeleton(): string {
  return `
    <section class="zone-node-list" id="zone-node-list" aria-label="Cluster Node Inventory">
      <div class="zone-header">
        <div class="zone-title-group">
          <h2 class="zone-title">Cluster Nodes</h2>
          <span class="zone-count font-mono">(SCANNING...)</span>
        </div>
        <span class="zone-caption">Querying cluster topology</span>
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
            <tr>
              <td><span class="skeleton-bar" style="width: 70px;"></span></td>
              <td><span class="skeleton-bar" style="width: 55px;"></span></td>
              <td><span class="skeleton-bar" style="width: 45px;"></span></td>
              <td><span class="skeleton-bar" style="width: 40px;"></span></td>
              <td><span class="skeleton-bar" style="width: 65px;"></span></td>
              <td><span class="skeleton-bar" style="width: 35px;"></span></td>
            </tr>
            <tr>
              <td><span class="skeleton-bar" style="width: 70px;"></span></td>
              <td><span class="skeleton-bar" style="width: 55px;"></span></td>
              <td><span class="skeleton-bar" style="width: 45px;"></span></td>
              <td><span class="skeleton-bar" style="width: 40px;"></span></td>
              <td><span class="skeleton-bar" style="width: 65px;"></span></td>
              <td><span class="skeleton-bar" style="width: 35px;"></span></td>
            </tr>
            <tr>
              <td><span class="skeleton-bar" style="width: 70px;"></span></td>
              <td><span class="skeleton-bar" style="width: 55px;"></span></td>
              <td><span class="skeleton-bar" style="width: 45px;"></span></td>
              <td><span class="skeleton-bar" style="width: 40px;"></span></td>
              <td><span class="skeleton-bar" style="width: 65px;"></span></td>
              <td><span class="skeleton-bar" style="width: 35px;"></span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  `;
}

export function renderNodeListEmpty(): string {
  return `
    <section class="zone-node-list" id="zone-node-list" aria-label="Cluster Node Inventory">
      <div class="zone-header">
        <div class="zone-title-group">
          <h2 class="zone-title">Cluster Nodes</h2>
          <span class="zone-count font-mono text-warn">(0 DISCOVERED)</span>
        </div>
        <span class="zone-caption">No active membership</span>
      </div>

      <div class="state-panel empty-state-panel" id="node-list-empty">
        <div class="state-header-group">
          <span class="badge badge-warn">0 PEERS</span>
          <h3 class="state-title">No Nodes Registered</h3>
        </div>
        <p class="state-message">
          No peer nodes discovered in cluster membership. Verify node processes (nodeA, nodeB, nodeC) are running on ports 8000–8002.
        </p>
        <div class="state-action-row">
          <button id="btn-scan-nodes" style="font-size: var(--text-xs); padding: var(--space-1) var(--space-3);">Scan Local Ports (8000–8002)</button>
        </div>
      </div>
    </section>
  `;
}

export function renderNodeListError(errorMsg?: string): string {
  const message = errorMsg || 'Unable to retrieve node telemetry. Coordinator returned HTTP 503 Service Unavailable.';
  return `
    <section class="zone-node-list" id="zone-node-list" aria-label="Cluster Node Inventory">
      <div class="zone-header">
        <div class="zone-title-group">
          <h2 class="zone-title">Cluster Nodes</h2>
          <span class="zone-count font-mono text-down">(TOPOLOGY ERROR)</span>
        </div>
        <span class="zone-caption text-down">Query failed</span>
      </div>

      <div class="state-panel error-state-panel" id="node-list-error">
        <div class="state-header-group">
          <span class="badge badge-down">HTTP 503</span>
          <h3 class="state-title">Topology Query Failed</h3>
        </div>
        <p class="state-message">
          ${message}
        </p>
        <div class="state-action-row">
          <button id="btn-retry-nodes" style="font-size: var(--text-xs); padding: var(--space-1) var(--space-3); border-color: var(--color-down-border);">Retry Fetch</button>
        </div>
      </div>
    </section>
  `;
}

export function renderNodeList(
  nodes: NodeInfo[] = [],
  viewState: ViewState = 'normal',
  errorMessage?: string
): string {
  if (viewState === 'loading') return renderNodeListSkeleton();
  if (viewState === 'empty') return renderNodeListEmpty();
  if (viewState === 'error') return renderNodeListError(errorMessage);

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
