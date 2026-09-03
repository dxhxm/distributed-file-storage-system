/**
 * Unit & Systems Verification Tests for DFSS Failure States & NO MAJORITY Copy Semantics
 *
 * Requirements & DoD:
 * 1. Every failure state in the app has specific, accurate copy tied to what actually happened.
 * 2. NO MAJORITY state clearly explains consensus is paused, not 'system down'.
 * 3. Copy reviewed for tone consistency with the rest of the UI.
 */

import {
  resolveHealthIndicatorStyle,
  renderClusterHealthIndicator,
} from '../components/ClusterHealthIndicator.ts';
import {
  renderClusterStatus,
  renderClusterStatusError,
} from '../components/ClusterStatus.ts';
import {
  renderNodeRow,
  renderNodeList,
  renderNodeListError,
} from '../components/NodeList.ts';
import {
  renderHeartbeatLane,
  renderHeartbeatRailError,
} from '../components/HeartbeatRail.ts';
import {
  renderNodeDetailPanel,
} from '../components/NodeDetailPanel.ts';
import {
  renderClusterNoticeBanner,
} from '../components/FilePanel.ts';

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

console.log('\n=== Starting DFSS Systems Failure Copy & NO MAJORITY Verification Tests ===\n');

// 1. NO MAJORITY State: Clearly Explains Consensus Is Paused, Not 'System Down'
console.log('Testing NO MAJORITY state copy semantics across components...');

// A. ClusterHealthIndicator under NO MAJORITY
const healthIndicatorStyle = resolveHealthIndicatorStyle('NO MAJORITY', 'NONE');
assert(
  healthIndicatorStyle.tooltip.includes('Consensus Paused') &&
  healthIndicatorStyle.tooltip.includes('Active nodes serve local reads'),
  'ClusterHealthIndicator tooltip explicitly explains consensus is paused and reads continue'
);
assert(
  !healthIndicatorStyle.tooltip.toLowerCase().includes('system down'),
  'Does not describe NO MAJORITY as system down'
);

const healthIndicatorHtml = renderClusterHealthIndicator('NO MAJORITY', 'NONE', 'normal');
assert(healthIndicatorHtml.includes('title="Consensus Paused:'), 'Markup carries explicit consensus paused tooltip');

// B. ClusterStatus Telemetry Strip under NO MAJORITY
const clusterStatusHtml = renderClusterStatus(
  {
    cluster_state: 'NO MAJORITY',
    leader_id: null,
    term: 4,
    commit_index: 1042,
    active_nodes: 1,
    total_nodes: 3,
    timestamp: Date.now(),
  },
  'CONNECTED'
);
assert(clusterStatusHtml.includes('1/3 (PAUSED)'), 'Quorum metric displays (PAUSED) under NO MAJORITY');
assert(
  clusterStatusHtml.includes('Consensus paused: Quorum majority lost') &&
  clusterStatusHtml.includes('local reads permitted'),
  'Quorum metric tooltip explains consensus is paused while local reads remain permitted'
);

// C. FilePanel Banner under NO MAJORITY
const noticeBannerHtml = renderClusterNoticeBanner('NO MAJORITY');
assert(
  noticeBannerHtml.includes('CONSENSUS PAUSED') &&
  noticeBannerHtml.includes('Quorum majority lost') &&
  noticeBannerHtml.includes('Existing replicas on active nodes remain downloadable'),
  'File panel banner clearly explains mutations are paused to prevent split-brain while replicas remain downloadable'
);

// D. NodeList Caption under NO MAJORITY
const nodeListHtml = renderNodeList(
  [
    { id: 'nodeA', displayName: 'nodeA', state: 'FOLLOWER', status: 'ONLINE', last_heartbeat: Date.now() / 1000, latencyMs: 0, port: ':8000' },
    { id: 'nodeB', displayName: 'nodeB', state: 'FOLLOWER', status: 'OFFLINE', last_heartbeat: 0, latencyMs: 0, port: ':8001' },
    { id: 'nodeC', displayName: 'nodeC', state: 'FOLLOWER', status: 'OFFLINE', last_heartbeat: 0, latencyMs: 0, port: ':8002' },
  ],
  'normal'
);
assert(
  nodeListHtml.includes('Consensus paused — quorum lost (1/3 active)'),
  'Node list caption explicitly states consensus paused under quorum loss'
);

console.log('  ✓ PASS: NO MAJORITY state uniformly communicates consensus paused (not system down) across all zones.');

// 2. Specific, Accurate Copy Tied to Real Failure Events
console.log('Testing specific failure copy for offline nodes, heartbeat stalls, and connectivity drops...');

// A. Node List Offline Node Row
const offlineNode = {
  id: 'nodeB',
  displayName: 'nodeB',
  state: 'FOLLOWER' as const,
  status: 'OFFLINE' as const,
  last_heartbeat: 0,
  latencyMs: 0,
  port: ':8001',
};
const nodeRowHtml = renderNodeRow(offlineNode);
assert(
  nodeRowHtml.includes('Heartbeat missed (>1.5s)') &&
  nodeRowHtml.includes('Node unresponsive on :8001') &&
  nodeRowHtml.includes('Replicas hosted on this node are temporarily unreachable'),
  'Node row status tooltip provides specific port, heartbeat threshold, and replica reachability impact'
);

// B. Heartbeat Pulse Stalled Lane
const pulseLaneHtml = renderHeartbeatLane({
  id: 'nodeB',
  displayName: 'nodeB',
  state: 'FOLLOWER' as const,
  status: 'OFFLINE' as const,
  lastHeartbeat: 0,
  latencyMs: 0,
  port: ':8001',
  isPulsing: false,
  history: Array(20).fill('missed'),
  consecutiveMissed: 5,
});
assert(
  pulseLaneHtml.includes('Pulse Stalled for nodeB: Missed heartbeats (>1.5s). Node unresponsive on :8001.'),
  'Heartbeat lane tooltip provides specific stall explanation and port info'
);

// C. Node Detail Panel Offline Status
const detailHtml = renderNodeDetailPanel({
  nodeId: 'nodeB',
  nodeDetail: {
    id: 'nodeB',
    state: 'FOLLOWER',
    status: 'OFFLINE',
    last_heartbeat: 0,
    url: 'http://127.0.0.1:8001',
  },
  isOpen: true,
  state: 'normal',
});
assert(
  detailHtml.includes('Unreachable / Stalled (>1.5s missed). Cannot participate in consensus or serve replicas.'),
  'Node detail panel connectivity metric gives precise systems failure detail'
);

// D. Coordinator Unreachable Error (ClusterStatus & HeartbeatRail & NodeList)
const clusterErrHtml = renderClusterStatusError();
assert(
  clusterErrHtml.includes('Coordinator unreachable: Cannot connect to nodeA HTTP API on port 8000') &&
  clusterErrHtml.includes('Process may be stopped or port in use'),
  'Cluster status error specifically names port 8000 and diagnostic step'
);

const railErrHtml = renderHeartbeatRailError();
assert(
  railErrHtml.includes('Coordinator at port 8000 is unreachable'),
  'Heartbeat rail error specifies port 8000 coordinator disconnection'
);

const nodeListErrHtml = renderNodeListError();
assert(
  nodeListErrHtml.includes('HTTP 503') &&
  nodeListErrHtml.includes('Coordinator returned HTTP 503 Service Unavailable'),
  'Node list error surfaces exact HTTP 503 status code'
);

console.log('  ✓ PASS: Every failure state carries specific, accurate systems copy tied to what actually happened.');

// 3. Quorum Degraded Copy (OPERATIONAL State)
console.log('Testing degraded consensus copy (OPERATIONAL state)...');

const operationalClusterHtml = renderClusterStatus(
  {
    cluster_state: 'OPERATIONAL',
    leader_id: 'nodeA',
    term: 4,
    commit_index: 1042,
    active_nodes: 2,
    total_nodes: 3,
    timestamp: Date.now(),
  },
  'CONNECTED'
);
assert(
  operationalClusterHtml.includes('2/3 (DEGRADED)'),
  'Quorum displays (DEGRADED) when 1 node is offline'
);
assert(
  operationalClusterHtml.includes('Single fault tolerance remaining'),
  'Quorum tooltip clarifies single fault tolerance remaining'
);

const operationalNoticeHtml = renderClusterNoticeBanner('OPERATIONAL');
assert(
  operationalNoticeHtml.includes('QUORUM DEGRADED') &&
  operationalNoticeHtml.includes('Majority quorum preserved; consensus transactions remain active'),
  'Notice banner informs user that transactions remain active despite 1 offline node'
);

console.log('  ✓ PASS: Degraded quorum state copy is technically accurate and reassuring.');

console.log('\n=== All Systems Failure Copy Verification Tests Passed Successfully (3/3)! ===\n');
