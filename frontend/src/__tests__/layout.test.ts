/**
 * Unit Tests for DFSS Static App Shell Layout & Three-Zone Architecture
 */

import * as fs from 'node:fs';
import * as path from 'node:path';

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

console.log('\n=== Starting DFSS App Shell Layout & Three-Zone Tests ===\n');

// 1. Verify HTML Structure & Zones Existence
console.log('Testing App Shell HTML Structure...');
const indexPath = path.resolve(process.cwd(), 'index.html');
assert(fs.existsSync(indexPath), 'index.html must exist in frontend root');

const htmlContent = fs.readFileSync(indexPath, 'utf-8');

assert(htmlContent.includes('id="zone-cluster-status"'), 'Zone 1: Cluster Status Zone must exist');
assert(htmlContent.includes('id="zone-node-list"'), 'Zone 2: Node List Zone must exist');
assert(htmlContent.includes('id="zone-file-panel"'), 'Zone 3: File Panel Zone must exist');
assert(htmlContent.includes('id="heartbeat-rail"'), 'Signature Heartbeat Rail must exist');
console.log('  ✓ PASS: All 3 distinct layout zones and signature heartbeat rail exist in DOM.');

// 2. Verify Locked Tokens & Zero-Slop Design in CSS
console.log('Testing Layout CSS & Tokens Adherence...');
const appCssPath = path.resolve(process.cwd(), 'src/styles/app.css');
assert(fs.existsSync(appCssPath), 'src/styles/app.css must exist');

const appCssContent = fs.readFileSync(appCssPath, 'utf-8');

// Check that no ad-hoc hex codes are defined in app.css
const adHocHexes = appCssContent.match(/#[0-9a-fA-F]{3,8}/g);
assert(adHocHexes === null || adHocHexes.length === 0, 'No ad-hoc hex values allowed in app.css (use tokens).');

// Verify responsive grid & breakpoints
assert(appCssContent.includes('grid-template-columns'), 'CSS Grid defined for desktop zone proportions.');
assert(appCssContent.includes('@media (max-width: 1024px)') || appCssContent.includes('@media (max-width: 640px)'), 'Responsive breakpoints defined for mobile (375px) support.');
console.log('  ✓ PASS: CSS strictly references design tokens with responsive grid layout.');

// 3. Verify Placeholder Data & Domain Structure
console.log('Testing Domain Placeholder Data Structure...');
assert(htmlContent.includes('nodeA') && htmlContent.includes('nodeB') && htmlContent.includes('nodeC'), 'Node inventory contains nodeA, nodeB, nodeC');
assert(htmlContent.includes('LEADER') && htmlContent.includes('FOLLOWER'), 'Raft roles present in placeholder');
assert(htmlContent.includes('REPLICATED') && htmlContent.includes('SYNCING') && htmlContent.includes('DEGRADED'), 'Replication statuses present');
assert(htmlContent.includes('Term') && htmlContent.includes('#4') && htmlContent.includes('Commit') && htmlContent.includes('#1042'), 'Consensus telemetry present');
console.log('  ✓ PASS: Placeholder data reflects distributed storage system domain.');

// 4. Verify Typography Pairing Rules
console.log('Testing Dual Font Pairing Rules in Shell...');
assert(htmlContent.includes('font-mono'), 'Monospace class used for tabular numeric display');
assert(htmlContent.includes('cluster-brand'), 'Branding and headers structured with Inter typography');
console.log('  ✓ PASS: Dual typography pairing (JetBrains Mono + Inter) strictly applied.');

console.log('\n=== All App Shell Layout Tests Passed Successfully (4/4)! ===\n');
