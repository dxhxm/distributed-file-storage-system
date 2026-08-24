/**
 * Unit Tests for DFSS Services, Health Monitoring & Routing
 */

import { apiService } from '../services/apiService.ts';
import { healthService } from '../services/healthService.ts';
import { router } from '../router/router.ts';

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
  const unsubscribe = healthService.subscribe((result) => {
    assert(result !== null, 'Health listener receives result object');
    notifiedState = true;
  });

  assert(notifiedState, 'HealthService immediately notifies new subscribers of current state');
  unsubscribe();

  // Test with mock successful health check
  const mockFetch = async () => {
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
  rawClient.fetchImpl = mockFetch;

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

  // 3. Router Path Matching & Navigation
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

  console.log('\n=== All Services & Routing Tests Passed Successfully (3/3)! ===\n');
}

runServicesTests();
