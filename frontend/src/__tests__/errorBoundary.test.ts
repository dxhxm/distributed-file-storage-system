/**
 * Error Boundary & Crash Fallback Test Suite
 *
 * Story DoD:
 * 1. An unhandled component error shows the boundary fallback instead of a blank white screen.
 * 2. Retry button re-attempts the failed fetch/render without a full page reload.
 * 3. Errors logged to console with enough structured context to debug.
 */

import { ErrorBoundary, errorBoundary } from '../components/ErrorBoundary.ts';

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

console.log('\n=== Starting DFSS Error Boundary & Crash Fallback Tests ===\n');

// 1. Initial Clean State
console.log('1. Testing initial error boundary clean state...');
const testBoundary = new ErrorBoundary();
assert(testBoundary.hasError() === false, 'Boundary initializes with hasError() === false');
assert(testBoundary.getError() === null, 'Boundary initializes with getError() === null');
console.log('   ✓ Clean state verified');

// 2. Capture Error & Structured Logging
console.log('2. Testing captureError and structured diagnostic console output...');
let loggedMessage = '';
let loggedContext: unknown = null;
const originalConsoleError = console.error;
console.error = (msg: unknown, ctx?: unknown) => {
  loggedMessage = String(msg);
  loggedContext = ctx;
};

const sampleError = new Error('Database schema synchronization failed');
const sampleTelemetry = { term: 5, leader: 'node-2', activeConnections: 12 };
const record = testBoundary.captureError(sampleError, 'FileLedgerService', sampleTelemetry);

// Restore console.error
console.error = originalConsoleError;

assert(testBoundary.hasError() === true, 'hasError() is true after captureError');
assert(record.error === sampleError, 'Record holds exact error instance');
assert(record.subsystem === 'FileLedgerService', 'Record holds correct subsystem identifier');
assert(record.telemetrySnapshot === sampleTelemetry, 'Record holds telemetry snapshot');
assert(typeof record.timestamp === 'number', 'Timestamp is a numeric epoch');
assert(typeof record.isoTime === 'string', 'isoTime is an ISO string');

assert(
  loggedMessage.includes('[DFSS ErrorBoundary]') && loggedMessage.includes('[FileLedgerService]'),
  'Structured console log includes prefix and subsystem name'
);
assert(
  (loggedContext as Record<string, unknown>)?.errorMessage === 'Database schema synchronization failed',
  'Structured console log payload contains error message and telemetry'
);
console.log('   ✓ Structured error capture and logging verified');

// 3. String & Non-Error Coercion
console.log('3. Testing non-Error exception wrapping...');
testBoundary.reset();
testBoundary.captureError('Raw string failure', 'ConsensusEngine');
assert(testBoundary.getError()?.error instanceof Error, 'String input coerced to Error instance');
assert(testBoundary.getError()?.error.message === 'Raw string failure', 'Message preserved in Error instance');
console.log('   ✓ Non-Error normalization verified');

// 4. Fallback HTML Rendering & Accessibility
console.log('4. Testing systems-grade fallback card markup and accessibility tags...');
const fallbackHtml = testBoundary.renderFallback();
assert(fallbackHtml.includes('id="error-boundary-root"'), 'Contains root container ID');
assert(fallbackHtml.includes('role="alert"'), 'Contains role="alert" for screen readers');
assert(fallbackHtml.includes('aria-live="assertive"'), 'Contains aria-live="assertive"');
assert(fallbackHtml.includes('APPLICATION FAULT INTERCEPTED'), 'Contains systems header badge');
assert(fallbackHtml.includes('SUBSYSTEM: ConsensusEngine'), 'Surfaces the failing subsystem tag');
assert(fallbackHtml.includes('Application Execution Paused'), 'Card title explains execution paused');
assert(fallbackHtml.includes('Distributed storage cluster nodes on ports 8000–8002 continue running normally'), 'Reassures user that storage nodes remain active');
assert(fallbackHtml.includes('id="btn-boundary-retry"'), 'Contains Re-attempt Render button ID');
assert(fallbackHtml.includes('Re-attempt Render'), 'Contains Re-attempt Render label');
assert(fallbackHtml.includes('id="btn-boundary-reset"'), 'Contains Reset Telemetry State button ID');
assert(fallbackHtml.includes('Reset Telemetry State'), 'Contains Reset Telemetry State label');
assert(fallbackHtml.includes('class="error-boundary-trace'), 'Contains diagnostic stack trace block');
console.log('   ✓ Systems-grade fallback rendering verified');

// 5. Safe Wrap Pipeline
console.log('5. Testing wrap() error containment for component render passes...');
testBoundary.reset();

// Test throwing case
const failingRender = () => {
  throw new Error('Null pointer in HeartbeatRail render loop');
};
const wrapOutput = testBoundary.wrap(failingRender, 'HeartbeatRail', { lanes: 3 });
assert(wrapOutput === undefined, 'wrap() returns undefined when render throws');
assert(testBoundary.hasError() === true, 'wrap() sets hasError to true on failure');
assert(testBoundary.getError()?.subsystem === 'HeartbeatRail', 'wrap() records subsystem on throw');
assert(
  testBoundary.getError()?.error.message === 'Null pointer in HeartbeatRail render loop',
  'wrap() records the caught exception'
);

// Test succeeding case
testBoundary.reset();
const succeedingRender = () => '<section id="cluster-root">OK</section>';
const successfulOutput = testBoundary.wrap(succeedingRender, 'ClusterStatus');
assert(successfulOutput === '<section id="cluster-root">OK</section>', 'wrap() returns function result on success');
assert(testBoundary.hasError() === false, 'wrap() leaves boundary clean on success');
console.log('   ✓ Safe wrap pipeline containment verified');

// 6. Retry Dispatch Without Page Reload
console.log('6. Testing retry dispatch mechanism without page reload...');
testBoundary.captureError(new Error('Transient network glitch'), 'Transport');
assert(testBoundary.hasError() === true, 'Boundary is in error state prior to retry');

const retryState = { count: 0 };
const unregisterRetry = testBoundary.onRetry(() => {
  retryState.count++;
});

testBoundary.triggerRetry();

assert(retryState.count === 1, 'triggerRetry() calls registered retry callback');
assert(testBoundary.hasError() === false, 'triggerRetry() automatically resets boundary error state');
assert(testBoundary.getError() === null, 'getError() is cleared after retry');

// Unregister retry test
unregisterRetry();
testBoundary.triggerRetry();
assert(retryState.count === 1, 'Unregistered retry callback is not called again');
console.log('   ✓ Retry dispatch mechanism verified');

// 7. Event Subscriptions & State Notifications
console.log('7. Testing state change listeners...');
let notificationCount = 0;
let lastCapturedRecord: unknown = null;
const unsubscribe = testBoundary.subscribe((record) => {
  notificationCount++;
  lastCapturedRecord = record;
});

testBoundary.captureError(new Error('Subscribed error'), 'SubsystemTest');
assert(notificationCount === 1, 'Listener notified on captureError');
assert(lastCapturedRecord !== null, 'Listener receives error record');

testBoundary.reset();
assert(notificationCount === 2, 'Listener notified on reset');
assert(lastCapturedRecord === null, 'Listener receives null on reset');

unsubscribe();
testBoundary.captureError(new Error('After unsubscribe'), 'SilentSubsystem');
assert(notificationCount === 2, 'Listener is not notified after unsubscribe');
console.log('   ✓ State listener subscriptions verified');

// 8. Singleton Export Verification
console.log('8. Testing exported errorBoundary singleton...');
assert(typeof errorBoundary.wrap === 'function', 'errorBoundary singleton has wrap method');
assert(typeof errorBoundary.captureError === 'function', 'errorBoundary singleton has captureError method');
assert(typeof errorBoundary.renderFallback === 'function', 'errorBoundary singleton has renderFallback method');
assert(typeof errorBoundary.triggerRetry === 'function', 'errorBoundary singleton has triggerRetry method');
console.log('   ✓ Singleton export verified');

console.log('\n=== All 8 Error Boundary & Crash Fallback Tests Passed Successfully! ===\n');
