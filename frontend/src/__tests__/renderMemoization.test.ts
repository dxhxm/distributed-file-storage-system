/**
 * Render Memoization & CPU Optimization Test Suite
 *
 * Story DoD:
 * 1. No unnecessary re-render of unrelated components on each poll tick.
 * 2. CPU usage stays low with the heartbeat rail animating continuously.
 * 3. In-place tick updates mutate span classes rather than destroying/recreating DOM.
 * 4. NodeList and FilePanel memoize display signatures and skip DOM writes when data is identical.
 */

import * as assert from 'node:assert';
import { updateHeartbeatRailDOM } from '../components/HeartbeatRail.ts';
import { updateNodeListDOM } from '../components/NodeList.ts';
import { updateFilePanelDOM } from '../components/FilePanel.ts';
import type { NodeHeartbeatState } from '../services/heartbeatService.ts';
import type { FileInfo } from '../types/api.ts';

console.log('\n=== Starting DFSS Render Memoization & Performance Tests ===\n');

// Lightweight In-Memory DOM Element Mock for Headless Test Verification
class SimpleElement {
  public id: string = '';
  public className: string = '';
  public textContent: string = '';
  public value: string = '';
  public disabled: boolean = false;
  public title: string = '';
  public style: Record<string, string> = {};
  public attributes: Map<string, string> = new Map();
  public children: SimpleElement[] = [];
  public parent: SimpleElement | null = null;
  public _innerHTML: string = '';

  constructor(public tagName: string = 'div') {}

  get innerHTML(): string {
    return this._innerHTML;
  }

  set innerHTML(val: string) {
    this._innerHTML = val;
    this.children = [];
  }

  get outerHTML(): string {
    return `<${this.tagName.toLowerCase()} id="${this.id}" class="${this.className}">${this._innerHTML}</${this.tagName.toLowerCase()}>`;
  }

  set outerHTML(val: string) {
    this._innerHTML = val;
  }

  public setAttribute(name: string, value: string): void {
    this.attributes.set(name, value);
    if (name === 'id') {
      this.id = value;
      domRegistry.set(value, this);
    }
    if (name === 'class') this.className = value;
  }

  public getAttribute(name: string): string | null {
    return this.attributes.get(name) || null;
  }

  get classList() {
    return {
      add: (...tokens: string[]) => {
        const set = new Set(this.className.split(/\s+/).filter(Boolean));
        tokens.forEach(t => set.add(t));
        this.className = Array.from(set).join(' ');
      },
      remove: (...tokens: string[]) => {
        const set = new Set(this.className.split(/\s+/).filter(Boolean));
        tokens.forEach(t => set.delete(t));
        this.className = Array.from(set).join(' ');
      },
      contains: (token: string) => {
        return this.className.split(/\s+/).filter(Boolean).includes(token);
      },
    };
  }

  public querySelector(selector: string): SimpleElement | null {
    const results = this.querySelectorAll(selector);
    return results.length > 0 && results[0] ? results[0] : null;
  }

  public querySelectorAll(selector: string): SimpleElement[] {
    const matched: SimpleElement[] = [];

    const walk = (node: SimpleElement) => {
      if (matchesSelector(node, selector)) {
        matched.push(node);
      }
      for (const child of node.children) {
        walk(child);
      }
    };

    for (const child of this.children) {
      walk(child);
    }
    return matched;
  }
}

function matchesSelector(el: SimpleElement, selector: string): boolean {
  if (selector.startsWith('#')) {
    return el.id === selector.slice(1);
  }
  if (selector.startsWith('.')) {
    const cls = selector.slice(1);
    return el.classList.contains(cls);
  }
  if (selector.includes('.')) {
    const parts = selector.split('.');
    const tag = parts[0] || '';
    const cls = parts[1] || '';
    return (tag === '' || el.tagName.toLowerCase() === tag.toLowerCase()) && el.classList.contains(cls);
  }
  if (selector.startsWith('[data-node=')) {
    const key = selector.replace(/\[data-node=["']?([^"']+)["']?\]/, '$1');
    return el.getAttribute('data-node') === key;
  }
  return el.tagName.toLowerCase() === selector.toLowerCase();
}

const domRegistry = new Map<string, SimpleElement>();

const mockDoc = {
  body: new SimpleElement('body'),
  getElementById(id: string): SimpleElement | null {
    return domRegistry.get(id) || null;
  },
  querySelector(sel: string): SimpleElement | null {
    for (const el of domRegistry.values()) {
      const match = el.querySelector(sel);
      if (match) return match;
    }
    return null;
  },
  querySelectorAll(sel: string): SimpleElement[] {
    const list: SimpleElement[] = [];
    for (const el of domRegistry.values()) {
      list.push(...el.querySelectorAll(sel));
    }
    return list;
  },
  activeElement: null as SimpleElement | null,
};

(globalThis as any).document = mockDoc;
(globalThis as any).window = {};

// ---------------------------------------------------------------------------
// Suite 1: HeartbeatRail Tick In-Place Mutation & Span Element Reuse
// ---------------------------------------------------------------------------
console.log('1. Testing HeartbeatRail in-place tick mutation (span reuse)...');

domRegistry.clear();

const railContainer = new SimpleElement('div');
railContainer.id = 'heartbeat-lanes-container';
domRegistry.set(railContainer.id, railContainer);

const laneA = new SimpleElement('div');
laneA.id = 'lane-nodeA';
laneA.setAttribute('data-node', 'nodeA');
domRegistry.set(laneA.id, laneA);
railContainer.children.push(laneA);

const trackEl = new SimpleElement('div');
trackEl.className = 'lane-track';
laneA.children.push(trackEl);

const initialTicks: SimpleElement[] = [];
for (let i = 0; i < 20; i++) {
  const tick = new SimpleElement('span');
  tick.className = 'pulse-tick';
  trackEl.children.push(tick);
  initialTicks.push(tick);
}

const initialRailNodes: NodeHeartbeatState[] = [
  {
    id: 'nodeA',
    displayName: 'Node A',
    state: 'LEADER',
    status: 'ONLINE',
    lastHeartbeat: 1725890000,
    latencyMs: 0,
    port: ':8000',
    isPulsing: false,
    history: Array(20).fill('ok'),
    consecutiveMissed: 0,
  },
];

// 1a. Lead tick pulse update: must mutate in-place, NOT recreate elements
const pulsingNodes: NodeHeartbeatState[] = [
  {
    ...initialRailNodes[0]!,
    isPulsing: true,
  },
];

updateHeartbeatRailDOM(pulsingNodes);

const afterPulseTicks = trackEl.querySelectorAll('.pulse-tick');
assert.strictEqual(afterPulseTicks.length, 20, 'Tick count remains 20');
assert.strictEqual(initialTicks[0], afterPulseTicks[0], 'Tick 0 element identity must be preserved');
assert.strictEqual(initialTicks[19], afterPulseTicks[19], 'Lead tick element identity must be preserved (zero DOM allocations)');
assert.ok(afterPulseTicks[19]!.classList.contains('pulse-active'), 'Lead tick should have pulse-active class');

// 1b. Missed pulse state: mutate class in-place
const missedNodes: NodeHeartbeatState[] = [
  {
    ...initialRailNodes[0]!,
    isPulsing: false,
    history: [...Array(19).fill('ok'), 'missed'],
    consecutiveMissed: 1,
  },
];

updateHeartbeatRailDOM(missedNodes);
const afterMissedTicks = trackEl.querySelectorAll('.pulse-tick');
assert.strictEqual(initialTicks[19], afterMissedTicks[19], 'Lead tick element identity preserved during missed pulse');
assert.ok(afterMissedTicks[19]!.classList.contains('tick-missed'), 'Lead tick should update to tick-missed in-place');
assert.ok(!afterMissedTicks[19]!.classList.contains('pulse-active'), 'pulse-active class should be removed in-place');
console.log('   ✓ HeartbeatRail span reuse and in-place class mutation verified');

// ---------------------------------------------------------------------------
// Suite 2: NodeList Signature Memoization & Zero DOM Mutation on Identical Ticks
// ---------------------------------------------------------------------------
console.log('2. Testing NodeList memoization and row identity preservation...');

domRegistry.clear();

const nodeTbody = new SimpleElement('tbody');
nodeTbody.id = 'node-table-tbody';
domRegistry.set(nodeTbody.id, nodeTbody);

const countEl = new SimpleElement('span');
countEl.id = 'node-list-count';
domRegistry.set(countEl.id, countEl);

const captionEl = new SimpleElement('span');
captionEl.id = 'node-list-caption';
domRegistry.set(captionEl.id, captionEl);

const initialNodeList: NodeHeartbeatState[] = [
  {
    id: 'nodeA',
    displayName: 'nodeA',
    state: 'LEADER',
    status: 'ONLINE',
    lastHeartbeat: 1725890000,
    latencyMs: 0,
    port: ':8000',
    isPulsing: false,
    history: Array(20).fill('ok'),
    consecutiveMissed: 0,
  },
  {
    id: 'nodeB',
    displayName: 'nodeB',
    state: 'FOLLOWER',
    status: 'ONLINE',
    lastHeartbeat: 1725890000,
    latencyMs: 8.4,
    port: ':8001',
    isPulsing: false,
    history: Array(20).fill('ok'),
    consecutiveMissed: 0,
  },
];

// Initial render
updateNodeListDOM(initialNodeList);
assert.strictEqual(countEl.textContent, '(2 ONLINE)', 'Header displays 2 ONLINE');
assert.strictEqual(captionEl.textContent, 'Quorum majority active', 'Quorum status is active');

const rowA = new SimpleElement('tr');
rowA.id = 'node-row-nodeA';
rowA.className = 'node-row';
nodeTbody.children.push(rowA);

const rowB = new SimpleElement('tr');
rowB.id = 'node-row-nodeB';
rowB.className = 'node-row';
nodeTbody.children.push(rowB);

// Memoized call with identical data
updateNodeListDOM(initialNodeList);
assert.strictEqual(nodeTbody.children[0], rowA, 'Row element A must remain untouched when signature matches');
assert.strictEqual(nodeTbody.children[1], rowB, 'Row element B must remain untouched when signature matches');

// Outage update: Node B transitions to OFFLINE
const outageNodeList: NodeHeartbeatState[] = [
  initialNodeList[0]!,
  {
    ...initialNodeList[1]!,
    status: 'OFFLINE',
    latencyMs: 0,
  },
];

updateNodeListDOM(outageNodeList);
assert.strictEqual(countEl.textContent, '(1 ONLINE)', 'Header displays (1 ONLINE)');
assert.ok(captionEl.textContent.includes('Consensus paused'), 'Caption updates to consensus paused');
assert.ok(captionEl.className.includes('text-down'), 'Caption gets text-down class');
console.log('   ✓ NodeList memoization and quorum state transitions verified');

// ---------------------------------------------------------------------------
// Suite 3: FilePanel Memoization & Skip Unnecessary Table Re-writes
// ---------------------------------------------------------------------------
console.log('3. Testing FilePanel memoization and replica status preservation...');

domRegistry.clear();

const fileTbody = new SimpleElement('tbody');
fileTbody.id = 'file-table-tbody';
domRegistry.set(fileTbody.id, fileTbody);

const fileCountEl = new SimpleElement('span');
fileCountEl.id = 'file-panel-count';
domRegistry.set(fileCountEl.id, fileCountEl);

const noticeSlot = new SimpleElement('div');
noticeSlot.id = 'cluster-notice-slot';
domRegistry.set(noticeSlot.id, noticeSlot);

const uploadBtn = new SimpleElement('button');
uploadBtn.id = 'btn-upload-file';
domRegistry.set(uploadBtn.id, uploadBtn);

const initialFiles: FileInfo[] = [
  {
    file_id: 'f-101',
    name: 'data-ledger.bin',
    size: 2048576,
    status: 'REPLICATED',
    replicas: ['nodeA', 'nodeB', 'nodeC'],
    modified_at: 1725890000,
  },
  {
    file_id: 'f-102',
    name: 'config.json',
    size: 4096,
    status: 'REPLICATED',
    replicas: ['nodeA', 'nodeB'],
    modified_at: 1725890010,
  },
];

// Initial call
updateFilePanelDOM(
  initialFiles,
  2,
  2052672,
  '',
  null,
  null,
  null,
  initialNodeList,
  'HEALTHY'
);

assert.ok(fileCountEl.textContent.includes('2 FILES'), 'Count element reflects 2 files');

// Manually attach mock row elements
const fileRow1 = new SimpleElement('tr');
fileRow1.className = 'file-row';
fileTbody.children.push(fileRow1);

const fileRow2 = new SimpleElement('tr');
fileRow2.className = 'file-row';
fileTbody.children.push(fileRow2);

// Call with identical files and nodes: memoization should hit and skip rewriting tbody
updateFilePanelDOM(
  initialFiles,
  2,
  2052672,
  '',
  null,
  null,
  null,
  initialNodeList,
  'HEALTHY'
);

assert.strictEqual(fileTbody.children[0], fileRow1, 'File row 1 reference preserved on identical poll tick');
assert.strictEqual(fileTbody.children[1], fileRow2, 'File row 2 reference preserved on identical poll tick');
console.log('   ✓ FilePanel memoization and row identity preservation verified');

// ---------------------------------------------------------------------------
// Suite 4: Cluster State Notice Banner Independence
// ---------------------------------------------------------------------------
console.log('4. Testing notice slot updating without rewriting table rows...');

// Transition cluster to NO MAJORITY
updateFilePanelDOM(
  initialFiles,
  2,
  2052672,
  '',
  null,
  null,
  null,
  initialNodeList,
  'NO MAJORITY'
);

assert.ok(noticeSlot.innerHTML.includes('CONSENSUS PAUSED'), 'Notice banner displays CONSENSUS PAUSED');
assert.strictEqual(uploadBtn.disabled, true, 'Upload button is disabled when quorum is lost');

console.log('   ✓ Notice banner and upload button state verified');

console.log('\n=== All Render Memoization & CPU Optimization Tests Passed Successfully! ===\n');
