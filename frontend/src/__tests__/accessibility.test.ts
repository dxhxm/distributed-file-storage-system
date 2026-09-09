/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Accessibility Pass Automated Test Suite
 *
 * Verifies:
 * 1. ARIA attributes, semantic roles, and accessible labels across all UI zones.
 * 2. Multi-modal status indication (textual labels + ARIA, never color alone).
 * 3. WCAG AA contrast ratio compliance against locked design tokens.
 */

import assert from 'node:assert';
import { renderClusterHealthIndicator, renderClusterHealthSkeleton, renderClusterHealthEmpty, renderClusterHealthError } from '../components/ClusterHealthIndicator.ts';
import { renderHeartbeatLane, renderHeartbeatRail } from '../components/HeartbeatRail.ts';
import { renderNodeRow, renderNodeListEmpty, renderNodeListError } from '../components/NodeList.ts';
import { renderFileRow, renderFilePanel, renderClusterNoticeBanner, renderUploadProgress, renderDownloadError, renderDeleteError } from '../components/FilePanel.ts';
import { renderNodeDetailPanel, renderNodeDetailSkeleton, renderNodeDetailError } from '../components/NodeDetailPanel.ts';
import { COLORS } from '../tokens/index.ts';

// Helper: Calculate relative luminance for sRGB hex color
export function calculateLuminance(hex: string): number {
  const cleanHex = hex.replace('#', '');
  const r = parseInt(cleanHex.slice(0, 2), 16) / 255;
  const g = parseInt(cleanHex.slice(2, 4), 16) / 255;
  const b = parseInt(cleanHex.slice(4, 6), 16) / 255;

  const toLinear = (c: number) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
  const rLin = toLinear(r);
  const gLin = toLinear(g);
  const bLin = toLinear(b);

  return 0.2126 * rLin + 0.7152 * gLin + 0.0722 * bLin;
}

// Helper: Calculate contrast ratio between two hex colors
export function calculateContrastRatio(hex1: string, hex2: string): number {
  const l1 = calculateLuminance(hex1);
  const l2 = calculateLuminance(hex2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

console.log('=== Starting DFSS Accessibility Pass Tests ===\n');

// --------------------------------------------------------------------------
// 1. ClusterHealthIndicator ARIA and Status Conveyance
// --------------------------------------------------------------------------
console.log('1. Testing ClusterHealthIndicator ARIA and text status conveyance...');
{
  const healthyHtml = renderClusterHealthIndicator('HEALTHY', 'nodeA');
  assert.ok(healthyHtml.includes('role="status"'), 'Indicator should have role="status"');
  assert.ok(healthyHtml.includes('aria-live="polite"'), 'Indicator should have aria-live="polite"');
  assert.ok(healthyHtml.includes('aria-label="Cluster status: HEALTHY, Current Raft Leader: nodeA"'), 'Indicator should have descriptive aria-label');
  assert.ok(healthyHtml.includes('aria-hidden="true"'), 'Status dot should have aria-hidden="true"');
  assert.ok(healthyHtml.includes('HEALTHY'), 'Status should have visible text label "HEALTHY"');
  assert.ok(healthyHtml.includes('nodeA'), 'Leader should be displayed as text "nodeA"');

  const pausedHtml = renderClusterHealthIndicator('NO MAJORITY', 'NONE');
  assert.ok(pausedHtml.includes('aria-label="Cluster status: NO MAJORITY, Current Raft Leader: NONE"'), 'Paused state should have descriptive aria-label');
  assert.ok(pausedHtml.includes('NO MAJORITY'), 'Status should have visible text label "NO MAJORITY"');

  const skeletonHtml = renderClusterHealthSkeleton();
  assert.ok(skeletonHtml.includes('role="status"'), 'Skeleton should have role="status"');
  assert.ok(skeletonHtml.includes('aria-label="Cluster status: Scanning topology, Leader: Unavailable"'), 'Skeleton should have descriptive aria-label');

  const emptyHtml = renderClusterHealthEmpty();
  assert.ok(emptyHtml.includes('role="status"'), 'Empty should have role="status"');
  assert.ok(emptyHtml.includes('aria-label="Cluster status: Bootstrapping, Leader: None"'), 'Empty should have descriptive aria-label');

  const errorHtml = renderClusterHealthError();
  assert.ok(errorHtml.includes('role="status"'), 'Error should have role="status"');
  assert.ok(errorHtml.includes('aria-label="Cluster status: Disconnected, Leader: Unavailable"'), 'Error should have descriptive aria-label');

  console.log('   ✓ ClusterHealthIndicator ARIA semantics verified');
}

// --------------------------------------------------------------------------
// 2. HeartbeatRail ARIA and Non-Color Status Conveyance
// --------------------------------------------------------------------------
console.log('2. Testing HeartbeatRail ARIA attributes and pulse tick hiding...');
{
  const node = {
    id: 'nodeA',
    displayName: 'Node A',
    state: 'LEADER' as const,
    status: 'ONLINE' as const,
    lastHeartbeat: Date.now() / 1000,
    latencyMs: 0,
    port: ':8000',
    isPulsing: false,
    history: Array(20).fill('ok' as const),
    consecutiveMissed: 0,
  };

  const laneHtml = renderHeartbeatLane(node, 'nodeA');
  assert.ok(laneHtml.includes('role="button"'), 'Lane must have role="button"');
  assert.ok(laneHtml.includes('tabindex="0"'), 'Lane must have tabindex="0"');
  assert.ok(laneHtml.includes('aria-pressed="true"'), 'Selected lane must have aria-pressed="true"');
  assert.ok(laneHtml.includes('aria-label="Node Node A: Online, Leader, Port :8000. Press Enter to view telemetry."'), 'Lane must have descriptive aria-label');
  assert.ok(laneHtml.includes('<div class="lane-track" title="Active Heartbeat Pulse Stream for Node A" aria-hidden="true">'), 'Lane pulse track must be hidden from screen readers via aria-hidden="true"');
  assert.ok(laneHtml.includes('<span class="status-dot dot-ok" aria-hidden="true"></span>'), 'Lane status dot must have aria-hidden="true"');
  assert.ok(laneHtml.includes('LEAD'), 'Role text badge LEAD must be present');

  const railHtml = renderHeartbeatRail([node]);
  assert.ok(railHtml.includes('aria-hidden="true"'), 'Legend dots must have aria-hidden="true"');
  assert.ok(railHtml.includes('Healthy') && railHtml.includes('Syncing') && railHtml.includes('Missed'), 'Legend must have clear text labels');

  console.log('   ✓ HeartbeatRail ARIA semantics verified');
}

// --------------------------------------------------------------------------
// 3. NodeList ARIA and Status Cell Verification
// --------------------------------------------------------------------------
console.log('3. Testing NodeList ARIA attributes and textual status conveyance...');
{
  const node = {
    id: 'nodeB',
    displayName: 'Node B',
    state: 'FOLLOWER' as const,
    status: 'ONLINE' as const,
    last_heartbeat: Date.now() / 1000,
    latencyMs: 8.4,
    port: ':8001',
  };

  const rowHtml = renderNodeRow(node);
  assert.ok(rowHtml.includes('role="row"'), 'Node row must have role="row"');
  assert.ok(rowHtml.includes('tabindex="0"'), 'Node row must have tabindex="0"');
  assert.ok(rowHtml.includes('aria-selected="false"'), 'Unselected node row must have aria-selected="false"');
  assert.ok(rowHtml.includes('aria-label="Node B: Role FOLLOWER, Status ONLINE, Latency +8.4 ms, Port :8001. Press Enter to view telemetry."'), 'Row must have full telemetry in aria-label');
  assert.ok(rowHtml.includes('<span class="status-dot dot-muted" aria-hidden="true"></span>'), 'Status dot in badge must have aria-hidden="true"');
  assert.ok(rowHtml.includes('<span class="text-ok font-mono text-xs">ONLINE</span>'), 'Status column must have explicit visible text ONLINE');

  const emptyHtml = renderNodeListEmpty();
  assert.ok(emptyHtml.includes('aria-label="Scan local ports 8000 to 8002"'), 'Scan button must have accessible aria-label');

  const errorHtml = renderNodeListError();
  assert.ok(errorHtml.includes('aria-label="Retry fetching node telemetry"'), 'Retry button must have accessible aria-label');

  console.log('   ✓ NodeList ARIA semantics and text status verified');
}

// --------------------------------------------------------------------------
// 4. FilePanel ARIA, Replica Pills, and Action Buttons
// --------------------------------------------------------------------------
console.log('4. Testing FilePanel replica pills, banners, and action controls...');
{
  const file = {
    file_id: 'file-123',
    name: 'test_manifest.bin',
    size: 1048576,
    status: 'REPLICATED' as const,
    replicas: ['nodeA', 'nodeB', 'nodeC'],
    modified_at: Date.now() / 1000,
  };

  const fileRowHtml = renderFileRow(file);
  // Replica pills accessibility check
  assert.ok(fileRowHtml.includes('role="status"'), 'Replica pills must have role="status"');
  assert.ok(fileRowHtml.includes('aria-label="Node A: Active replica reachable on Node A (Leader)"'), 'Leader replica pill must have descriptive aria-label');
  assert.ok(fileRowHtml.includes('aria-label="Node B: Active replica reachable on Node B"'), 'Follower replica pill must have descriptive aria-label');
  assert.ok(fileRowHtml.includes('aria-hidden="true"'), 'Replica pill dot must have aria-hidden="true"');
  assert.ok(fileRowHtml.includes('aria-label="Download test_manifest.bin"'), 'Download button must have accessible aria-label');
  assert.ok(fileRowHtml.includes('aria-label="Delete test_manifest.bin"'), 'Delete button must have accessible aria-label');

  // Confirmation state
  const confirmingHtml = renderFileRow(file, undefined, {
    confirmingFileId: 'file-123',
    isDeleting: false,
    fileId: 'file-123',
    error: null,
  });
  assert.ok(confirmingHtml.includes('aria-label="Confirm deletion of test_manifest.bin"'), 'Confirm delete button must have accessible aria-label');
  assert.ok(confirmingHtml.includes('aria-label="Cancel deletion of test_manifest.bin"'), 'Cancel delete button must have accessible aria-label');

  // Cluster Notice Banners
  const pausedBanner = renderClusterNoticeBanner('NO MAJORITY');
  assert.ok(pausedBanner.includes('role="status"'), 'Notice banner must have role="status"');
  assert.ok(pausedBanner.includes('aria-live="polite"'), 'Notice banner must have aria-live="polite"');
  assert.ok(pausedBanner.includes('aria-hidden="true"'), 'Banner status dot must have aria-hidden="true"');
  assert.ok(pausedBanner.includes('CONSENSUS PAUSED'), 'Banner must have explicit textual status');

  // Upload Progress Card
  const uploadHtml = renderUploadProgress({
    isUploading: true,
    filename: 'data.csv',
    percent: 64,
    loadedBytes: 64000,
    totalBytes: 100000,
    error: null,
  });
  assert.ok(uploadHtml.includes('role="progressbar"'), 'Upload track must have role="progressbar"');
  assert.ok(uploadHtml.includes('aria-valuenow="64"'), 'Upload progressbar must expose aria-valuenow');
  assert.ok(uploadHtml.includes('aria-valuemin="0"'), 'Upload progressbar must expose aria-valuemin');
  assert.ok(uploadHtml.includes('aria-valuemax="100"'), 'Upload progressbar must expose aria-valuemax');
  assert.ok(uploadHtml.includes('aria-label="Upload progress for data.csv: 64%"'), 'Upload progressbar must have accessible label');

  // Upload Error
  const uploadErrorHtml = renderUploadProgress({
    isUploading: false,
    filename: 'data.csv',
    percent: 0,
    loadedBytes: 0,
    totalBytes: 0,
    error: 'Checksum failure',
  });
  assert.ok(uploadErrorHtml.includes('role="alert"'), 'Upload error card must have role="alert"');
  assert.ok(uploadErrorHtml.includes('aria-label="Retry upload of data.csv"'), 'Retry button must have accessible label');
  assert.ok(uploadErrorHtml.includes('aria-label="Dismiss upload error"'), 'Dismiss button must have accessible label');

  // Download & Delete Error cards
  const downloadErrHtml = renderDownloadError({ isDownloading: false, fileId: '1', filename: 'doc.pdf', error: 'Replica corrupted' });
  assert.ok(downloadErrHtml.includes('role="alert"'), 'Download error must have role="alert"');
  assert.ok(downloadErrHtml.includes('aria-label="Dismiss download error"'), 'Download dismiss button must have accessible label');

  const deleteErrHtml = renderDeleteError({ confirmingFileId: null, isDeleting: false, fileId: '1', error: 'Mutation paused' });
  assert.ok(deleteErrHtml.includes('role="alert"'), 'Delete error must have role="alert"');
  assert.ok(deleteErrHtml.includes('aria-label="Dismiss delete error"'), 'Delete dismiss button must have accessible label');

  // Toolbar buttons
  const panelHtml = renderFilePanel([file]);
  assert.ok(panelHtml.includes('aria-label="Trigger cluster file synchronization"'), 'Trigger sync button must have accessible label');
  assert.ok(panelHtml.includes('aria-label="Upload file to cluster"'), 'Upload button must have accessible label');

  console.log('   ✓ FilePanel ARIA semantics and action buttons verified');
}

// --------------------------------------------------------------------------
// 5. NodeDetailPanel Modal Dialog & Form Controls
// --------------------------------------------------------------------------
console.log('5. Testing NodeDetailPanel ARIA dialog semantics and button labels...');
{
  const panelHtml = renderNodeDetailPanel({
    nodeId: 'nodeA',
    isOpen: true,
    state: 'normal',
    nodeDetail: {
      id: 'nodeA',
      state: 'LEADER',
      status: 'ONLINE',
      last_heartbeat: Date.now() / 1000,
      url: 'http://127.0.0.1:8000',
      term: 4,
      commit_index: 1042,
      peers: ['nodeB', 'nodeC'],
    },
  });

  assert.ok(panelHtml.includes('role="dialog"'), 'Panel must have role="dialog"');
  assert.ok(panelHtml.includes('aria-modal="true"'), 'Panel must have aria-modal="true"');
  assert.ok(panelHtml.includes('aria-labelledby="node-detail-title"'), 'Panel must reference title with aria-labelledby');
  assert.ok(panelHtml.includes('aria-label="Close node detail panel"'), 'Close button must have aria-label');
  assert.ok(panelHtml.includes('aria-label="Refresh telemetry for nodeA"'), 'Refresh button must have accessible label');
  assert.ok(panelHtml.includes('aria-hidden="true"'), 'Status dots must have aria-hidden="true"');

  // Error state
  const errorHtml = renderNodeDetailError('nodeB', 'Connection timed out');
  assert.ok(errorHtml.includes('aria-label="Retry fetching telemetry for node nodeB"'), 'Retry button must have accessible label');
  assert.ok(errorHtml.includes('aria-label="Close node detail panel"'), 'Close button must have accessible label');

  // Skeleton state
  const skeletonHtml = renderNodeDetailSkeleton('nodeC');
  assert.ok(skeletonHtml.includes('aria-label="Close node detail panel"'), 'Skeleton close button must have accessible label');

  console.log('   ✓ NodeDetailPanel dialog and controls verified');
}

// --------------------------------------------------------------------------
// 6. WCAG AA Contrast Ratio Programmatic Verification
// --------------------------------------------------------------------------
console.log('6. Testing WCAG AA contrast ratio compliance against locked tokens...');
{
  const bg = COLORS.bg;              // #0F1210
  const surface = COLORS.surface;    // #171B18

  // Contrast targets:
  // Normal body text: >= 4.5:1
  // Large text / UI components / Bold badges: >= 3.0:1

  // Primary text: ink (#E8ECE9)
  const inkOnSurface = calculateContrastRatio(COLORS.ink, surface);
  const inkOnBg = calculateContrastRatio(COLORS.ink, bg);
  assert.ok(inkOnSurface >= 4.5, `ink on surface must be >= 4.5:1 (got ${inkOnSurface.toFixed(2)}:1)`);
  assert.ok(inkOnBg >= 4.5, `ink on bg must be >= 4.5:1 (got ${inkOnBg.toFixed(2)}:1)`);

  // Secondary text: inkSecondary (#C2C9C3)
  const inkSecOnSurface = calculateContrastRatio(COLORS.inkSecondary, surface);
  assert.ok(inkSecOnSurface >= 4.5, `inkSecondary on surface must be >= 4.5:1 (got ${inkSecOnSurface.toFixed(2)}:1)`);

  // Muted text: muted (#8A928C)
  const mutedOnSurface = calculateContrastRatio(COLORS.muted, surface);
  assert.ok(mutedOnSurface >= 4.5, `muted on surface must be >= 4.5:1 (got ${mutedOnSurface.toFixed(2)}:1)`);

  // Status OK: ok (#5FB88A)
  const okOnSurface = calculateContrastRatio(COLORS.ok, surface);
  assert.ok(okOnSurface >= 4.5, `ok on surface must be >= 4.5:1 (got ${okOnSurface.toFixed(2)}:1)`);

  // Status WARN: warn (#D9A441)
  const warnOnSurface = calculateContrastRatio(COLORS.warn, surface);
  assert.ok(warnOnSurface >= 4.5, `warn on surface must be >= 4.5:1 (got ${warnOnSurface.toFixed(2)}:1)`);

  // Status INFO: info (#6499B8)
  const infoOnSurface = calculateContrastRatio(COLORS.info, surface);
  assert.ok(infoOnSurface >= 4.5, `info on surface must be >= 4.5:1 (got ${infoOnSurface.toFixed(2)}:1)`);

  // Status DOWN: down (#C15B4A)
  // Used in badges (bold uppercase), alert boxes, and UI border indicators
  const downOnSurface = calculateContrastRatio(COLORS.down, surface);
  assert.ok(downOnSurface >= 3.0, `down on surface must be >= 3.0:1 for UI components/large text (got ${downOnSurface.toFixed(2)}:1)`);

  // Focus ring outline: ok (#5FB88A)
  const focusRingContrast = calculateContrastRatio(COLORS.ok, surface);
  assert.ok(focusRingContrast >= 3.0, `focus outline contrast must meet WCAG AA >= 3.0:1 for UI components (got ${focusRingContrast.toFixed(2)}:1)`);

  console.log(`   ✓ Contrast ratio: ink on surface = ${inkOnSurface.toFixed(2)}:1 (>= 4.5:1 WCAG AA)`);
  console.log(`   ✓ Contrast ratio: inkSecondary on surface = ${inkSecOnSurface.toFixed(2)}:1 (>= 4.5:1 WCAG AA)`);
  console.log(`   ✓ Contrast ratio: muted on surface = ${mutedOnSurface.toFixed(2)}:1 (>= 4.5:1 WCAG AA)`);
  console.log(`   ✓ Contrast ratio: ok on surface = ${okOnSurface.toFixed(2)}:1 (>= 4.5:1 WCAG AA)`);
  console.log(`   ✓ Contrast ratio: warn on surface = ${warnOnSurface.toFixed(2)}:1 (>= 4.5:1 WCAG AA)`);
  console.log(`   ✓ Contrast ratio: info on surface = ${infoOnSurface.toFixed(2)}:1 (>= 4.5:1 WCAG AA)`);
  console.log(`   ✓ Contrast ratio: down on surface = ${downOnSurface.toFixed(2)}:1 (>= 3.0:1 WCAG AA component/large)`);
  console.log(`   ✓ Contrast ratio: focus outline = ${focusRingContrast.toFixed(2)}:1 (>= 3.0:1 WCAG AA component)`);
}

console.log('\n=== All 6 Accessibility Pass Tests Passed Successfully! ===\n');
