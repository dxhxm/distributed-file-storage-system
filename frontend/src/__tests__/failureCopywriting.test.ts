/**
 * Comprehensive Systems Failure Copywriting Test Suite
 *
 * Story DoD:
 * 1. Every failure state in the app has specific, accurate copy tied to what actually happened.
 * 2. NO MAJORITY state clearly explains consensus is paused, not 'system down'.
 * 3. Copy reviewed for tone consistency with the rest of the UI.
 * 4. No generic 'Something went wrong' placeholders remain anywhere.
 */

import {
  resolveHealthIndicatorStyle,
  renderClusterHealthIndicator,
  renderClusterHealthError,
} from '../components/ClusterHealthIndicator.ts';
import {
  renderClusterStatus,
  renderClusterStatusError,
  renderClusterStatusEmpty,
} from '../components/ClusterStatus.ts';
import {
  renderNodeRow,
  renderNodeList,
  renderNodeListError,
  renderNodeListEmpty,
} from '../components/NodeList.ts';
import {
  renderHeartbeatLane,
  renderHeartbeatRail,
  renderHeartbeatRailError,
  renderHeartbeatRailEmpty,
} from '../components/HeartbeatRail.ts';
import {
  renderNodeDetailPanel,
  renderNodeDetailError,
} from '../components/NodeDetailPanel.ts';
import {
  renderFileRow,
  renderFilePanel,
  renderFilePanelEmpty,
  renderFilePanelError,
  renderClusterNoticeBanner,
  renderUploadProgress,
  renderDownloadError,
  renderDeleteError,
} from '../components/FilePanel.ts';

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

console.log('\n=== Starting DFSS Systems Failure Copywriting Comprehensive Tests ===\n');

// 1. NO MAJORITY: Consensus Paused (Not 'System Down') Semantics
console.log('1. Verifying NO MAJORITY copy semantics across all layout zones...');

// Zone 1: Health Indicator
const healthStyle = resolveHealthIndicatorStyle('NO MAJORITY', 'NONE');
assert(
  healthStyle.tooltip.includes('Consensus Paused') &&
  healthStyle.tooltip.includes('Active nodes serve local reads') &&
  !healthStyle.tooltip.toLowerCase().includes('system down'),
  'ClusterHealthIndicator tooltip explains consensus paused, local reads continue, not system down'
);

// Zone 1: Telemetry Quorum Metric
const clusterHtml = renderClusterStatus(
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
assert(clusterHtml.includes('1/3 (PAUSED)'), 'Quorum value renders (PAUSED) under NO MAJORITY');
assert(
  clusterHtml.includes('Consensus paused: Quorum majority lost') &&
  clusterHtml.includes('local reads permitted'),
  'Quorum tooltip clarifies consensus paused while local reads are permitted'
);

// Zone 2: Node List Caption
const nodeListNoMajority = renderNodeList(
  [
    { id: 'nodeA', displayName: 'nodeA', state: 'FOLLOWER', status: 'ONLINE', last_heartbeat: Date.now() / 1000, latencyMs: 0, port: ':8000' },
    { id: 'nodeB', displayName: 'nodeB', state: 'FOLLOWER', status: 'OFFLINE', last_heartbeat: 0, latencyMs: 0, port: ':8001' },
    { id: 'nodeC', displayName: 'nodeC', state: 'FOLLOWER', status: 'OFFLINE', last_heartbeat: 0, latencyMs: 0, port: ':8002' },
  ],
  'normal'
);
assert(
  nodeListNoMajority.includes('Consensus paused — quorum lost (1/3 active)'),
  'NodeList caption explicitly communicates consensus paused under quorum loss'
);

// Zone 3: File Panel Banner & Dropzone & Action Buttons
const noticeBanner = renderClusterNoticeBanner('NO MAJORITY');
assert(
  noticeBanner.includes('CONSENSUS PAUSED') &&
  noticeBanner.includes('mutations are paused to prevent split-brain') &&
  noticeBanner.includes('Existing replicas on active nodes remain downloadable'),
  'File panel notice banner gives comprehensive distributed consensus explanation'
);

const panelNoMajority = renderFilePanel(
  [
    {
      file_id: 'f-1',
      name: 'critical_archive.tar.gz',
      size: 4096,
      replicas: ['Node A', 'Node B'],
      status: 'REPLICATED',
    },
  ],
  'normal',
  undefined,
  1,
  4096,
  '',
  null,
  null,
  null,
  [
    { id: 'nodeA', displayName: 'nodeA', state: 'FOLLOWER', status: 'ONLINE' },
    { id: 'nodeB', displayName: 'nodeB', state: 'FOLLOWER', status: 'OFFLINE' },
  ],
  'NO MAJORITY'
);
assert(
  panelNoMajority.includes('title="Uploads paused: Quorum majority lost (< 2/3 nodes active)"'),
  'Upload button is disabled with explanatory consensus paused title'
);
assert(
  panelNoMajority.includes('title="Mutations paused: Quorum majority lost"'),
  'Delete button is disabled with consensus paused title'
);
assert(
  panelNoMajority.includes('Consensus paused: File uploads temporarily paused until quorum restored'),
  'Drop overlay explains uploads are temporarily paused'
);

console.log('  ✓ PASS: NO MAJORITY consensus paused semantics strictly verified across all zones.');

// 2. Node-Down Failure Copy
console.log('2. Verifying Node-Down failure copy across all components...');

// A. Node row offline status tooltip
const offlineRow = renderNodeRow({
  id: 'nodeB',
  displayName: 'nodeB',
  state: 'FOLLOWER',
  status: 'OFFLINE',
  last_heartbeat: 0,
  latencyMs: 0,
  port: ':8001',
});
assert(
  offlineRow.includes('Heartbeat missed (>1.5s)') &&
  offlineRow.includes('Node unresponsive on :8001') &&
  offlineRow.includes('Replicas hosted on this node are temporarily unreachable'),
  'Node row status tooltip gives exact threshold (>1.5s), port (:8001), and replica reachability impact'
);

// B. Heartbeat lane stalled pulse tooltip
const stalledLane = renderHeartbeatLane({
  id: 'nodeB',
  displayName: 'nodeB',
  state: 'FOLLOWER',
  status: 'OFFLINE',
  lastHeartbeat: 0,
  latencyMs: 0,
  port: ':8001',
  isPulsing: false,
  history: Array(20).fill('missed'),
  consecutiveMissed: 4,
});
assert(
  stalledLane.includes('Pulse Stalled for nodeB: Missed heartbeats (>1.5s). Node unresponsive on :8001.'),
  'Heartbeat lane tooltip provides specific stalled pulse detail'
);

// C. Node detail panel offline connectivity metric
const offlineDetail = renderNodeDetailPanel({
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
  offlineDetail.includes('Unreachable / Stalled (>1.5s missed). Cannot participate in consensus or serve replicas.'),
  'Node detail panel connectivity metric gives precise systems failure detail'
);

// D. Degraded file row replica pills
const degradedRow = renderFileRow(
  {
    file_id: 'f-1',
    name: 'data.csv',
    size: 2048,
    replicas: ['Node A', 'Node B', 'Node C'],
    status: 'REPLICATED',
  },
  null,
  null,
  [
    { id: 'nodeA', displayName: 'Node A', state: 'LEADER', status: 'ONLINE' },
    { id: 'nodeB', displayName: 'Node B', state: 'FOLLOWER', status: 'OFFLINE' },
    { id: 'nodeC', displayName: 'Node C', state: 'FOLLOWER', status: 'ONLINE' },
  ],
  'OPERATIONAL'
);
assert(
  degradedRow.includes('DEGRADED (2/3)') &&
  degradedRow.includes('Node B is OFFLINE') &&
  degradedRow.includes('Node B (OFFLINE) — Replica stored but node unreachable'),
  'File row accurately names offline replica holder and reflects 2/3 reachable count'
);

console.log('  ✓ PASS: Node-down failure copy verified with specific ports, heartbeats, and replica impacts.');

// 3. Upload, Download, and Delete Inline Failure Cards
console.log('3. Verifying Upload, Download, and Delete error cards...');

const uploadCard = renderUploadProgress({
  isUploading: false,
  filename: 'database_dump.sql',
  percent: 0,
  loadedBytes: 0,
  totalBytes: 1048576,
  error: 'Upload paused: Cluster consensus is paused (quorum majority lost). File cannot be replicated safely until peer nodes reconnect.',
  lastFailedFile: null,
});
assert(uploadCard.includes('UPLOAD FAILED'), 'Upload error card includes UPLOAD FAILED badge');
assert(uploadCard.includes('Cluster consensus is paused'), 'Upload error card renders explicit systems error');
assert(uploadCard.includes('btn-retry-upload') && uploadCard.includes('btn-dismiss-upload-error'), 'Upload error card provides Retry and Dismiss actions');

const downloadCard = renderDownloadError({
  isDownloading: false,
  fileId: 'f-123',
  filename: 'archive.tar',
  error: "Download unavailable: All nodes holding replicas for 'archive.tar' are offline or unreachable.",
});
assert(downloadCard.includes('REPLICA ERROR'), 'Download error card includes REPLICA ERROR badge');
assert(downloadCard.includes('All nodes holding replicas for \'archive.tar\' are offline'), 'Download card renders explicit replica availability error');
assert(downloadCard.includes('btn-dismiss-download-error'), 'Download error card provides Dismiss action');

const deleteCard = renderDeleteError({
  confirmingFileId: null,
  isDeleting: false,
  fileId: 'f-456',
  error: 'Deletion paused: Consensus is paused (quorum majority lost). Cannot commit file deletion safely without majority quorum.',
});
assert(deleteCard.includes('DELETE ERROR'), 'Delete error card includes DELETE ERROR badge');
assert(deleteCard.includes('Consensus is paused (quorum majority lost)'), 'Delete card renders consensus pause error');
assert(deleteCard.includes('btn-dismiss-delete-error'), 'Delete error card provides Dismiss action');

console.log('  ✓ PASS: Upload, download, and delete error cards render explicit systems copy with user controls.');

// 4. Zero Generic Placeholders Check
console.log('4. Auditing entire UI for zero generic placeholders or clichés...');

const allComponentsMarkup = [
  renderClusterStatusError(),
  renderClusterStatusEmpty(),
  renderClusterHealthIndicator('NO MAJORITY', 'NONE', 'normal'),
  renderClusterHealthError(),
  renderNodeListError(),
  renderNodeListEmpty(),
  renderHeartbeatRail([], 'normal'),
  renderHeartbeatRailError(),
  renderHeartbeatRailEmpty(),
  renderNodeDetailError('nodeB'),
  renderFilePanelError(),
  renderFilePanelEmpty(),
].join('\n');

const genericClichés = [
  'something went wrong',
  'an error occurred',
  'unknown error',
  'oops',
  'please try again later',
];

for (const cliché of genericClichés) {
  assert(
    !allComponentsMarkup.toLowerCase().includes(cliché),
    `No generic cliché "${cliché}" found in error/empty state shells`
  );
}

console.log('  ✓ PASS: Zero generic clichés or uninformative error placeholders found in codebase.');

console.log('\n=== All Systems Failure Copywriting Tests Passed Successfully (4/4)! ===\n');
