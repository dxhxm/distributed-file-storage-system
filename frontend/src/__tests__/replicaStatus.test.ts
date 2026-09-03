/**
 * Unit & Integration Tests for DFSS Replica Status Display & Cluster State Integration
 */

import {
  findNodeForTarget,
  renderClusterNoticeBanner,
  renderFileRow,
  renderFilePanel,
} from '../components/FilePanel.ts';
import type { FileInfo } from '../types/api.ts';

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

function assertStrictEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) {
    throw new Error(`Expected ${String(expected)}, but got ${String(actual)}. ${message}`);
  }
}

console.log('\n=== Starting DFSS Replica Status Display & Cluster State Tests ===\n');

// 1. Test findNodeForTarget
console.log('Testing findNodeForTarget helper...');

const mockNodes = [
  { id: 'nodeA', displayName: 'Node A', state: 'LEADER', status: 'ONLINE' },
  { id: 'nodeB', displayName: 'Node B', state: 'FOLLOWER', status: 'OFFLINE' },
  { id: 'nodeC', displayName: 'Node C', state: 'FOLLOWER', status: 'ONLINE' },
];

const targetA = findNodeForTarget(mockNodes, 'A');
assertStrictEqual(targetA.isOnline, true, 'Node A is online');
assertStrictEqual(targetA.isLeader, true, 'Node A is leader');
assertStrictEqual(targetA.status, 'ONLINE', 'Node A status is ONLINE');

const targetB = findNodeForTarget(mockNodes, 'B');
assertStrictEqual(targetB.isOnline, false, 'Node B is offline');
assertStrictEqual(targetB.isLeader, false, 'Node B is follower');
assertStrictEqual(targetB.status, 'OFFLINE', 'Node B status is OFFLINE');

const targetC = findNodeForTarget(mockNodes, 'C');
assertStrictEqual(targetC.isOnline, true, 'Node C is online');

console.log('  ✓ PASS: findNodeForTarget accurately resolves node status and consensus roles.');

// 2. Test renderClusterNoticeBanner
console.log('Testing renderClusterNoticeBanner for consensus paused explanations...');

const healthyBanner = renderClusterNoticeBanner('HEALTHY');
assertStrictEqual(healthyBanner, '', 'HEALTHY cluster state produces no banner');

const operationalBanner = renderClusterNoticeBanner('OPERATIONAL');
assert(operationalBanner.includes('QUORUM DEGRADED'), 'OPERATIONAL banner includes QUORUM DEGRADED badge');
assert(operationalBanner.includes('1 node offline'), 'OPERATIONAL banner explains 1 node is offline');

const noMajorityBanner = renderClusterNoticeBanner('NO MAJORITY');
assert(noMajorityBanner.includes('CONSENSUS PAUSED'), 'NO MAJORITY banner explicitly includes CONSENSUS PAUSED badge');
assert(
  noMajorityBanner.includes('Quorum majority lost') && noMajorityBanner.includes('Consensus replication and mutations are paused'),
  'NO MAJORITY banner clearly explains consensus is paused, not system down'
);
assert(
  noMajorityBanner.includes('Existing replicas on active nodes remain downloadable'),
  'NO MAJORITY banner confirms existing replicas remain accessible'
);

console.log('  ✓ PASS: Cluster notice banner explicitly clarifies NO MAJORITY consensus paused semantics.');

// 3. Test renderFileRow with All Active Replicas
console.log('Testing renderFileRow with fully healthy replicas...');

const allOnlineNodes = [
  { id: 'nodeA', displayName: 'Node A', state: 'LEADER', status: 'ONLINE' },
  { id: 'nodeB', displayName: 'Node B', state: 'FOLLOWER', status: 'ONLINE' },
  { id: 'nodeC', displayName: 'Node C', state: 'FOLLOWER', status: 'ONLINE' },
];

const testFile: FileInfo = {
  file_id: 'f-100',
  name: 'cluster_manifest.json',
  size: 2048,
  replicas: ['Node A', 'Node B', 'Node C'],
  status: 'REPLICATED',
  modified_at: 1724784000,
};

const healthyRowHtml = renderFileRow(testFile, null, null, allOnlineNodes, 'HEALTHY');
assert(healthyRowHtml.includes('REPLICATED (3/3)'), 'Shows REPLICATED (3/3) when all replicas are online');
assert(healthyRowHtml.includes('replica-leader'), 'Leader replica pill includes replica-leader class');
assert(healthyRowHtml.includes('Active replica reachable'), 'Pill tooltips indicate reachable active replica');
assert(!healthyRowHtml.includes('replica-offline'), 'No replica-offline class when all nodes are healthy');

console.log('  ✓ PASS: Fully replicated file displays 3/3 reachable count and leader indication.');

// 4. Test renderFileRow with Degraded Replicas (Node B OFFLINE)
console.log('Testing renderFileRow when a holding node is OFFLINE...');

const degradedNodes = [
  { id: 'nodeA', displayName: 'Node A', state: 'LEADER', status: 'ONLINE' },
  { id: 'nodeB', displayName: 'Node B', state: 'FOLLOWER', status: 'OFFLINE' },
  { id: 'nodeC', displayName: 'Node C', state: 'FOLLOWER', status: 'ONLINE' },
];

const degradedRowHtml = renderFileRow(testFile, null, null, degradedNodes, 'OPERATIONAL');
assert(degradedRowHtml.includes('DEGRADED (2/3)'), 'Reflects 2/3 reachable replica count when Node B is offline');
assert(degradedRowHtml.includes('replica-offline'), 'Applies replica-offline styling to offline node pill');
assert(degradedRowHtml.includes('Node B (OFFLINE)'), 'Tooltip explicitly notes Node B is OFFLINE');
assert(degradedRowHtml.includes('btn-download-file') && !degradedRowHtml.includes('disabled'), 'Download remains enabled with 2 active replicas');

console.log('  ✓ PASS: Degraded cluster accurately updates per-file reachable count and offline pill styling.');

// 5. Test renderFileRow when ALL replica nodes are OFFLINE
console.log('Testing renderFileRow when ALL holding nodes are OFFLINE...');

const allOfflineNodes = [
  { id: 'nodeA', displayName: 'Node A', state: 'LEADER', status: 'OFFLINE' },
  { id: 'nodeB', displayName: 'Node B', state: 'FOLLOWER', status: 'OFFLINE' },
  { id: 'nodeC', displayName: 'Node C', state: 'FOLLOWER', status: 'OFFLINE' },
];

const offlineRowHtml = renderFileRow(testFile, null, null, allOfflineNodes, 'NO MAJORITY');
assert(offlineRowHtml.includes('UNREACHABLE (0/3)'), 'Displays UNREACHABLE (0/3) when all holding nodes are offline');
assert(offlineRowHtml.includes('All replica nodes are offline'), 'Download action is disabled with explanatory tooltip');

console.log('  ✓ PASS: Unreachable file correctly disables download and surfaces 0/3 count.');

// 6. Test renderFilePanel with Cluster Notice Banner Slot
console.log('Testing renderFilePanel integration with cluster notice banner...');

const panelHtml = renderFilePanel([testFile], 'normal', undefined, 1, 2048, '', null, null, null, mockNodes, 'NO MAJORITY');
assert(panelHtml.includes('cluster-notice-slot'), 'File panel contains cluster-notice-slot');
assert(panelHtml.includes('CONSENSUS PAUSED'), 'File panel renders consensus paused notice under NO MAJORITY');

console.log('  ✓ PASS: File panel seamlessly integrates cluster notice banner and replica status.');

console.log('\n=== All Replica Status & Cluster Integration Tests Passed Successfully (6/6)! ===\n');
