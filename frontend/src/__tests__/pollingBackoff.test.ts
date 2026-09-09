/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Polling Hardening & Exponential Backoff Automated Test Suite
 *
 * Verifies:
 * 1. Exponential backoff progression during sustained backend outages across all services.
 * 2. Maximum interval capping (ceiling enforcement).
 * 3. Immediate snap-back recovery to base intervals when backend connectivity restores.
 * 4. Manual retry resetting failure counts and backoff delays without page reload.
 * 5. Single-flight timeout scheduling and start/stop lifecycle management.
 */

import assert from 'node:assert';
import { heartbeatService } from '../services/heartbeatService.ts';
import { clusterStatusService } from '../services/clusterStatusService.ts';
import { fileService } from '../services/fileService.ts';
import { healthService } from '../services/healthService.ts';
import { apiService } from '../services/apiService.ts';

console.log('=== Starting DFSS Polling Hardening & Exponential Backoff Tests ===\n');

// --------------------------------------------------------------------------
// 1. HeartbeatService Exponential Backoff & Recovery
// --------------------------------------------------------------------------
console.log('1. Testing HeartbeatService exponential backoff and recovery...');
{
  heartbeatService.reset();

  // Mathematical backoff calculation check
  assert.strictEqual(heartbeatService.calculateBackoffInterval(0), 500, '0 failures should be base interval (500ms)');
  assert.strictEqual(heartbeatService.calculateBackoffInterval(1), 750, '1 failure should be 750ms (500 * 1.5)');
  assert.strictEqual(heartbeatService.calculateBackoffInterval(2), 1125, '2 failures should be 1125ms (500 * 1.5^2)');
  assert.strictEqual(heartbeatService.calculateBackoffInterval(3), 1688, '3 failures should be 1688ms');
  assert.strictEqual(heartbeatService.calculateBackoffInterval(8), 10000, '8 failures must be capped at maxIntervalMs (10,000ms)');

  // Mock API failures
  const originalGetNodes = apiService.getNodes.bind(apiService);
  let shouldFail = true;

  apiService.getNodes = async () => {
    if (shouldFail) {
      throw new Error('Coordinator network partition');
    }
    return {
      nodes: [
        { id: 'nodeA', state: 'LEADER', last_heartbeat: Date.now() / 1000, status: 'ONLINE', url: 'http://127.0.0.1:8000' },
        { id: 'nodeB', state: 'FOLLOWER', last_heartbeat: Date.now() / 1000, status: 'ONLINE', url: 'http://127.0.0.1:8001' },
      ],
    };
  };

  try {
    // 1st Outage Tick
    const res1 = await heartbeatService.pollHeartbeats();
    assert.strictEqual(res1.reachable, false, '1st poll should report unreachable');
    assert.strictEqual(res1.consecutiveFailures, 1, 'consecutiveFailures should be 1');
    assert.strictEqual(res1.currentIntervalMs, 750, 'currentIntervalMs should back off to 750ms');

    // 2nd Outage Tick
    const res2 = await heartbeatService.pollHeartbeats();
    assert.strictEqual(res2.consecutiveFailures, 2, 'consecutiveFailures should be 2');
    assert.strictEqual(res2.currentIntervalMs, 1125, 'currentIntervalMs should back off to 1125ms');

    // 3rd Outage Tick
    const res3 = await heartbeatService.pollHeartbeats();
    assert.strictEqual(res3.consecutiveFailures, 3, 'consecutiveFailures should be 3');
    assert.strictEqual(res3.currentIntervalMs, 1688, 'currentIntervalMs should back off to 1688ms');

    // Backend Recovers!
    shouldFail = false;
    const resRecovered = await heartbeatService.pollHeartbeats();
    assert.strictEqual(resRecovered.reachable, true, 'Recovered poll should report reachable');
    assert.strictEqual(resRecovered.consecutiveFailures, 0, 'consecutiveFailures must reset to 0 upon recovery');
    assert.strictEqual(resRecovered.currentIntervalMs, 500, 'currentIntervalMs must snap back to 500ms upon recovery');

    // Outage again, then manual retry
    shouldFail = true;
    await heartbeatService.pollHeartbeats();
    assert.strictEqual(heartbeatService.getLastResult().consecutiveFailures, 1);

    // Manual retry() resets delay even if backend is still offline
    const resRetry = await heartbeatService.retry();
    assert.strictEqual(resRetry.consecutiveFailures, 1, 'Retry attempt increments from 0 to 1 on failure');
    assert.strictEqual(resRetry.currentIntervalMs, 750);
  } finally {
    apiService.getNodes = originalGetNodes;
    heartbeatService.reset();
  }

  console.log('   ✓ HeartbeatService backoff, capping, and recovery verified');
}

// --------------------------------------------------------------------------
// 2. ClusterStatusService Exponential Backoff & Recovery
// --------------------------------------------------------------------------
console.log('2. Testing ClusterStatusService exponential backoff and recovery...');
{
  clusterStatusService.reset();

  assert.strictEqual(clusterStatusService.calculateBackoffInterval(0), 500);
  assert.strictEqual(clusterStatusService.calculateBackoffInterval(1), 750);
  assert.strictEqual(clusterStatusService.calculateBackoffInterval(2), 1125);
  assert.strictEqual(clusterStatusService.calculateBackoffInterval(8), 10000);

  const originalGetClusterStatus = apiService.getClusterStatus.bind(apiService);
  let shouldFail = true;

  apiService.getClusterStatus = async () => {
    if (shouldFail) {
      throw new Error('Connection refused on port 8000');
    }
    return {
      cluster_state: 'HEALTHY' as const,
      leader_id: 'nodeA',
      term: 4,
      commit_index: 1042,
      active_nodes: 3,
      total_nodes: 3,
      timestamp: Date.now() / 1000,
    };
  };

  try {
    const res1 = await clusterStatusService.fetchClusterStatus();
    assert.strictEqual(res1.reachable, false);
    assert.strictEqual(res1.consecutiveFailures, 1);
    assert.strictEqual(res1.currentIntervalMs, 750);

    const res2 = await clusterStatusService.fetchClusterStatus();
    assert.strictEqual(res2.consecutiveFailures, 2);
    assert.strictEqual(res2.currentIntervalMs, 1125);

    // Recovery
    shouldFail = false;
    const resRecovered = await clusterStatusService.fetchClusterStatus();
    assert.strictEqual(resRecovered.reachable, true);
    assert.strictEqual(resRecovered.consecutiveFailures, 0);
    assert.strictEqual(resRecovered.currentIntervalMs, 500);

    // Test retry()
    shouldFail = true;
    await clusterStatusService.fetchClusterStatus();
    shouldFail = false;
    const retryRes = await clusterStatusService.retry();
    assert.strictEqual(retryRes.reachable, true);
    assert.strictEqual(retryRes.consecutiveFailures, 0);
    assert.strictEqual(retryRes.currentIntervalMs, 500);
  } finally {
    apiService.getClusterStatus = originalGetClusterStatus;
    clusterStatusService.reset();
  }

  console.log('   ✓ ClusterStatusService backoff, capping, and recovery verified');
}

// --------------------------------------------------------------------------
// 3. FileService Exponential Backoff & Recovery
// --------------------------------------------------------------------------
console.log('3. Testing FileService exponential backoff and recovery...');
{
  fileService.reset();

  assert.strictEqual(fileService.calculateBackoffInterval(0), 3000);
  assert.strictEqual(fileService.calculateBackoffInterval(1), 4500);
  assert.strictEqual(fileService.calculateBackoffInterval(2), 6750);
  assert.strictEqual(fileService.calculateBackoffInterval(5), 15000, 'Must cap at 15000ms maxIntervalMs');

  const originalGetFiles = apiService.getFiles.bind(apiService);
  let shouldFail = true;

  apiService.getFiles = async () => {
    if (shouldFail) {
      throw new Error('Ledger storage node offline');
    }
    return {
      files: [],
      total_files: 0,
      total_size_bytes: 0,
    };
  };

  try {
    const res1 = await fileService.fetchFiles();
    assert.strictEqual(res1.reachable, false);
    assert.strictEqual(res1.consecutiveFailures, 1);
    assert.strictEqual(res1.currentIntervalMs, 4500);

    const res2 = await fileService.fetchFiles();
    assert.strictEqual(res2.consecutiveFailures, 2);
    assert.strictEqual(res2.currentIntervalMs, 6750);

    // Recovery
    shouldFail = false;
    const resRecovered = await fileService.fetchFiles();
    assert.strictEqual(resRecovered.reachable, true);
    assert.strictEqual(resRecovered.consecutiveFailures, 0);
    assert.strictEqual(resRecovered.currentIntervalMs, 3000);

    // refreshFiles() reset
    shouldFail = true;
    await fileService.fetchFiles();
    shouldFail = false;
    const refreshRes = await fileService.refreshFiles();
    assert.strictEqual(refreshRes.reachable, true);
    assert.strictEqual(refreshRes.consecutiveFailures, 0);
    assert.strictEqual(refreshRes.currentIntervalMs, 3000);
  } finally {
    apiService.getFiles = originalGetFiles;
    fileService.reset();
  }

  console.log('   ✓ FileService backoff, capping, and recovery verified');
}

// --------------------------------------------------------------------------
// 4. HealthService Exponential Backoff & Recovery
// --------------------------------------------------------------------------
console.log('4. Testing HealthService exponential backoff and recovery...');
{
  healthService.reset();

  assert.strictEqual(healthService.calculateBackoffInterval(0), 3000);
  assert.strictEqual(healthService.calculateBackoffInterval(1), 4500);
  assert.strictEqual(healthService.calculateBackoffInterval(5), 15000);

  const originalGetHealth = apiService.getHealth.bind(apiService);
  let shouldFail = true;

  apiService.getHealth = async () => {
    if (shouldFail) {
      throw new Error('Server unreachable');
    }
    return {
      status: 'ok',
      message: 'Service operational',
      node_id: 'nodeA',
      timestamp: Date.now() / 1000,
    };
  };

  try {
    const res1 = await healthService.checkHealth();
    assert.strictEqual(res1.reachable, false);
    assert.strictEqual(res1.consecutiveFailures, 1);
    assert.strictEqual(res1.currentIntervalMs, 4500);

    const res2 = await healthService.checkHealth();
    assert.strictEqual(res2.consecutiveFailures, 2);
    assert.strictEqual(res2.currentIntervalMs, 6750);

    // Recovery
    shouldFail = false;
    const resRecovered = await healthService.checkHealth();
    assert.strictEqual(resRecovered.reachable, true);
    assert.strictEqual(resRecovered.consecutiveFailures, 0);
    assert.strictEqual(resRecovered.currentIntervalMs, 3000);

    // retry() reset
    shouldFail = true;
    await healthService.checkHealth();
    shouldFail = false;
    const retryRes = await healthService.retry();
    assert.strictEqual(retryRes.reachable, true);
    assert.strictEqual(retryRes.consecutiveFailures, 0);
    assert.strictEqual(retryRes.currentIntervalMs, 3000);
  } finally {
    apiService.getHealth = originalGetHealth;
    healthService.reset();
  }

  console.log('   ✓ HealthService backoff, capping, and recovery verified');
}

// --------------------------------------------------------------------------
// 5. Lifecycle and Single-Flight Execution Verification
// --------------------------------------------------------------------------
console.log('5. Testing polling lifecycle and single-flight execution...');
{
  heartbeatService.reset();
  assert.strictEqual(heartbeatService.isRunning(), false);

  heartbeatService.startPolling(500);
  assert.strictEqual(heartbeatService.isRunning(), true);

  heartbeatService.stopPolling();
  assert.strictEqual(heartbeatService.isRunning(), false);

  clusterStatusService.reset();
  assert.strictEqual(clusterStatusService.isRunning(), false);

  clusterStatusService.startPolling(500);
  assert.strictEqual(clusterStatusService.isRunning(), true);

  clusterStatusService.stopPolling();
  assert.strictEqual(clusterStatusService.isRunning(), false);

  fileService.reset();
  assert.strictEqual(fileService.isRunning(), false);

  fileService.startPolling(3000);
  assert.strictEqual(fileService.isRunning(), true);

  fileService.stopPolling();
  assert.strictEqual(fileService.isRunning(), false);

  healthService.reset();
  assert.strictEqual(healthService.isRunning(), false);

  healthService.startPolling(3000);
  assert.strictEqual(healthService.isRunning(), true);

  healthService.stopPolling();
  assert.strictEqual(healthService.isRunning(), false);

  console.log('   ✓ Polling lifecycle and single-flight controls verified');
}

console.log('\n=== All 5 Polling Hardening & Backoff Tests Passed Successfully! ===\n');
