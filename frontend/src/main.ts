/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Main Application Bootstrap & Lifecycle Manager
 */

import './styles/index.css';
import { router } from './router/index.ts';
import { healthService, clusterStatusService, heartbeatService } from './services/index.ts';
import {
  renderClusterStatus,
  renderHeartbeatRail,
  renderNodeList,
  renderFilePanel,
  updateClusterStatusDOM,
  updateHeartbeatRailDOM,
} from './components/index.ts';
import type { ViewState } from './types/components.ts';

let currentViewState: ViewState = 'normal';

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

function attachStateSwitcherListeners(): void {
  const stateBtns = document.querySelectorAll<HTMLButtonElement>('.state-btn');
  stateBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetState = btn.dataset.state as ViewState;
      if (targetState) {
        setViewState(targetState);
      }
    });
  });
}

export function setViewState(state: ViewState): void {
  currentViewState = state;
  renderDashboard();
}

export function getViewState(): ViewState {
  return currentViewState;
}

function renderDashboard(): void {
  const appContainer = document.getElementById('app-main');
  if (!appContainer) return;

  const currentHealth = healthService.getLastResult();
  const currentCluster = clusterStatusService.getLastResult();
  const currentHeartbeats = heartbeatService.getLastResult();

  const switcherHtml = `
    <div style="display: flex; justify-content: flex-end; align-items: center; gap: var(--space-2); margin-bottom: -16px;">
      <span style="font-size: var(--text-2xs); color: var(--color-muted); font-family: var(--font-mono); text-transform: uppercase;">State Preview:</span>
      <div class="state-switcher-toolbar" role="toolbar" aria-label="Visual State Switcher">
        <button class="state-btn ${currentViewState === 'normal' ? 'active' : ''}" data-state="normal">LIVE</button>
        <button class="state-btn ${currentViewState === 'loading' ? 'active' : ''}" data-state="loading">LOADING</button>
        <button class="state-btn ${currentViewState === 'empty' ? 'active' : ''}" data-state="empty">EMPTY</button>
        <button class="state-btn ${currentViewState === 'error' ? 'active' : ''}" data-state="error">ERROR</button>
      </div>
    </div>
  `;

  appContainer.innerHTML = `
    ${switcherHtml}

    <!-- ZONE 1: CLUSTER STATUS & HEARTBEAT RAIL -->
    <section class="zone-cluster-status" id="zone-cluster-status" aria-label="Cluster Status and Telemetry">
      <div id="cluster-status-root">
        ${renderClusterStatus(
          currentCluster.data,
          currentHealth.status,
          currentCluster.latencyMs,
          currentViewState
        )}
      </div>
      <div id="heartbeat-rail-root">
        ${renderHeartbeatRail(currentHeartbeats.nodes, currentViewState)}
      </div>
    </section>

    <!-- LOWER TWO-COLUMN GRID: ZONE 2 (NODES) & ZONE 3 (FILES) -->
    <div class="lower-zones-grid">
      <div id="node-list-root">
        ${renderNodeList([], currentViewState)}
      </div>
      <div id="file-panel-root">
        ${renderFilePanel([], currentViewState)}
      </div>
    </div>
  `;

  attachStateSwitcherListeners();

  if (currentViewState === 'normal') {
    attachInteractiveHoverLinks();
  }
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
    if (currentViewState !== 'normal') return;
    const connectivityItem = document.getElementById('backend-connectivity-item');
    if (connectivityItem) {
      if (result.reachable) {
        connectivityItem.innerHTML = `<span class="badge badge-ok" title="Backend node reached (+${result.latencyMs}ms)"><span class="status-dot dot-ok"></span> API LIVE</span>`;
      } else {
        connectivityItem.innerHTML = `<span class="badge badge-down" title="${result.error || 'Server offline'}"><span class="status-dot dot-down"></span> OFFLINE</span>`;
      }
    }
  });

  // Subscribe to cluster status polling for dynamic Zone 1 telemetry
  clusterStatusService.subscribe((result) => {
    if (currentViewState !== 'normal') return;
    const healthResult = healthService.getLastResult();
    const connectivity = result.reachable ? healthResult.status : 'DISCONNECTED';
    updateClusterStatusDOM(result.data, connectivity, result.latencyMs);
  });

  // Subscribe to heartbeat rail polling for live per-node pulse tracks
  heartbeatService.subscribe((result) => {
    if (currentViewState !== 'normal') return;
    updateHeartbeatRailDOM(result.nodes);
  });

  // Start routing, health checking, cluster status polling, and heartbeat pulse engine (~500ms cadence)
  router.start();
  healthService.startPolling(3000);
  clusterStatusService.startPolling(500);
  heartbeatService.startPolling(500);

  // Lifecycle listeners to prevent memory leaks
  window.addEventListener('beforeunload', () => {
    clusterStatusService.stopPolling();
    heartbeatService.stopPolling();
    healthService.stopPolling();
  });
}

// Start application on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}


