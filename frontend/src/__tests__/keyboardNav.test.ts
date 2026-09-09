/**
 * Keyboard Navigation & Focus Management Test Suite
 *
 * Story DoD:
 * 1. Every interactive element reachable and operable via keyboard alone.
 * 2. Visual focus outlines and focus management on overlay drawers.
 * 3. Focus trapping and restoration on drawer close.
 */

import { renderHeartbeatLane } from '../components/HeartbeatRail.ts';
import { renderNodeRow } from '../components/NodeList.ts';
import { renderFileRow } from '../components/FilePanel.ts';
import { renderNodeDetailPanel } from '../components/NodeDetailPanel.ts';
import { FocusManager, focusManager } from '../utils/focusManager.ts';

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

// Lightweight mock environment for headless Node.js test runner
class MockHTMLElement {
  public id: string = '';
  public tabIndex: number = 0;
  public offsetWidth: number = 100;
  public offsetHeight: number = 20;
  public focusCalled: boolean = false;

  public getClientRects() {
    return [{}];
  }

  public focus() {
    this.focusCalled = true;
  }
}

(globalThis as any).HTMLElement = MockHTMLElement;

if (typeof globalThis.document === 'undefined') {
  (globalThis as any).document = {
    activeElement: null,
    body: {
      contains: () => true,
    },
  };
}

console.log('\n=== Starting DFSS Keyboard Navigation & Focus Management Tests ===\n');

// 1. Verify tabindex="0" and button roles on custom interactive elements
console.log('1. Verifying keyboard reachability of custom interactive elements...');

// Heartbeat Lane
const laneHtml = renderHeartbeatLane({
  id: 'nodeA',
  displayName: 'nodeA',
  state: 'LEADER',
  status: 'ONLINE',
  lastHeartbeat: Date.now() / 1000,
  latencyMs: 0.0,
  port: ':8000',
  isPulsing: true,
  history: Array(20).fill('ok'),
  consecutiveMissed: 0,
});
assert(laneHtml.includes('tabindex="0"'), 'Heartbeat lane has tabindex="0" for keyboard focus');
assert(laneHtml.includes('role="button"'), 'Heartbeat lane has role="button"');
assert(laneHtml.includes('aria-pressed='), 'Heartbeat lane conveys pressed state');
console.log('   ✓ Heartbeat lane keyboard reachability verified');

// Node Row
const rowHtml = renderNodeRow({
  id: 'nodeB',
  displayName: 'nodeB',
  state: 'FOLLOWER',
  status: 'ONLINE',
  lastHeartbeat: Date.now() / 1000,
  latencyMs: 8.4,
  port: ':8001',
  isPulsing: false,
  history: Array(20).fill('ok'),
  consecutiveMissed: 0,
});
assert(rowHtml.includes('tabindex="0"'), 'Node row has tabindex="0" for keyboard navigation');
assert(rowHtml.includes('role="row"'), 'Node row has role="row"');
assert(rowHtml.includes('aria-selected='), 'Node row conveys selected state');
console.log('   ✓ Node row keyboard reachability verified');

// 2. Action Controls in File Panel
console.log('2. Verifying native button elements for file actions...');
const fileRowHtml = renderFileRow({
  file_id: 'test-uuid-1',
  name: 'dataset.csv',
  size: 1024,
  status: 'REPLICATED',
  replicas: ['nodeA', 'nodeB', 'nodeC'],
  modified_at: 1724500000,
});
assert(fileRowHtml.includes('class="btn-file-action btn-download-file"'), 'Download control is an accessible button');
assert(fileRowHtml.includes('class="btn-file-action btn-delete-file"'), 'Delete control is an accessible button');

// Confirmation delete buttons
const confirmingRowHtml = renderFileRow(
  {
    file_id: 'test-uuid-1',
    name: 'dataset.csv',
    size: 1024,
    status: 'REPLICATED',
    replicas: ['nodeA', 'nodeB', 'nodeC'],
    modified_at: 1724500000,
  },
  null,
  { confirmingFileId: 'test-uuid-1', isDeleting: false }
);
assert(confirmingRowHtml.includes('class="btn-file-action btn-confirm-delete"'), 'Confirm delete is an accessible button');
assert(confirmingRowHtml.includes('class="btn-file-action btn-cancel-delete"'), 'Cancel delete is an accessible button');
console.log('   ✓ File actions keyboard controls verified');

// 3. Node Detail Panel Accessibility & Dialog Semantics
console.log('3. Verifying Node Detail Drawer dialog attributes and controls...');
const drawerHtml = renderNodeDetailPanel({
  nodeId: 'nodeA',
  nodeDetail: {
    id: 'nodeA',
    state: 'LEADER',
    status: 'ONLINE',
    last_heartbeat: 1724500000,
    url: 'http://127.0.0.1:8000',
    term: 4,
    commit_index: 1042,
  },
  isOpen: true,
  state: 'normal',
});
assert(drawerHtml.includes('role="dialog"'), 'Drawer specifies role="dialog"');
assert(drawerHtml.includes('aria-modal="true"'), 'Drawer specifies aria-modal="true"');
assert(drawerHtml.includes('aria-labelledby="node-detail-title"'), 'Drawer links accessible title');
assert(drawerHtml.includes('id="btn-close-node-detail"'), 'Drawer includes accessible close button');
assert(drawerHtml.includes('id="btn-refresh-node-detail"'), 'Drawer includes accessible refresh button');
console.log('   ✓ Node detail drawer dialog semantics verified');

// 4. Focus Tracking and Restoration Logic
console.log('4. Testing focus tracking on open and restoration on close...');

const customManager = new FocusManager();

// Mock triggering button
const mockTriggerBtn = new MockHTMLElement();
mockTriggerBtn.id = 'btn-trigger-node-detail';

// Set active element to mock button
Object.defineProperty(document, 'activeElement', {
  value: mockTriggerBtn,
  writable: true,
  configurable: true,
});

// Capture active focus
customManager.captureActiveFocus();
assert(customManager.getPreviousFocus() === (mockTriggerBtn as unknown as HTMLElement), 'captureActiveFocus captures triggering element');

// Restore focus
const restored = customManager.restorePreviousFocus();
assert(restored === true, 'restorePreviousFocus returns true on successful restore');
assert(mockTriggerBtn.focusCalled, 'restorePreviousFocus invokes element.focus()');
assert(customManager.getPreviousFocus() === null, 'previousFocus is cleared after restore');
console.log('   ✓ Focus capture and restoration verified');

// 5. Drawer Focus Trap Semantics
console.log('5. Testing drawer focus trap wrap-around behavior...');

// Create mock elements
const mockBtn1 = new MockHTMLElement();
mockBtn1.id = 'btn-1';

const mockBtn2 = new MockHTMLElement();
mockBtn2.id = 'btn-2';

const mockPanel = new MockHTMLElement();
mockPanel.id = 'node-detail-panel';
(mockPanel as any).querySelectorAll = (_selector: string) => [mockBtn1, mockBtn2];
(mockPanel as any).querySelector = (selector: string) => (selector === '#btn-1' ? mockBtn1 : mockBtn2);

// Initial focus test
const focusedInit = customManager.focusInitial(mockPanel as unknown as HTMLElement, '#btn-1');
assert(focusedInit === (mockBtn1 as unknown as HTMLElement), 'focusInitial prioritizes preferred selector');
assert(mockBtn1.focusCalled, 'focusInitial activates button focus');

// Reset focus state
mockBtn1.focusCalled = false;
mockBtn2.focusCalled = false;

// Forward Tab on last element (btn2) -> wraps to first element (btn1)
const forwardState = { defaultPrevented: false };
Object.defineProperty(document, 'activeElement', {
  value: mockBtn2,
  writable: true,
  configurable: true,
});

const forwardTabEvent = {
  key: 'Tab',
  shiftKey: false,
  preventDefault: () => {
    forwardState.defaultPrevented = true;
  },
} as unknown as KeyboardEvent;

const trappedForward = customManager.trapFocus(mockPanel as unknown as HTMLElement, forwardTabEvent);
assert(trappedForward === true, 'trapFocus returns true when trapping Tab');
assert(forwardState.defaultPrevented === true, 'Forward Tab from last element prevents default browser tabout');
assert(mockBtn1.focusCalled, 'Forward Tab wraps focus to first element in drawer');

// Backward Shift+Tab on first element (btn1) -> wraps to last element (btn2)
const backwardState = { defaultPrevented: false };
mockBtn1.focusCalled = false;
mockBtn2.focusCalled = false;
Object.defineProperty(document, 'activeElement', {
  value: mockBtn1,
  writable: true,
  configurable: true,
});

const backwardTabEvent = {
  key: 'Tab',
  shiftKey: true,
  preventDefault: () => {
    backwardState.defaultPrevented = true;
  },
} as unknown as KeyboardEvent;

const trappedBackward = customManager.trapFocus(mockPanel as unknown as HTMLElement, backwardTabEvent);
assert(trappedBackward === true, 'trapFocus returns true when trapping Shift+Tab');
assert(backwardState.defaultPrevented === true, 'Backward Tab from first element prevents default browser tabout');
assert(mockBtn2.focusCalled, 'Backward Tab wraps focus to last element in drawer');

// Non-Tab keys ignored
const escEvent = {
  key: 'Escape',
  shiftKey: false,
  preventDefault: () => {},
} as unknown as KeyboardEvent;
assert(customManager.trapFocus(mockPanel as unknown as HTMLElement, escEvent) === false, 'trapFocus ignores non-Tab keys');
console.log('   ✓ Focus trapping wrap-around verified');

// 6. FocusManager singleton export
console.log('6. Verifying focusManager singleton...');
assert(typeof focusManager.captureActiveFocus === 'function', 'focusManager has captureActiveFocus');
assert(typeof focusManager.restorePreviousFocus === 'function', 'focusManager has restorePreviousFocus');
assert(typeof focusManager.trapFocus === 'function', 'focusManager has trapFocus');
console.log('   ✓ FocusManager singleton verified');

console.log('\n=== All 6 Keyboard Navigation & Focus Management Tests Passed Successfully! ===\n');
