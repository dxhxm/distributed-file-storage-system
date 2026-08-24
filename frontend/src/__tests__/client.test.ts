/**
 * Comprehensive Test Suite for DFSS API Contract Types & Data Fetching Layer
 */

import {
  DistributedStorageClient,
  ApiClientError,
  createClient,
  getHealth,
  getClusterStatus,
  getNodes,
  getNodeById,
  getFiles,
} from '../index.ts';
import type {
  ClusterState,
  NodeState,
  NodeStatus,
  FileStatus,
  HealthResponse,
  ClusterStatusResponse,
  NodesResponse,
  NodeDetailResponse,
  FilesResponse,
} from '../index.ts';

// Simple test runner assertion helper
function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(`Assertion Failed: ${message}`);
  }
}

function assertEquals<T>(actual: T, expected: T, message: string): void {
  const actualStr = JSON.stringify(actual);
  const expectedStr = JSON.stringify(expected);
  if (actualStr !== expectedStr) {
    throw new Error(`Assertion Failed: ${message}\nExpected: ${expectedStr}\nActual:   ${actualStr}`);
  }
}

async function runTests(): Promise<void> {
  console.log('\n=== Starting DFSS API Client & Contract Tests ===\n');
  let passed = 0;
  let total = 0;

  async function test(name: string, fn: () => Promise<void>): Promise<void> {
    total++;
    try {
      await fn();
      console.log(`  ✓ PASS: ${name}`);
      passed++;
    } catch (err: unknown) {
      console.error(`  ✗ FAIL: ${name}`);
      console.error('   ', err instanceof Error ? err.stack : err);
    }
  }

  // --- Test Mock Data ---
  const mockHealthData: HealthResponse = {
    status: 'ok',
    message: 'Node is alive',
    node_id: 'Node A',
    timestamp: 1724430000.0,
  };

  const mockClusterStatusHealthy: ClusterStatusResponse = {
    cluster_state: 'HEALTHY',
    leader_id: 'Node A',
    term: 1,
    commit_index: 0,
    active_nodes: 3,
    total_nodes: 3,
    timestamp: 1724430000.0,
  };

  const mockClusterStatusOperational: ClusterStatusResponse = {
    cluster_state: 'OPERATIONAL',
    leader_id: 'Node A',
    term: 2,
    commit_index: 5,
    active_nodes: 2,
    total_nodes: 3,
    timestamp: 1724430010.0,
  };

  const mockClusterStatusNoMajority: ClusterStatusResponse = {
    cluster_state: 'NO MAJORITY',
    leader_id: null,
    term: 3,
    commit_index: 5,
    active_nodes: 1,
    total_nodes: 3,
    timestamp: 1724430020.0,
  };

  const mockNodesData: NodesResponse = {
    nodes: [
      {
        id: 'Node A',
        state: 'LEADER',
        last_heartbeat: 1724430000.0,
        status: 'ONLINE',
        url: 'http://localhost:8000',
      },
      {
        id: 'Node B',
        state: 'FOLLOWER',
        last_heartbeat: 1724430000.0,
        status: 'ONLINE',
        url: 'http://localhost:8001',
      },
      {
        id: 'Node C',
        state: 'CANDIDATE',
        last_heartbeat: 1724430000.0,
        status: 'OFFLINE',
        url: 'http://localhost:8002',
      },
    ],
  };

  const mockNodeDetail: NodeDetailResponse = {
    id: 'Node A',
    state: 'LEADER',
    last_heartbeat: 1724430000.0,
    status: 'ONLINE',
    url: 'http://localhost:8000',
    term: 1,
    commit_index: 0,
    peers: ['Node B', 'Node C'],
  };

  const mockFilesData: FilesResponse = {
    files: [
      {
        file_id: 'file-a1b2c3d4',
        name: 'sample_report.pdf',
        size: 1048576,
        replicas: ['Node A', 'Node B', 'Node C'],
        status: 'REPLICATED',
        checksum: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        modified_at: 1724430000.0,
      },
      {
        file_id: 'file-e5f6g7h8',
        name: 'syncing_data.bin',
        size: 2048,
        replicas: ['Node A'],
        status: 'SYNCING',
      },
    ],
    total_files: 2,
    total_size_bytes: 1050624,
  };

  // 1. Test Mock Fetch Engine
  function createMockFetch(routeHandlers: Record<string, (url: string) => { status: number; body: unknown }>): typeof fetch {
    return (async (input: RequestInfo | URL) => {
      const urlStr = input.toString();
      const parsedUrl = new URL(urlStr, 'http://localhost:8000');
      const pathname = parsedUrl.pathname;

      const handler = routeHandlers[pathname];
      if (!handler) {
        return new Response(JSON.stringify({ detail: `Route ${pathname} not found` }), {
          status: 404,
          statusText: 'Not Found',
          headers: { 'Content-Type': 'application/json' },
        });
      }

      const result = handler(urlStr);
      return new Response(JSON.stringify(result.body), {
        status: result.status,
        statusText: result.status === 200 ? 'OK' : 'Error',
        headers: { 'Content-Type': 'application/json' },
      });
    }) as typeof fetch;
  }

  // --- Tests Execution ---

  await test('GET /health: deserializes and validates health schema', async () => {
    const mockFetch = createMockFetch({
      '/health': () => ({ status: 200, body: mockHealthData }),
    });

    const client = createClient({ fetchImpl: mockFetch });
    const res = await client.getHealth();

    assertEquals(res.status, 'ok', 'Status should be ok');
    assertEquals(res.node_id, 'Node A', 'Node ID should match');
    assert(typeof res.timestamp === 'number', 'Timestamp must be a number');
  });

  await test('GET /cluster/status: verifies HEALTHY, OPERATIONAL, and NO MAJORITY states', async () => {
    let currentState: ClusterStatusResponse = mockClusterStatusHealthy;

    const mockFetch = createMockFetch({
      '/cluster/status': () => ({ status: 200, body: currentState }),
    });

    const client = createClient({ fetchImpl: mockFetch });

    // Test HEALTHY
    let res = await client.getClusterStatus();
    const state1: ClusterState = res.cluster_state;
    assertEquals(state1, 'HEALTHY', 'Cluster state should be HEALTHY');
    assertEquals(res.active_nodes, 3, 'Active nodes should be 3');

    // Test OPERATIONAL
    currentState = mockClusterStatusOperational;
    res = await client.getClusterStatus();
    const state2: ClusterState = res.cluster_state;
    assertEquals(state2, 'OPERATIONAL', 'Cluster state should be OPERATIONAL');
    assertEquals(res.active_nodes, 2, 'Active nodes should be 2');

    // Test NO MAJORITY
    currentState = mockClusterStatusNoMajority;
    res = await client.getClusterStatus();
    const state3: ClusterState = res.cluster_state;
    assertEquals(state3, 'NO MAJORITY', 'Cluster state should be NO MAJORITY');
    assertEquals(res.leader_id, null, 'Leader ID should be null during NO MAJORITY');
  });

  await test('GET /nodes: validates node fields (id, state, last_heartbeat, status)', async () => {
    const mockFetch = createMockFetch({
      '/nodes': () => ({ status: 200, body: mockNodesData }),
    });

    const client = createClient({ fetchImpl: mockFetch });
    const res = await client.getNodes();

    assertEquals(res.nodes.length, 3, 'Should return 3 nodes');

    const nodeA = res.nodes[0]!;
    const stateA: NodeState = nodeA.state;
    const statusA: NodeStatus = nodeA.status;
    assertEquals(nodeA.id, 'Node A', 'Node ID');
    assertEquals(stateA, 'LEADER', 'Node A state');
    assertEquals(statusA, 'ONLINE', 'Node A status');
    assert(typeof nodeA.last_heartbeat === 'number', 'last_heartbeat number');

    const nodeC = res.nodes[2]!;
    const stateC: NodeState = nodeC.state;
    const statusC: NodeStatus = nodeC.status;
    assertEquals(nodeC.id, 'Node C', 'Node ID');
    assertEquals(stateC, 'CANDIDATE', 'Node C state');
    assertEquals(statusC, 'OFFLINE', 'Node C status');
  });

  await test('GET /nodes/{node_id}: fetches node with URL encoding', async () => {
    const mockFetch = createMockFetch({
      '/nodes/Node%20A': () => ({ status: 200, body: mockNodeDetail }),
      '/nodes/Node A': () => ({ status: 200, body: mockNodeDetail }),
    });

    const client = createClient({ fetchImpl: mockFetch });
    const res = await client.getNodeById('Node A');

    assertEquals(res.id, 'Node A', 'Node ID');
    assertEquals(res.state, 'LEADER', 'Node state');
    assertEquals(res.peers?.length, 2, 'Peers count');
  });

  await test('GET /files: validates file_id, name, size, replicas, status', async () => {
    const mockFetch = createMockFetch({
      '/files': () => ({ status: 200, body: mockFilesData }),
    });

    const client = createClient({ fetchImpl: mockFetch });
    const res = await client.getFiles();

    assertEquals(res.total_files, 2, 'Total files');
    assertEquals(res.total_size_bytes, 1050624, 'Total size');

    const file1 = res.files[0]!;
    const fileStatus1: FileStatus = file1.status;
    assertEquals(file1.file_id, 'file-a1b2c3d4', 'file_id');
    assertEquals(file1.name, 'sample_report.pdf', 'file name');
    assertEquals(file1.size, 1048576, 'file size');
    assertEquals(file1.replicas, ['Node A', 'Node B', 'Node C'], 'replicas list');
    assertEquals(fileStatus1, 'REPLICATED', 'File status');

    const file2 = res.files[1]!;
    const fileStatus2: FileStatus = file2.status;
    assertEquals(file2.file_id, 'file-e5f6g7h8', 'file_id');
    assertEquals(fileStatus2, 'SYNCING', 'File status');
  });

  await test('Error Handling: ApiClientError captures status codes and error bodies', async () => {
    const mockFetch = createMockFetch({
      '/nodes/UnknownNode': () => ({
        status: 404,
        body: { detail: "Node 'UnknownNode' not found" },
      }),
    });

    const client = createClient({ fetchImpl: mockFetch });

    try {
      await client.getNodeById('UnknownNode');
      assert(false, 'Should have thrown ApiClientError');
    } catch (err: unknown) {
      assert(err instanceof ApiClientError, 'Must be instance of ApiClientError');
      const apiErr = err as ApiClientError;
      assertEquals(apiErr.status, 404, 'Status code should be 404');
      assertEquals(apiErr.errorData?.detail, "Node 'UnknownNode' not found", 'Detail message');
    }
  });

  await test('DistributedStorageClient class & Standalone functions', async () => {
    const directClient = new DistributedStorageClient();
    assert(directClient instanceof DistributedStorageClient, 'Must be instance of DistributedStorageClient');
    assert(typeof directClient.getHealth === 'function', 'getHealth method');

    // Verify type signatures of standalone functions compile cleanly
    assert(typeof getHealth === 'function', 'getHealth is function');
    assert(typeof getClusterStatus === 'function', 'getClusterStatus is function');
    assert(typeof getNodes === 'function', 'getNodes is function');
    assert(typeof getNodeById === 'function', 'getNodeById is function');
    assert(typeof getFiles === 'function', 'getFiles is function');
  });

  console.log(`\n=== Tests Finished: ${passed}/${total} Passed ===\n`);
  if (passed !== total) {
    process.exit(1);
  }
}

runTests().catch((err) => {
  console.error('Fatal error during test run:', err);
  process.exit(1);
});
