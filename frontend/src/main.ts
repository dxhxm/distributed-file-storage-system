/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Main Application Bootstrap & Lifecycle Manager
 */

import './styles/index.css';
import { router } from './router/index.ts';
import { healthService } from './services/index.ts';
import {
  renderClusterStatus,
  renderHeartbeatRail,
  renderNodeList,
  renderFilePanel,
} from './components/index.ts';

function attachInteractiveHoverLinks(): void {
  const nodeRows = document.querySelectorAll<HTMLElement>('.node-row');
  const lanes = document.querySelectorAll<HTMLElement>('.heartbeat-lane');

  function highlightLane(nodeId: string, active: boolean): void {
    lanes.forEach(lane => {
      if (lane.dataset.node === nodeId) {
        if (active) {
          lane.style.borderColor = 'var(--color-line-bright)';
          lane.style.backgroundColor = 'var(--color-surface-hover)';
        } else {
          lane.style.borderColor = '';
          lane.style.backgroundColor = '';
        }
      }
    });
  }

  function highlightRow(nodeId: string, active: boolean): void {
    nodeRows.forEach(row => {
      if (row.dataset.node === nodeId) {
        if (active) {
          row.style.backgroundColor = 'var(--color-surface-hover)';
        } else {
          row.style.backgroundColor = '';
        }
      }
    });
  }

  nodeRows.forEach(row => {
    const nodeId = row.dataset.node;
    if (!nodeId) return;

    row.addEventListener('mouseenter', () => highlightLane(nodeId, true));
    row.addEventListener('mouseleave', () => highlightLane(nodeId, false));
    row.addEventListener('focus', () => highlightLane(nodeId, true));
    row.addEventListener('blur', () => highlightLane(nodeId, false));
  });

  lanes.forEach(lane => {
    const nodeId = lane.dataset.node;
    if (!nodeId) return;

    lane.addEventListener('mouseenter', () => highlightRow(nodeId, true));
    lane.addEventListener('mouseleave', () => highlightRow(nodeId, false));
    lane.addEventListener('focus', () => highlightRow(nodeId, true));
    lane.addEventListener('blur', () => highlightRow(nodeId, false));
  });
}

function renderDashboard(): void {
  const appContainer = document.getElementById('app-main');
  if (!appContainer) return;

  const currentHealth = healthService.getLastResult();

  appContainer.innerHTML = `
    <!-- ZONE 1: CLUSTER STATUS & HEARTBEAT RAIL -->
    <section class="zone-cluster-status" id="zone-cluster-status" aria-label="Cluster Status and Telemetry">
      <div id="cluster-status-root">
        ${renderClusterStatus(null, currentHealth.status, currentHealth.latencyMs)}
      </div>
      <div id="heartbeat-rail-root">
        ${renderHeartbeatRail()}
      </div>
    </section>

    <!-- LOWER TWO-COLUMN GRID: ZONE 2 (NODES) & ZONE 3 (FILES) -->
    <div class="lower-zones-grid">
      <div id="node-list-root">
        ${renderNodeList()}
      </div>
      <div id="file-panel-root">
        ${renderFilePanel()}
      </div>
    </div>
  `;

  attachInteractiveHoverLinks();
}

function init(): void {
  // Setup client-side routes
  router
    .addRoute('/', () => renderDashboard())
    .addRoute('/dashboard', () => renderDashboard())
    .addRoute('/tokens', () => {
      window.location.href = './tokens-preview.html';
    })
    .setNotFound(() => renderDashboard());

  // Subscribe to health monitoring for live backend indicator
  healthService.subscribe((result) => {
    const connectivityItem = document.getElementById('backend-connectivity-item');
    if (connectivityItem) {
      if (result.reachable) {
        connectivityItem.innerHTML = `<span class="badge badge-ok" title="Backend node reached (+${result.latencyMs}ms)"><span class="status-dot dot-ok"></span> API LIVE</span>`;
      } else {
        connectivityItem.innerHTML = `<span class="badge badge-down" title="${result.error || 'Server offline'}"><span class="status-dot dot-down"></span> OFFLINE</span>`;
      }
    }
  });

  // Start routing and background health check
  router.start();
  healthService.startPolling(3000);
}

// Start application on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
