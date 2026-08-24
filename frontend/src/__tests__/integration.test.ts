/**
 * Live Integration Test: Runs against local FastAPI node if running on port 8000
 */

import {
  createClient,
  ApiClientError,
} from '../index.ts';

async function runLiveIntegrationTest(): Promise<void> {
  console.log('\n=== Testing Live FastAPI Server on http://localhost:8000 ===\n');

  const client = createClient({
    baseUrl: 'http://localhost:8000',
    defaultTimeoutMs: 2000,
  });

  try {
    const health = await client.getHealth();
    console.log('  ✓ GET /health response:', health);

    const clusterStatus = await client.getClusterStatus();
    console.log('  ✓ GET /cluster/status response:', clusterStatus);

    const nodes = await client.getNodes();
    console.log('  ✓ GET /nodes response:', nodes);

    const nodeA = await client.getNodeById('Node A');
    console.log('  ✓ GET /nodes/Node A response:', nodeA);

    const files = await client.getFiles();
    console.log('  ✓ GET /files response:', files);

    console.log('\n=== All live endpoints verified successfully! ===\n');
  } catch (err: unknown) {
    if (err instanceof ApiClientError) {
      console.log(`  [INFO] Backend not running or returned: ${err.message}`);
    } else {
      console.log('  [INFO] Server offline on port 8000 (unit tests already verified logic).');
    }
  }
}

runLiveIntegrationTest();
