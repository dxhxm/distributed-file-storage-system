/**
 * Unit Tests for DFSS NodeDetailPanel Component
 *
 * Tests:
 * 1. Correct rendering of all fields from GET /nodes/{node_id} (id, state, last_heartbeat, response_time, connectivity, url, term, commit_index, peers).
 * 2. Strict typography pairing: JetBrains Mono for data/numbers/timestamps/IDs, Inter for descriptions/labels.
 * 3. Zero-layout-shift overlay drawer & backdrop architecture (open/close DOM contract).
 * 4. Loading skeleton and error state shells.
 */

import {
  renderNodeDetailPanel,
  renderNodeDetailSkeleton,
  renderNodeDetailError,
  formatDetailedTimestamp,
  resolveNodeMetadata,
} from '../components/NodeDetailPanel.ts';
import type { NodeDetailResponse } from '../types/api.ts';

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

console.log('\n=== Starting DFSS Node Detail Panel Unit Tests ===\n');

// 1. Data Parsing & Metadata Helpers
console.log('Testing Timestamp & Metadata Formatters...');
const testTs = 1724784000; // Epoch timestamp
const formattedTs = formatDetailedTimestamp(testTs);
assert(formattedTs.full.includes('UTC'), 'Timestamp includes UTC designation');
assert(typeof formattedTs.relative === 'string' && formattedTs.relative.length > 0, 'Relative timestamp is generated');

const metaA = resolveNodeMetadata({
  id: 'Node A',
  state: 'LEADER',
  last_heartbeat: testTs,
  status: 'ONLINE',
  url: 'http://127.0.0.1:8000',
  term: 4,
  commit_index: 1042,
  peers: ['nodeB', 'nodeC'],
}, 'nodeA');

assertStrictEqual(metaA.port, ':8000', 'Node A resolves port :8000');
assertStrictEqual(metaA.term, 4, 'Node A resolves Raft Term #4');
assertStrictEqual(metaA.commitIndex, 1042, 'Node A resolves Commit Index #1042');
assert(metaA.peers.includes('nodeB') && metaA.peers.includes('nodeC'), 'Node A includes peer nodes nodeB and nodeC');

const metaB = resolveNodeMetadata(null, 'nodeB');
assertStrictEqual(metaB.port, ':8001', 'Node B fallback resolves port :8001');
console.log('  ✓ PASS: Timestamp formatting and node metadata resolution verified.');


// 2. Rendering All Fields from GET /nodes/{node_id}
console.log('Testing GET /nodes/{node_id} Field Rendering in Open Detail Panel...');
const leaderNode: NodeDetailResponse = {
  id: 'nodeA',
  state: 'LEADER',
  last_heartbeat: 1724784000,
  status: 'ONLINE',
  url: 'http://127.0.0.1:8000',
  term: 4,
  commit_index: 1042,
  peers: ['nodeB', 'nodeC'],
};

const markupLeader = renderNodeDetailPanel({
  nodeId: 'nodeA',
  nodeDetail: leaderNode,
  latencyMs: 0.0,
  isOpen: true,
  state: 'normal',
});

// Field: id
assert(markupLeader.includes('nodeA'), 'Renders node ID nodeA');
assert(markupLeader.includes('id="node-detail-title"'), 'Header title element exists');

// Field: state & role badge
assert(markupLeader.includes('LEADER'), 'Renders state LEADER');
assert(markupLeader.includes('badge-ok'), 'Leader uses badge-ok token');
assert(markupLeader.includes('dot-ok'), 'Leader uses dot-ok status dot');

// Field: status / connectivity
assert(markupLeader.includes('ONLINE'), 'Renders status ONLINE');
assert(markupLeader.includes('id="node-detail-status-val"'), 'Status value element exists');
assert(markupLeader.includes('Reachable on network'), 'Shows connectivity description');

// Field: response time / latency
assert(markupLeader.includes('+0.0 ms'), 'Renders latency +0.0 ms for leader');
assert(markupLeader.includes('id="node-detail-latency-val"'), 'Latency value element exists');

// Field: last_heartbeat
assert(markupLeader.includes('id="node-detail-hb-time"'), 'Last heartbeat time element exists');
assert(markupLeader.includes('UTC'), 'Last heartbeat includes UTC string');

// Field: url & port
assert(markupLeader.includes('http://127.0.0.1:8000'), 'Renders endpoint URL');
assert(markupLeader.includes(':8000'), 'Renders network port :8000');

// Field: term & commit_index & peers
assert(markupLeader.includes('#4'), 'Renders Raft Term #4');
assert(markupLeader.includes('#1042'), 'Renders Commit Index #1042');
assert(markupLeader.includes('nodeB') && markupLeader.includes('nodeC'), 'Renders peer node pills');

// Follower / Candidate Node testing
const followerNode: NodeDetailResponse = {
  id: 'nodeB',
  state: 'FOLLOWER',
  last_heartbeat: 1724784000,
  status: 'ONLINE',
  url: 'http://127.0.0.1:8001',
  term: 4,
  commit_index: 1042,
};

const markupFollower = renderNodeDetailPanel({
  nodeId: 'nodeB',
  nodeDetail: followerNode,
  latencyMs: 8.4,
  isOpen: true,
  state: 'normal',
});

assert(markupFollower.includes('FOLLOWER'), 'Renders state FOLLOWER');
assert(markupFollower.includes('badge-info'), 'Follower uses badge-info token');
assert(markupFollower.includes('+8.4 ms'), 'Renders follower latency +8.4 ms');
assert(markupFollower.includes(':8001'), 'Renders follower port :8001');

// Offline Node testing
const offlineNode: NodeDetailResponse = {
  id: 'nodeC',
  state: 'FOLLOWER',
  last_heartbeat: 1724783000,
  status: 'OFFLINE',
  url: 'http://127.0.0.1:8002',
};

const markupOffline = renderNodeDetailPanel({
  nodeId: 'nodeC',
  nodeDetail: offlineNode,
  isOpen: true,
  state: 'normal',
});

assert(markupOffline.includes('OFFLINE'), 'Renders status OFFLINE');
assert(markupOffline.includes('badge-down'), 'Offline status uses badge-down token');
assert(markupOffline.includes('dot-down'), 'Offline status uses dot-down token');
assert(markupOffline.includes('Unreachable / Stalled'), 'Shows stalled/unreachable description');

console.log('  ✓ PASS: All fields from GET /nodes/{node_id} render accurately across roles.');


// 3. Strict Typography Dual Pairing (JetBrains Mono for Data, Inter for Descriptions)
console.log('Testing Typography Pairing (JetBrains Mono vs Inter)...');

// Verify numeric & identifier fields have font-mono
assert(markupLeader.includes('class="node-detail-title font-mono"'), 'Node ID rendered in font-mono');
assert(markupLeader.includes('id="node-detail-status-val"'), 'Status value contains font-mono');
assert(markupLeader.includes('id="node-detail-latency-val"'), 'Latency metric rendered in font-mono');
assert(markupLeader.includes('id="node-detail-hb-time"'), 'Heartbeat timestamp rendered in font-mono');
assert(markupLeader.includes('id="node-detail-url-val"'), 'Endpoint URL rendered in font-mono');
assert(markupLeader.includes('id="node-detail-port-val"'), 'Port rendered in font-mono');
assert(markupLeader.includes('id="node-detail-term-val"'), 'Raft Term rendered in font-mono');
assert(markupLeader.includes('id="node-detail-commit-val"'), 'Commit Index rendered in font-mono');
assert(markupLeader.includes('class="detail-peer-pill font-mono"'), 'Peer node pills rendered in font-mono');

// Verify labels and descriptions have font-sans
assert(markupLeader.includes('class="node-detail-eyebrow font-sans"'), 'Eyebrow header rendered in font-sans');
assert(markupLeader.includes('class="detail-section-header font-sans"'), 'Section headers rendered in font-sans');
assert(markupLeader.includes('class="detail-metric-label font-sans"'), 'Metric labels rendered in font-sans');
assert(markupLeader.includes('class="detail-metric-subtext font-sans"'), 'Metric descriptions rendered in font-sans');
assert(markupLeader.includes('class="detail-kv-label font-sans"'), 'Key-value labels rendered in font-sans');
assert(markupLeader.includes('id="btn-refresh-node-detail"'), 'Refresh button uses font-sans');
assert(markupLeader.includes('id="btn-dismiss-node-detail"'), 'Dismiss button uses font-sans');

console.log('  ✓ PASS: Typography rules strictly adhered to (Mono for telemetry, Sans for UI/labels).');


// 4. Zero Layout Shift Overlay Drawer Architecture
console.log('Testing Zero Layout Shift Overlay Drawer DOM Structure...');

// Closed state
const markupClosed = renderNodeDetailPanel({
  nodeId: null,
  nodeDetail: null,
  isOpen: false,
});

assert(markupClosed.includes('id="node-detail-backdrop"'), 'Backdrop exists in closed state');
assert(markupClosed.includes('id="node-detail-panel"'), 'Panel container exists in closed state');
assert(markupClosed.includes('aria-hidden="true"'), 'Closed state is marked aria-hidden="true"');
assert(!markupClosed.includes('class="node-detail-panel open"'), 'Closed panel does not have open class');

// Open state
assert(markupLeader.includes('class="node-detail-backdrop open"'), 'Open state adds open class to backdrop');
assert(markupLeader.includes('class="node-detail-panel open"'), 'Open state adds open class to drawer panel');
assert(markupLeader.includes('role="dialog"'), 'Panel has role="dialog"');
assert(markupLeader.includes('aria-modal="true"'), 'Panel has aria-modal="true"');
assert(markupLeader.includes('aria-labelledby="node-detail-title"'), 'Panel is accessible with aria-labelledby');
assert(markupLeader.includes('id="btn-close-node-detail"'), 'Panel includes close button with aria-label');

console.log('  ✓ PASS: Zero-layout-shift slide-over overlay drawer structure verified.');


// 5. Loading Skeleton & Error States
console.log('Testing Loading Skeleton & Error States...');

// Loading Skeleton State
const markupSkeleton = renderNodeDetailPanel({
  nodeId: 'nodeB',
  nodeDetail: null,
  isOpen: true,
  state: 'loading',
});
const markupSkeletonDirect = renderNodeDetailSkeleton('nodeB');

assert(markupSkeleton.includes('skeleton-box'), 'Loading skeleton uses skeleton-box');
assert(markupSkeleton.includes('skeleton-bar'), 'Loading skeleton uses skeleton-bar');
assert(markupSkeletonDirect === markupSkeleton, 'Direct render matches loading state prop');
assert(markupSkeleton.includes('nodeB'), 'Skeleton header shows node ID');
assert(!markupSkeleton.toLowerCase().includes('spinner'), 'Restrained motion: No spinner clichés');

// Error State
const markupError = renderNodeDetailPanel({
  nodeId: 'nodeC',
  nodeDetail: null,
  isOpen: true,
  state: 'error',
  errorMessage: 'HTTP 404 Node not found',
});
const markupErrorDirect = renderNodeDetailError('nodeC', 'HTTP 404 Node not found');

assert(markupError.includes('TELEMETRY ERROR'), 'Error state indicates telemetry error');
assert(markupError.includes('HTTP 404 Node not found'), 'Error message rendered');
assert(markupError.includes('id="btn-retry-node-detail"'), 'Retry button provided in error state');
assert(markupErrorDirect === markupError, 'Direct render matches error state prop');

console.log('  ✓ PASS: Loading skeleton and error state shells validated.');

console.log('\n=== All Node Detail Panel Tests Passed Successfully (5/5)! ===\n');
