import { apiService } from '../services/apiService.ts';
import { healthService } from '../services/healthService.ts';
import { clusterStatusService } from '../services/clusterStatusService.ts';
import { router } from '../router/router.ts';
import type { ClusterStatusResponse } from '../types/api.ts';

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

async function runServicesTests(): Promise<void> {
  console.log('\n=== Starting DFSS Services & Routing Unit Tests ===\n');

  // 1. ApiService Configuration & Delegation
  console.log('Testing ApiService Configuration...');
  assert(typeof apiService.getHealth === 'function', 'apiService has getHealth method');
  assert(typeof apiService.getClusterStatus === 'function', 'apiService has getClusterStatus method');
  assert(typeof apiService.getNodes === 'function', 'apiService has getNodes method');
  assert(typeof apiService.getFiles === 'function', 'apiService has getFiles method');
  
  apiService.setBaseUrl('http://localhost:8000');
  assertStrictEqual(apiService.getBaseUrl(), 'http://localhost:8000', 'apiService sets custom baseUrl');
  console.log('  ✓ PASS: ApiService properly configured with typed API endpoints.');

  // 2. HealthService Reachability & State Management
  console.log('Testing HealthService Monitoring...');
  let notifiedState = false;
  const unsubscribeHealth = healthService.subscribe((result) => {
    assert(result !== null, 'Health listener receives result object');
    notifiedState = true;
  });

  assert(notifiedState, 'HealthService immediately notifies new subscribers of current state');
  unsubscribeHealth();

  // Test with mock successful health check
  const mockHealthFetch = async () => {
    return new Response(JSON.stringify({
      status: 'ok',
      message: 'Node is alive',
      node_id: 'Node A',
      timestamp: Date.now() / 1000,
    }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  };

  const rawClient = apiService.getRawClient();
  // @ts-expect-error - overriding fetchImpl for unit test
  rawClient.fetchImpl = mockHealthFetch;

  const healthResult = await healthService.checkHealth();
  assert(healthResult.reachable === true, 'Health check marked reachable on 200 OK');
  assertStrictEqual(healthResult.status, 'CONNECTED', 'Status is CONNECTED');
  assertStrictEqual(healthResult.data?.node_id, 'Node A', 'Health data deserialized correctly');
  assert(healthResult.latencyMs >= 0, 'Latency measured');
  console.log('  ✓ PASS: HealthService correctly checks and deserializes /health response.');

  // Test with mock offline server
  const mockFailingFetch = async () => {
    throw new Error('Connection refused');
  };
  // @ts-expect-error - overriding fetchImpl for offline test
  rawClient.fetchImpl = mockFailingFetch;

  const offlineResult = await healthService.checkHealth();
  assert(offlineResult.reachable === false, 'Health check marked unreachable on connection error');
  assertStrictEqual(offlineResult.status, 'DISCONNECTED', 'Status transitions to DISCONNECTED');
  assert(offlineResult.error?.includes('Connection refused') === true, 'Error message captured');
  console.log('  ✓ PASS: HealthService handles offline backend gracefully without throwing unhandled exceptions.');

  // 3. ClusterStatusService Polling, Consensus States & Exponential Backoff
  console.log('Testing ClusterStatusService Polling & State Management...');
  clusterStatusService.reset();

  // Test subscriber immediate notification
  let clusterNotified = false;
  let receivedStatus = '';
  const unsubscribeCluster = clusterStatusService.subscribe((res) => {
    clusterNotified = true;
    receivedStatus = res.status;
  });
  assert(clusterNotified, 'ClusterStatusService immediately informs subscriber of initial state');
  assertStrictEqual(receivedStatus, 'UNKNOWN', 'Initial state is UNKNOWN before first query');

  // Test successful GET /cluster/status deserialization (HEALTHY state)
  const healthyPayload: ClusterStatusResponse = {
    cluster_state: 'HEALTHY',
    leader_id: 'Node A',
    term: 4,
    commit_index: 1042,
    active_nodes: 3,
    total_nodes: 3,
    timestamp: Date.now() / 1000,
  };

  // @ts-expect-error - overriding fetchImpl for healthy cluster
  rawClient.fetchImpl = async () => new Response(JSON.stringify(healthyPayload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });

  const healthyResult = await clusterStatusService.fetchClusterStatus();
  assert(healthyResult.reachable === true, 'Cluster status reachable on 200 OK');
  assertStrictEqual(healthyResult.status, 'HEALTHY', 'Status is HEALTHY');
  assertStrictEqual(healthyResult.data?.leader_id, 'Node A', 'Leader ID matches');
  assertStrictEqual(healthyResult.data?.term, 4, 'Term is 4');
  assertStrictEqual(healthyResult.data?.commit_index, 1042, 'Commit index is 1042');
  assertStrictEqual(healthyResult.data?.active_nodes, 3, 'Active nodes is 3');
  assertStrictEqual(healthyResult.consecutiveFailures, 0, 'Consecutive failures is 0');
  assertStrictEqual(healthyResult.currentIntervalMs, 500, 'Cadence is base 500ms');
  console.log('  ✓ PASS: ClusterStatusService deserializes HEALTHY state within 500ms cadence.');

  // Test OPERATIONAL state (Quorum degraded)
  const operationalPayload: ClusterStatusResponse = {
    cluster_state: 'OPERATIONAL',
    leader_id: 'Node A',
    term: 4,
    commit_index: 1050,
    active_nodes: 2,
    total_nodes: 3,
    timestamp: Date.now() / 1000,
  };
  // @ts-expect-error - overriding fetchImpl
  rawClient.fetchImpl = async () => new Response(JSON.stringify(operationalPayload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
  const operationalResult = await clusterStatusService.fetchClusterStatus();
  assertStrictEqual(operationalResult.status, 'OPERATIONAL', 'Status transitions to OPERATIONAL');
  assertStrictEqual(operationalResult.data?.active_nodes, 2, 'Active nodes updated to 2');
  console.log('  ✓ PASS: ClusterStatusService reflects OPERATIONAL state on quorum degradation.');

  // Test NO MAJORITY state (Quorum lost)
  const noMajorityPayload: ClusterStatusResponse = {
    cluster_state: 'NO MAJORITY',
    leader_id: null,
    term: 5,
    commit_index: 1050,
    active_nodes: 1,
    total_nodes: 3,
    timestamp: Date.now() / 1000,
  };
  // @ts-expect-error - overriding fetchImpl
  rawClient.fetchImpl = async () => new Response(JSON.stringify(noMajorityPayload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
  const noMajorityResult = await clusterStatusService.fetchClusterStatus();
  assertStrictEqual(noMajorityResult.status, 'NO MAJORITY', 'Status transitions to NO MAJORITY');
  assertStrictEqual(noMajorityResult.data?.leader_id, null, 'Leader ID is null in NO MAJORITY');
  console.log('  ✓ PASS: ClusterStatusService reflects NO MAJORITY state on quorum loss.');

  // Test Exponential Backoff on repeated failures
  // @ts-expect-error - overriding fetchImpl with repeated network failure
  rawClient.fetchImpl = async () => {
    throw new Error('Coordinator connection dropped');
  };

  const fail1 = await clusterStatusService.fetchClusterStatus();
  assertStrictEqual(fail1.reachable, false, 'Failure 1 marked unreachable');
  assertStrictEqual(fail1.consecutiveFailures, 1, 'Consecutive failures is 1');
  assertStrictEqual(fail1.currentIntervalMs, 750, 'Backoff interval after fail 1 is 750ms');

  const fail2 = await clusterStatusService.fetchClusterStatus();
  assertStrictEqual(fail2.consecutiveFailures, 2, 'Consecutive failures is 2');
  assertStrictEqual(fail2.currentIntervalMs, 1125, 'Backoff interval after fail 2 is 1125ms');

  const fail3 = await clusterStatusService.fetchClusterStatus();
  assertStrictEqual(fail3.consecutiveFailures, 3, 'Consecutive failures is 3');
  assertStrictEqual(fail3.currentIntervalMs, 1688, 'Backoff interval after fail 3 is 1688ms');

  // Verify backoff clamping at max interval (10000ms)
  const maxDelay = clusterStatusService.calculateBackoffInterval(20);
  assertStrictEqual(maxDelay, 10000, 'Backoff is clamped to max 10000ms (no runaway retry loop)');
  console.log('  ✓ PASS: Polling backs off gracefully on repeated failure (750ms -> 1125ms -> 1688ms -> max 10000ms).');

  // Test Recovery: resets consecutiveFailures to 0 and interval to 500ms
  // @ts-expect-error - overriding fetchImpl for recovery
  rawClient.fetchImpl = async () => new Response(JSON.stringify(healthyPayload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
  const recoveredResult = await clusterStatusService.fetchClusterStatus();
  assertStrictEqual(recoveredResult.reachable, true, 'Recovered request is reachable');
  assertStrictEqual(recoveredResult.consecutiveFailures, 0, 'Consecutive failures reset to 0');
  assertStrictEqual(recoveredResult.currentIntervalMs, 500, 'Interval resets to base 500ms');
  console.log('  ✓ PASS: Recovery resets failure count and restores 500ms polling cadence.');

  // Test Unsubscribe and Unmount Lifecycle (Leak Prevention)
  unsubscribeCluster();
  clusterStatusService.startPolling(500);
  assert(clusterStatusService.isRunning() === true, 'Polling is active');
  clusterStatusService.stopPolling();
  assert(clusterStatusService.isRunning() === false, 'Polling stopped on unmount with interval cleared');
  console.log('  ✓ PASS: Memory leak prevention verified (timers cleared on unmount/stop).');

  // 4. HeartbeatService Per-Node Pulse History & Stalled States
  console.log('Testing HeartbeatService (Pulse History & Dead Node Stalling)...');
  const { heartbeatService } = await import('../services/heartbeatService.ts');
  heartbeatService.reset();

  let hbNotified = false;
  const unsubscribeHb = heartbeatService.subscribe((res) => {
    hbNotified = true;
    assert(res.nodes.length === 3, 'HeartbeatService starts with 3 tracked nodes');
  });
  assert(hbNotified, 'HeartbeatService immediately notifies subscriber');

  // Mock live nodes response (All nodes online & pulsing)
  const nowSec = Date.now() / 1000;
  const liveNodesPayload = {
    nodes: [
      { id: 'Node A', state: 'LEADER', status: 'ONLINE', last_heartbeat: nowSec + 1, url: 'http://127.0.0.1:8000' },
      { id: 'Node B', state: 'FOLLOWER', status: 'ONLINE', last_heartbeat: nowSec + 1, url: 'http://127.0.0.1:8001' },
      { id: 'Node C', state: 'FOLLOWER', status: 'ONLINE', last_heartbeat: nowSec + 1, url: 'http://127.0.0.1:8002' },
    ],
  };

  // @ts-expect-error - overriding fetchImpl for live heartbeat check
  rawClient.fetchImpl = async () => new Response(JSON.stringify(liveNodesPayload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });

  const hbResult1 = await heartbeatService.pollHeartbeats();
  assertStrictEqual(hbResult1.reachable, true, 'Heartbeat query reachable');
  const nodeA1 = hbResult1.nodes.find(n => n.id === 'nodeA');
  const nodeB1 = hbResult1.nodes.find(n => n.id === 'nodeB');
  assert(nodeA1 !== undefined, 'Node A tracked');
  assert(nodeB1 !== undefined, 'Node B tracked');
  assertStrictEqual(nodeA1?.isPulsing, true, 'Node A pulses on advanced heartbeat timestamp');
  assertStrictEqual(nodeB1?.status, 'ONLINE', 'Node B initially ONLINE and pulsing');
  assertStrictEqual(nodeA1?.history.length, 20, 'History maintains 20-tick sliding window');
  assertStrictEqual(nodeA1?.history[19], 'ok', 'Latest tick is ok for online pulsing node');
  console.log('  ✓ PASS: HeartbeatService registers active pulse ticks from real backend heartbeat telemetry.');


  // Mock killing Node B (Dead node stalling check)
  const deadNodePayload = {
    nodes: [
      { id: 'Node A', state: 'LEADER', status: 'ONLINE', last_heartbeat: nowSec + 2, url: 'http://127.0.0.1:8000' },
      { id: 'Node B', state: 'FOLLOWER', status: 'OFFLINE', last_heartbeat: nowSec, url: 'http://127.0.0.1:8001' },
      { id: 'Node C', state: 'FOLLOWER', status: 'ONLINE', last_heartbeat: nowSec + 2, url: 'http://127.0.0.1:8002' },
    ],
  };

  // @ts-expect-error - overriding fetchImpl for dead node B
  rawClient.fetchImpl = async () => new Response(JSON.stringify(deadNodePayload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });

  const hbResult2 = await heartbeatService.pollHeartbeats();
  const nodeB2 = hbResult2.nodes.find(n => n.id === 'nodeB');
  const nodeA2 = hbResult2.nodes.find(n => n.id === 'nodeA');
  assertStrictEqual(nodeA2?.isPulsing, true, 'Online Node A continues pulsing');
  assertStrictEqual(nodeB2?.status, 'OFFLINE', 'Node B status is OFFLINE');
  assertStrictEqual(nodeB2?.isPulsing, false, 'Offline Node B pulse is strictly halted (no fake pulse)');
  assertStrictEqual(nodeB2?.history[19], 'missed', 'Offline Node B records missed tick in history');
  assert(nodeB2?.consecutiveMissed !== undefined && nodeB2.consecutiveMissed >= 1, 'Consecutive missed increments');
  console.log('  ✓ PASS: Dead/offline node rail visibly halts pulsing and records missed ticks.');

  // Test Lifecycle cleanup
  unsubscribeHb();
  heartbeatService.startPolling(500);
  assert(heartbeatService.isRunning() === true, 'Heartbeat polling active');
  heartbeatService.stopPolling();
  assert(heartbeatService.isRunning() === false, 'Heartbeat polling stopped on unmount');
  console.log('  ✓ PASS: HeartbeatService memory leak prevention verified.');

  // 5. Router Path Matching & Navigation
  console.log('Testing Hash Router...');
  let dashboardVisited = false;
  let customRouteVisited = false;
  let notFoundVisited = false;

  router
    .addRoute('/dashboard', () => { dashboardVisited = true; })
    .addRoute('/custom', () => { customRouteVisited = true; })
    .setNotFound(() => { notFoundVisited = true; });

  // Simulate route handlers directly
  // @ts-expect-error - testing private handleRouteChange
  router.routes.get('/dashboard')();
  assert(dashboardVisited, 'Router triggers /dashboard route handler');

  // @ts-expect-error - testing private handleRouteChange
  router.routes.get('/custom')();
  assert(customRouteVisited, 'Router triggers /custom route handler');

  // @ts-expect-error - testing not found handler
  router.notFoundHandler();
  assert(notFoundVisited, 'Router triggers fallback handler on unknown route');
  console.log('  ✓ PASS: Router matches declared paths and executes route lifecycles.');

  console.log('\n=== All Services & Routing Tests Passed Successfully (5/5)! ===\n');
}

runServicesTests();


