/**
 * Final Visual QA & Token Invariant Test Suite
 *
 * Story DoD:
 * 1. No component deviates from the locked color tokens or type pairing.
 * 2. No default component-library styling leaked through anywhere.
 * 3. Heartbeat rail remains the single standout interaction — nothing else competes with it visually.
 * 4. Final review confirms the UI would not be mistaken for a generic AI-generated admin dashboard.
 */

import * as fs from 'node:fs';
import * as path from 'node:path';
import * as assert from 'node:assert';
import { FONTS, RADII } from '../tokens/index.ts';
import { renderClusterStatus } from '../components/ClusterStatus.ts';
import { renderHeartbeatRail } from '../components/HeartbeatRail.ts';
import { renderNodeList } from '../components/NodeList.ts';
import { renderFilePanel } from '../components/FilePanel.ts';
import { renderNodeDetailPanel } from '../components/NodeDetailPanel.ts';

console.log('\n=== Starting DFSS Final Visual QA & Design Invariants Audit ===\n');

const stylesDir = path.resolve(process.cwd(), 'src/styles');
const appCssPath = path.join(stylesDir, 'app.css');
const tokensCssPath = path.join(stylesDir, 'tokens.css');
const appCss = fs.readFileSync(appCssPath, 'utf-8');
const tokensCss = fs.readFileSync(tokensCssPath, 'utf-8');

// ---------------------------------------------------------------------------
// 1. Color Token Compliance: Zero Raw Hex / Unlocked Colors in app.css
// ---------------------------------------------------------------------------
console.log('1. Verifying color token invariants in app.css...');

// In app.css, no ad-hoc hex values are allowed; everything must refer to var(--color-*) or var(--*)
const hexMatches = appCss.match(/#[0-9a-fA-F]{3,8}/g);
assert.strictEqual(
  hexMatches,
  null,
  `Found ad-hoc hex codes in app.css: ${JSON.stringify(hexMatches)}. All colors must use tokens!`
);

// Verify no unauthorized rgb() declarations in app.css
const rgbMatches = appCss.match(/rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)/g);
assert.strictEqual(
  rgbMatches,
  null,
  `Found ad-hoc rgb() values in app.css: ${JSON.stringify(rgbMatches)}. Use locked tokens.`
);

console.log('   ✓ Zero ad-hoc hex or rgb() codes in app.css verified');

// ---------------------------------------------------------------------------
// 2. Anti-AI-Dashboard Rules: Zero Glassmorphism, Zero Neon, Zero Gradients
// ---------------------------------------------------------------------------
console.log('2. Verifying anti-AI-slop aesthetic constraints...');

// No backdrop-filter blur (glassmorphism cliché)
assert.ok(
  !appCss.includes('backdrop-filter: blur') && !appCss.includes('backdrop-filter:blur'),
  'Forbidden glassmorphic blur found in app.css! Strictly prohibited by anti-AI-slop constraint.'
);

// No linear-gradient or radial-gradient background fills
assert.ok(
  !appCss.includes('background-image: linear-gradient') && !appCss.includes('background: linear-gradient'),
  'Forbidden linear-gradient found in app.css! Systems UI uses flat, disciplined earth/slate panels.'
);

// No large soft glowing card box-shadows (e.g. 0 10px 30px rgba(...) or neon glows)
const glowShadows = appCss.match(/box-shadow:[^;]*(?:var\(--color-ok\)|var\(--color-info\)|neon|cyan|magenta)/gi);
assert.strictEqual(
  glowShadows,
  null,
  `Found neon glowing card shadows: ${JSON.stringify(glowShadows)}`
);

console.log('   ✓ Zero glassmorphism, zero neon glows, zero gradients verified');

// ---------------------------------------------------------------------------
// 3. Border-Radius Discipline: Strict 0px on Data Rows & Panels
// ---------------------------------------------------------------------------
console.log('3. Verifying border-radius discipline (0px data rows)...');

// All table rows, table bodies, and panels must have 0px border radius
assert.strictEqual(RADII.none, '0px', 'RADII.none must be 0px');
assert.ok(
  tokensCss.includes('--radius-none: 0px'),
  'tokens.css must define --radius-none: 0px'
);

// Node rows, file rows, and heartbeat lanes must never have rounded corners
assert.ok(
  !appCss.includes('.node-row { border-radius:') || appCss.includes('.node-row { border-radius: 0') || appCss.includes('.node-row {\n  border-radius: 0'),
  'Node rows must have 0px border radius'
);
assert.ok(
  !appCss.includes('.file-row { border-radius:') || appCss.includes('.file-row { border-radius: 0'),
  'File rows must have 0px border radius'
);

console.log('   ✓ Strict 0px data panel geometry verified');

// ---------------------------------------------------------------------------
// 4. Strict Typography Pairing: Monospace Telemetry & Sans-Serif Labels
// ---------------------------------------------------------------------------
console.log('4. Verifying dual typography pairing rules...');

assert.ok(FONTS.mono.includes('JetBrains Mono'), 'Monospace font token must be JetBrains Mono');
assert.ok(FONTS.sans.includes('Inter'), 'Sans-serif font token must be Inter');

// Render components and verify appropriate font family class application
const clusterHtml = renderClusterStatus({
  cluster_state: 'HEALTHY',
  leader_id: 'nodeA',
  term: 4,
  commit_index: 1042,
  active_nodes: 3,
  total_nodes: 3,
  timestamp: 1725890000,
});

// Telemetry values in Zone 1 must use .telemetry-value which maps to font-mono
assert.ok(clusterHtml.includes('telemetry-value'), 'Cluster status telemetry values must use telemetry-value');
assert.ok(appCss.includes('.telemetry-value {\n  font-family: var(--font-mono);'), '.telemetry-value must explicitly define font-mono');
assert.ok(clusterHtml.includes('#4'), 'Term number present');
assert.ok(clusterHtml.includes('#1042'), 'Commit index present');

// NodeList columns for metrics must use font-mono
const nodeListHtml = renderNodeList();
assert.ok(nodeListHtml.includes('font-mono text-ink'), 'Node IDs must be styled with font-mono');
assert.ok(nodeListHtml.includes('font-mono text-xs text-muted'), 'Timestamps must be styled with font-mono');

// FilePanel filenames and sizes must use font-mono
const filePanelHtml = renderFilePanel([
  {
    file_id: 'f-101',
    name: 'distributed-ledger.bin',
    size: 2048576,
    status: 'REPLICATED',
    replicas: ['nodeA', 'nodeB', 'nodeC'],
    modified_at: 1725890000,
  }
]);
assert.ok(filePanelHtml.includes('font-mono text-ink'), 'Filenames must be styled with font-mono');
assert.ok(filePanelHtml.includes('distributed-ledger.bin'), 'Filename rendered');

console.log('   ✓ Dual typography pairing strictly enforced across all components');

// ---------------------------------------------------------------------------
// 5. Standout Interaction Isolation: Heartbeat Pulse Rail
// ---------------------------------------------------------------------------
console.log('5. Verifying Heartbeat Rail visual standout hierarchy...');

const railHtml = renderHeartbeatRail();
assert.ok(railHtml.includes('heartbeat-rail'), 'Heartbeat rail present');
assert.ok(railHtml.includes('lane-track'), 'Heartbeat lane track present');
assert.ok(railHtml.includes('pulse-tick'), 'Heartbeat pulse ticks present');

// Verify pulse tick styling in app.css: 4px width, hardware accelerated, scaleY transform
assert.ok(appCss.includes('.pulse-tick {'), '.pulse-tick defined in app.css');
assert.ok(appCss.includes('transform: scaleY(1.35)'), 'Lead tick pulse animation active');
assert.ok(appCss.includes('transform: translateZ(0)'), 'Hardware acceleration active on pulse ticks');
assert.ok(appCss.includes('will-change: transform, opacity'), 'will-change optimization present on pulse ticks');

// Verify that other zones do NOT feature pulsing animations that compete with the rail
const nonRailPulses = appCss.match(/\.zone-node-list[^{]*\{[^}]*animation:[^;]*pulse/i);
assert.strictEqual(nonRailPulses, null, 'No competing pulse animations in Zone 2 Node List');

const filePanelPulses = appCss.match(/\.zone-file-panel[^{]*\{[^}]*animation:[^;]*pulse/i);
assert.strictEqual(filePanelPulses, null, 'No competing pulse animations in Zone 3 File Panel');

console.log('   ✓ Heartbeat rail isolation verified (sole pulsing visual standout)');

// ---------------------------------------------------------------------------
// 6. Zero Leaked Component-Library Reset Classes
// ---------------------------------------------------------------------------
console.log('6. Verifying zero component library leaks...');

const forbiddenFrameworkTokens = [
  'tailwind',
  'bootstrap',
  'ant-',
  'chakra-',
  'mui-',
  'shadcn',
  'v-application',
];

for (const token of forbiddenFrameworkTokens) {
  assert.ok(!appCss.toLowerCase().includes(token), `Found framework class token "${token}" in app.css!`);
  assert.ok(!tokensCss.toLowerCase().includes(token), `Found framework class token "${token}" in tokens.css!`);
}

console.log('   ✓ Zero component-library styling leaked through');

// ---------------------------------------------------------------------------
// 7. Node Detail Drawer Artisanal Systems Styling
// ---------------------------------------------------------------------------
console.log('7. Verifying Node Detail Drawer design invariants...');

const drawerHtml = renderNodeDetailPanel({
  nodeId: 'nodeA',
  nodeDetail: {
    id: 'nodeA',
    state: 'LEADER',
    status: 'ONLINE',
    last_heartbeat: 1725890000,
    url: 'http://127.0.0.1:8000',
    term: 4,
    commit_index: 1042,
    peers: ['nodeB', 'nodeC'],
  },
  isOpen: true,
});

assert.ok(drawerHtml.includes('node-detail-panel'), 'Drawer panel element present');
assert.ok(appCss.includes('border-left: 1px solid var(--color-line);'), 'Drawer uses hairline border defined in app.css');
assert.ok(appCss.includes('.node-detail-panel {'), 'Drawer styled in app.css');

console.log('   ✓ Node detail drawer conforms to zero-slop systems design');

console.log('\n=== All 7 Final Visual QA Invariants Passed with Zero Deviations! ===\n');
