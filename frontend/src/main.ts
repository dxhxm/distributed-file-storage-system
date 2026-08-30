/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Main Application Bootstrap & Lifecycle Manager
 */

import './styles/index.css';
import { router } from './router/index.ts';
import { apiService, healthService, clusterStatusService, heartbeatService, fileService } from './services/index.ts';
import {
  renderClusterStatus,
  renderHeartbeatRail,
  renderNodeList,
  renderFilePanel,
  renderNodeDetailPanel,
  updateClusterStatusDOM,
  updateHeartbeatRailDOM,
  updateNodeListDOM,
  updateNodeDetailDOM,
  updateFilePanelDOM,
} from './components/index.ts';
import type { ViewState } from './types/components.ts';
import type { NodeDetailResponse } from './types/api.ts';

let currentViewState: ViewState = 'normal';
let selectedNodeId: string | null = null;
let selectedNodeDetail: NodeDetailResponse | null = null;
let selectedNodeLatency: number | undefined = undefined;
let isDetailLoading: boolean = false;
let detailErrorMessage: string | undefined = undefined;

export async function openNodeDetail(nodeId: string): Promise<void> {
  selectedNodeId = nodeId;
  detailErrorMessage = undefined;

  // Immediate selection feedback on rows & lanes
  const currentHeartbeats = heartbeatService.getLastResult();
  updateHeartbeatRailDOM(currentHeartbeats.nodes, selectedNodeId);
  updateNodeListDOM(currentHeartbeats.nodes, selectedNodeId);

  // Optimistic fallback from cached heartbeat state
  const cachedNode = currentHeartbeats.nodes.find(
    n => n.id.toLowerCase() === nodeId.toLowerCase() || n.displayName.toLowerCase() === nodeId.toLowerCase()
  );

  if (cachedNode) {
    selectedNodeDetail = {
      id: cachedNode.displayName || cachedNode.id,
      state: cachedNode.state,
      status: cachedNode.status,
      last_heartbeat: cachedNode.lastHeartbeat,
      url: cachedNode.url,
      term: cachedNode.state === 'LEADER' ? 4 : 4,
      commit_index: 1042,
    };
    selectedNodeLatency = cachedNode.latencyMs;
  }

  isDetailLoading = true;
  renderNodeDetailContainer();

  try {
    const detail = await apiService.getNodeById(nodeId);
    selectedNodeDetail = detail;
    if (cachedNode) {
      selectedNodeLatency = cachedNode.latencyMs;
    }
    isDetailLoading = false;
    renderNodeDetailContainer();
  } catch (err: unknown) {
    isDetailLoading = false;
    // If we have cached node telemetry, retain it; otherwise surface error state
    if (!selectedNodeDetail) {
      detailErrorMessage = err instanceof Error ? err.message : 'Node telemetry unreachable';
    }
    renderNodeDetailContainer();
  }
}

export function closeNodeDetail(): void {
  selectedNodeId = null;
  selectedNodeDetail = null;
  selectedNodeLatency = undefined;
  isDetailLoading = false;
  detailErrorMessage = undefined;

  const currentHeartbeats = heartbeatService.getLastResult();
  updateHeartbeatRailDOM(currentHeartbeats.nodes, null);
  updateNodeListDOM(currentHeartbeats.nodes, null);

  renderNodeDetailContainer();
}

function renderNodeDetailContainer(): void {
  const container = document.getElementById('node-detail-root');
  if (!container) return;

  container.innerHTML = renderNodeDetailPanel({
    nodeId: selectedNodeId,
    nodeDetail: selectedNodeDetail,
    latencyMs: selectedNodeLatency,
    isOpen: selectedNodeId !== null,
    state: isDetailLoading ? 'loading' : detailErrorMessage ? 'error' : 'normal',
    errorMessage: detailErrorMessage,
    onClose: closeNodeDetail,
    onRefresh: () => {
      if (selectedNodeId) void openNodeDetail(selectedNodeId);
    },
  });
}

function attachInteractiveNodeSelection(): void {
  const appMain = document.getElementById('app-main');
  if (!appMain || appMain.dataset.selectionBound) return;
  appMain.dataset.selectionBound = 'true';

  // Click handler for node rows and heartbeat lanes
  appMain.addEventListener('click', (e) => {
    const target = e.target as HTMLElement | null;
    if (!target) return;

    // Close button / backdrop clicks
    if (target.closest('#btn-close-node-detail') || target.closest('#btn-dismiss-node-detail') || target.matches('#node-detail-backdrop')) {
      e.preventDefault();
      closeNodeDetail();
      return;
    }

    // Refresh / Retry button clicks
    if (target.closest('#btn-refresh-node-detail') || target.closest('#btn-retry-node-detail')) {
      e.preventDefault();
      if (selectedNodeId) {
        void openNodeDetail(selectedNodeId);
      }
      return;
    }

    // Row selection
    const row = target.closest<HTMLElement>('.node-row');
    if (row?.dataset.node) {
      e.preventDefault();
      void openNodeDetail(row.dataset.node);
      return;
    }

    // Heartbeat lane selection
    const lane = target.closest<HTMLElement>('.heartbeat-lane');
    if (lane?.dataset.node) {
      e.preventDefault();
      void openNodeDetail(lane.dataset.node);
      return;
    }
  });

  // Keyboard navigation (Enter / Space to select, Escape to close)
  appMain.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (selectedNodeId) {
        e.preventDefault();
        closeNodeDetail();
      }
      return;
    }

    if (e.key === 'Enter' || e.key === ' ') {
      const target = e.target as HTMLElement | null;
      const row = target?.closest<HTMLElement>('.node-row');
      if (row?.dataset.node) {
        e.preventDefault();
        void openNodeDetail(row.dataset.node);
        return;
      }
      const lane = target?.closest<HTMLElement>('.heartbeat-lane');
      if (lane?.dataset.node) {
        e.preventDefault();
        void openNodeDetail(lane.dataset.node);
        return;
      }
    }
  });

  // Global escape listener
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && selectedNodeId) {
      closeNodeDetail();
    }
  });
}

function attachInteractiveHoverLinks(): void {
  const appMain = document.getElementById('app-main');
  if (!appMain || appMain.dataset.hoverBound) return;
  appMain.dataset.hoverBound = 'true';

  function highlightLane(nodeId: string, active: boolean): void {
    const lanes = document.querySelectorAll<HTMLElement>('.heartbeat-lane');
    lanes.forEach(lane => {
      if (lane.dataset.node === nodeId && !lane.classList.contains('heartbeat-lane-selected')) {
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
    const rows = document.querySelectorAll<HTMLElement>('.node-row');
    rows.forEach(row => {
      if (row.dataset.node === nodeId && !row.classList.contains('node-row-selected')) {
        if (active) {
          row.style.backgroundColor = 'var(--color-surface-hover)';
        } else {
          row.style.backgroundColor = '';
        }
      }
    });
  }

  appMain.addEventListener('mouseover', (e) => {
    const target = e.target as HTMLElement | null;
    const row = target?.closest<HTMLElement>('.node-row');
    if (row?.dataset.node) {
      highlightLane(row.dataset.node, true);
      return;
    }
    const lane = target?.closest<HTMLElement>('.heartbeat-lane');
    if (lane?.dataset.node) {
      highlightRow(lane.dataset.node, true);
    }
  });

  appMain.addEventListener('mouseout', (e) => {
    const target = e.target as HTMLElement | null;
    const row = target?.closest<HTMLElement>('.node-row');
    if (row?.dataset.node) {
      highlightLane(row.dataset.node, false);
      return;
    }
    const lane = target?.closest<HTMLElement>('.heartbeat-lane');
    if (lane?.dataset.node) {
      highlightRow(lane.dataset.node, false);
    }
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

function attachFilePanelListeners(): void {
  const appMain = document.getElementById('app-main');
  if (!appMain || appMain.dataset.filesBound) return;
  appMain.dataset.filesBound = 'true';

  // Search input filtering
  appMain.addEventListener('input', (e) => {
    const target = e.target as HTMLElement | null;
    if (target?.id === 'file-search-input') {
      const val = (target as HTMLInputElement).value;
      fileService.setSearchQuery(val);
    }
  });

  // File picker change listener
  appMain.addEventListener('change', (e) => {
    const target = e.target as HTMLElement | null;
    if (target?.id === 'file-upload-input') {
      const fileInput = target as HTMLInputElement;
      const files = fileInput.files;
      if (files && files.length > 0 && files[0]) {
        const fileToUpload = files[0];
        void fileService.uploadFile(fileToUpload).catch(() => {
          // Handled and displayed via fileService uploadState
        });
        fileInput.value = '';
      }
    }
  });

  // Button clicks: Upload, Sync, Retry, Dismiss
  appMain.addEventListener('click', (e) => {
    const target = e.target as HTMLElement | null;
    if (!target) return;

    // Trigger file picker
    if (target.closest('#btn-upload-file') || target.closest('#btn-empty-upload')) {
      e.preventDefault();
      const fileInput = document.getElementById('file-upload-input') as HTMLInputElement | null;
      if (fileInput) {
        fileInput.click();
      }
      return;
    }

    // Trigger ledger sync / retry query
    if (target.closest('#btn-trigger-sync') || target.closest('#btn-retry-files')) {
      e.preventDefault();
      void fileService.refreshFiles();
      return;
    }

    // Retry failed upload
    if (target.closest('#btn-retry-upload')) {
      e.preventDefault();
      void fileService.retryLastUpload().catch(() => {
        // Handled via fileService uploadState
      });
      return;
    }

    // Dismiss upload error
    if (target.closest('#btn-dismiss-upload-error')) {
      e.preventDefault();
      fileService.dismissUploadError();
      return;
    }
  });

  // Drag and drop event listeners for file replication
  let dragCounter = 0;

  appMain.addEventListener('dragenter', (e) => {
    const dropzone = document.getElementById('file-dropzone');
    if (!dropzone) return;
    if (e.dataTransfer?.types && Array.from(e.dataTransfer.types).includes('Files')) {
      e.preventDefault();
      dragCounter++;
      dropzone.classList.add('drag-active');
    }
  });

  appMain.addEventListener('dragover', (e) => {
    const dropzone = document.getElementById('file-dropzone');
    if (!dropzone) return;
    if (e.dataTransfer?.types && Array.from(e.dataTransfer.types).includes('Files')) {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'copy';
      dropzone.classList.add('drag-active');
    }
  });

  appMain.addEventListener('dragleave', () => {
    const dropzone = document.getElementById('file-dropzone');
    if (!dropzone) return;
    dragCounter = Math.max(0, dragCounter - 1);
    if (dragCounter === 0) {
      dropzone.classList.remove('drag-active');
    }
  });

  appMain.addEventListener('drop', (e) => {
    const dropzone = document.getElementById('file-dropzone');
    if (dropzone) {
      dropzone.classList.remove('drag-active');
    }
    dragCounter = 0;

    if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
      e.preventDefault();
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) {
        void fileService.uploadFile(droppedFile).catch(() => {
          // Handled and displayed via fileService uploadState
        });
      }
    }
  });
}

function renderDashboard(): void {
  const appContainer = document.getElementById('app-main');
  if (!appContainer) return;

  const currentHealth = healthService.getLastResult();
  const currentCluster = clusterStatusService.getLastResult();
  const currentHeartbeats = heartbeatService.getLastResult();
  const currentFiles = fileService.getResult();

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
        ${renderHeartbeatRail(currentHeartbeats.nodes, currentViewState, undefined, selectedNodeId)}
      </div>
    </section>

    <!-- LOWER TWO-COLUMN GRID: ZONE 2 (NODES) & ZONE 3 (FILES) -->
    <div class="lower-zones-grid">
      <div id="node-list-root">
        ${renderNodeList(currentHeartbeats.nodes, currentViewState, undefined, selectedNodeId)}
      </div>
      <div id="file-panel-root">
        ${renderFilePanel(
          currentFiles.files,
          currentViewState,
          currentFiles.error || undefined,
          currentFiles.totalFiles,
          currentFiles.totalSizeBytes,
          currentFiles.searchQuery,
          currentFiles.uploadState
        )}
      </div>
    </div>

    <!-- ZERO LAYOUT SHIFT OVERLAY DRAWER CONTAINER -->
    <div id="node-detail-root">
      ${renderNodeDetailPanel({
        nodeId: selectedNodeId,
        nodeDetail: selectedNodeDetail,
        latencyMs: selectedNodeLatency,
        isOpen: selectedNodeId !== null,
        state: isDetailLoading ? 'loading' : detailErrorMessage ? 'error' : 'normal',
        errorMessage: detailErrorMessage,
      })}
    </div>
  `;

  attachStateSwitcherListeners();
  attachInteractiveNodeSelection();
  attachFilePanelListeners();

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

  // Subscribe to heartbeat rail & node telemetry for Zone 1, Zone 2, and open Node Detail Panel live synchronization
  heartbeatService.subscribe((result) => {
    if (currentViewState !== 'normal') return;
    updateHeartbeatRailDOM(result.nodes, selectedNodeId);
    updateNodeListDOM(result.nodes, selectedNodeId);

    // If detail panel is open, update its telemetry in real time
    if (selectedNodeId) {
      const activeNode = result.nodes.find(
        n => n.id.toLowerCase() === selectedNodeId?.toLowerCase() || n.displayName.toLowerCase() === selectedNodeId?.toLowerCase()
      );
      if (activeNode) {
        selectedNodeDetail = {
          id: activeNode.displayName || activeNode.id,
          state: activeNode.state,
          status: activeNode.status,
          last_heartbeat: activeNode.lastHeartbeat,
          url: activeNode.url,
          term: activeNode.state === 'LEADER' ? 4 : 4,
          commit_index: 1042,
        };
        selectedNodeLatency = activeNode.latencyMs;

        updateNodeDetailDOM({
          nodeId: selectedNodeId,
          nodeDetail: selectedNodeDetail,
          latencyMs: selectedNodeLatency,
          isOpen: true,
        });
      }
    }
  });

  // Subscribe to file ledger updates for Zone 3 live synchronization
  fileService.subscribe((result) => {
    if (currentViewState !== 'normal') return;
    updateFilePanelDOM(result.files, result.totalFiles, result.totalSizeBytes, result.searchQuery, result.uploadState);
  });

  // Start routing, health checking, cluster status polling, heartbeat pulse engine, and file ledger polling
  router.start();
  healthService.startPolling(3000);
  clusterStatusService.startPolling(500);
  heartbeatService.startPolling(500);
  fileService.startPolling(3000);

  // Lifecycle listeners to prevent memory leaks
  window.addEventListener('beforeunload', () => {
    clusterStatusService.stopPolling();
    heartbeatService.stopPolling();
    healthService.stopPolling();
    fileService.stopPolling();
  });
}

// Start application on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}



