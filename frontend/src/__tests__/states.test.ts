/**
 * Unit Tests for DFSS Visual States: Loading Skeletons, Empty States & Error States
 */

import {
  renderClusterStatus,
  renderClusterStatusSkeleton,
  renderClusterStatusEmpty,
  renderClusterStatusError,
  renderHeartbeatRail,
  renderHeartbeatRailSkeleton,
  renderHeartbeatRailEmpty,
  renderHeartbeatRailError,
  renderNodeList,
  renderNodeListSkeleton,
  renderNodeListEmpty,
  renderNodeListError,
  renderFilePanel,
  renderFilePanelSkeleton,
  renderFilePanelEmpty,
  renderFilePanelError,
} from '../components/index.ts';

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

console.log('\n=== Starting DFSS Visual State Shells Tests ===\n');

// 1. Zone 1: Cluster Status & Heartbeat Rail States
console.log('Testing Zone 1 (Cluster Status & Heartbeat Rail) States...');

// Loading Skeleton
const csSkeleton = renderClusterStatus(null, 'CONNECTED', 0, 'loading');
const csSkeletonDirect = renderClusterStatusSkeleton();
assert(csSkeleton.includes('skeleton-bar'), 'Cluster status loading state uses skeleton-bar');
assert(csSkeletonDirect === csSkeleton, 'renderClusterStatusSkeleton equals loading viewState');
assert(!csSkeleton.toLowerCase().includes('spinner'), 'No spinner icons in cluster status skeleton');

const hrSkeleton = renderHeartbeatRail([], 'loading');
const hrSkeletonDirect = renderHeartbeatRailSkeleton();
assert(hrSkeleton.includes('skeleton-box'), 'Heartbeat rail loading state uses skeleton-box');
assert(hrSkeletonDirect === hrSkeleton, 'renderHeartbeatRailSkeleton equals loading viewState');
assert(hrSkeleton.includes('Connecting...'), 'Heartbeat rail loading indicates connecting state');

// Empty State
const csEmpty = renderClusterStatus(null, 'CONNECTED', 0, 'empty');
const csEmptyDirect = renderClusterStatusEmpty();
assert(csEmpty.includes('BOOTSTRAPPING'), 'Cluster status empty state shows BOOTSTRAPPING');
assert(csEmptyDirect === csEmpty, 'renderClusterStatusEmpty equals empty viewState');
assert(csEmpty.includes('AWAITING PEERS'), 'Cluster status empty state shows AWAITING PEERS');

const hrEmpty = renderHeartbeatRail([], 'empty');
const hrEmptyDirect = renderHeartbeatRailEmpty();
assert(hrEmpty.includes('No peer heartbeat signals detected'), 'Heartbeat rail empty state has direct copy');
assert(hrEmptyDirect === hrEmpty, 'renderHeartbeatRailEmpty equals empty viewState');
assert(hrEmpty.includes('Broadcast Probe'), 'Heartbeat rail empty state provides action button');

// Error State
const csError = renderClusterStatus(null, 'CONNECTED', 0, 'error', 'Port 8000 unreachable');
const csErrorDirect = renderClusterStatusError('Port 8000 unreachable');
assert(csError.includes('DISCONNECTED'), 'Cluster status error state shows DISCONNECTED');
assert(csErrorDirect === csError, 'renderClusterStatusError equals error viewState');
assert(csError.includes('OFFLINE'), 'Cluster status error state shows OFFLINE');

const hrError = renderHeartbeatRail([], 'error');
const hrErrorDirect = renderHeartbeatRailError();
assert(hrError.includes('STREAM OFFLINE'), 'Heartbeat rail error shows STREAM OFFLINE');
assert(hrErrorDirect === hrError, 'renderHeartbeatRailError equals error viewState');
assert(hrError.includes('Reconnect Rail'), 'Heartbeat rail error provides action button');

console.log('  ✓ PASS: Zone 1 (Cluster Status & Rail) loading, empty, and error states verified.');

// 2. Zone 2: Node List States
console.log('Testing Zone 2 (Node List) States...');

// Loading Skeleton
const nlSkeleton = renderNodeList([], 'loading');
const nlSkeletonDirect = renderNodeListSkeleton();
assert(nlSkeleton.includes('skeleton-bar'), 'Node list skeleton uses skeleton-bar in rows');
assert(nlSkeletonDirect === nlSkeleton, 'renderNodeListSkeleton equals loading viewState');
assert(nlSkeleton.includes('SCANNING...'), 'Node list skeleton header indicates scanning');

// Empty State
const nlEmpty = renderNodeList([], 'empty');
const nlEmptyDirect = renderNodeListEmpty();
assert(nlEmpty.includes('No Nodes Registered'), 'Node list empty state has direct title');
assert(nlEmptyDirect === nlEmpty, 'renderNodeListEmpty equals empty viewState');
assert(nlEmpty.includes('Scan Local Ports'), 'Node list empty state has Scan Ports button');

// Error State
const nlError = renderNodeList([], 'error');
const nlErrorDirect = renderNodeListError();
assert(nlError.includes('Topology Query Failed'), 'Node list error state has clear title');
assert(nlErrorDirect === nlError, 'renderNodeListError equals error viewState');
assert(nlError.includes('Retry Fetch'), 'Node list error state has Retry Fetch action');

console.log('  ✓ PASS: Zone 2 (Node List) loading, empty, and error states verified.');

// 3. Zone 3: File Panel States
console.log('Testing Zone 3 (File Panel) States...');

// Loading Skeleton
const fpSkeleton = renderFilePanel([], 'loading');
const fpSkeletonDirect = renderFilePanelSkeleton();
assert(fpSkeleton.includes('skeleton-bar'), 'File panel skeleton uses skeleton-bar');
assert(fpSkeletonDirect === fpSkeleton, 'renderFilePanelSkeleton equals loading viewState');
assert(fpSkeleton.includes('INDEXING...'), 'File panel skeleton header indicates indexing');

// Empty State
const fpEmpty = renderFilePanel([], 'empty');
const fpEmptyDirect = renderFilePanelEmpty();
assert(fpEmpty.includes('No Files Stored in Cluster'), 'File panel empty state has direct title');
assert(fpEmptyDirect === fpEmpty, 'renderFilePanelEmpty equals empty viewState');
assert(fpEmpty.includes('Upload First File'), 'File panel empty state has Upload action');

// Error State
const fpError = renderFilePanel([], 'error');
const fpErrorDirect = renderFilePanelError();
assert(fpError.includes('Storage Ledger Unreachable'), 'File panel error state has clear title');
assert(fpErrorDirect === fpError, 'renderFilePanelError equals error viewState');
assert(fpError.includes('Retry Ledger Query'), 'File panel error state has retry action');

console.log('  ✓ PASS: Zone 3 (File Panel) loading, empty, and error states verified.');

// 4. Anti-AI-Dashboard & Restrained Motion Validation Check
console.log('Testing Anti-AI Dashboard Cliché Check across all states...');
const allOutputs = [
  csSkeleton, csEmpty, csError,
  hrSkeleton, hrEmpty, hrError,
  nlSkeleton, nlEmpty, nlError,
  fpSkeleton, fpEmpty, fpError,
].join(' ');

assert(!allOutputs.includes('Oops!'), 'No vague "Oops!" copy');
assert(!allOutputs.includes('Something went wrong'), 'No generic "Something went wrong" copy');
assert(!allOutputs.includes('fa-spinner'), 'No FontAwesome spinner icons');
assert(!allOutputs.includes('animate-spin'), 'No spinning animation clichés');
console.log('  ✓ PASS: All visual states pass the Anti-AI Dashboard and restrained motion check.');

console.log('\n=== All State Shell Tests Passed Successfully (4/4)! ===\n');
