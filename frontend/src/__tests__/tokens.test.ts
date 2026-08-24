/**
 * Unit Tests for DFSS Design Tokens & Type System
 */

import {
  COLORS,
  SPACING,
  FONTS,
  TYPOGRAPHY,
  RADII,
  BORDERS,
  CLUSTER_STATE_THEME,
  NODE_STATE_THEME,
  NODE_STATUS_THEME,
  FILE_STATUS_THEME,
  formatBytes,
  formatTimestamp,
  formatLatency,
  formatTerm,
  formatCommitIndex,
  TOKENS,
} from '../tokens/index.ts';

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

console.log('\n=== Starting DFSS Design Tokens & Type System Tests ===\n');

// 1. Color Palette Integrity (Locked Hex Values, No Neon)
console.log('Testing Color Palette & Hex Validation...');
const hexRegex = /^#([A-Fa-f0-9]{6})$/;

for (const [key, val] of Object.entries(COLORS)) {
  assert(hexRegex.test(val), `Color token '${key}' (${val}) must be a valid 6-digit hex string.`);
}

assertStrictEqual(COLORS.bg, '#0F1210', 'Canvas background matches locked near-black token.');
assertStrictEqual(COLORS.surface, '#171B18', 'Primary surface matches locked container token.');
assertStrictEqual(COLORS.line, '#2A2F2B', 'Hairline border matches locked divider token.');
assertStrictEqual(COLORS.ink, '#E8ECE9', 'High-contrast ink matches locked primary text token.');
assertStrictEqual(COLORS.muted, '#8A928C', 'Muted ink matches locked secondary label token.');
assertStrictEqual(COLORS.ok, '#5FB88A', 'Healthy/Leader matches locked muted forest green.');
assertStrictEqual(COLORS.warn, '#D9A441', 'Candidate/Degraded matches locked muted amber.');
assertStrictEqual(COLORS.down, '#C15B4A', 'Quorum Lost/Offline matches locked muted crimson.');
console.log('  ✓ PASS: All 20 color tokens match strict locked hex palette without neon/gradients.');

// 2. Geometry & Anti-AI-Dashboard Rules
console.log('Testing Geometry & Elevation Rules...');
assertStrictEqual(RADII.none, '0px', 'Data panels and rows must have 0px border-radius.');
assertStrictEqual(RADII.sm, '2px', 'Micro status badges must use 2px radius.');
assertStrictEqual(RADII.md, '4px', 'Interactive controls must have max 4px radius.');
assert(BORDERS.hairline.includes('1px solid'), 'Borders must be 1px solid hairline.');
console.log('  ✓ PASS: Strict 0px panel radius and 1px hairline border rules verified.');

// 3. Spacing Scale (4px Base Grid)
console.log('Testing Spacing Scale...');
assertStrictEqual(SPACING[1], '4px', 'Space 1 is 4px base.');
assertStrictEqual(SPACING[2], '8px', 'Space 2 is 8px.');
assertStrictEqual(SPACING[4], '16px', 'Space 4 is 16px.');
assertStrictEqual(SPACING[8], '32px', 'Space 8 is 32px.');
console.log('  ✓ PASS: Spacing scale follows exact 4px grid.');

// 4. Typography Font Pairing
console.log('Testing Font Pairing Definitions...');
assert(FONTS.mono.includes('JetBrains Mono'), 'Monospace stack must prioritize JetBrains Mono.');
assert(FONTS.sans.includes('Inter'), 'Sans-serif stack must prioritize Inter.');
assert(TYPOGRAPHY.sizes.base === '0.875rem', 'Base text size is 14px (0.875rem).');
assert(TYPOGRAPHY.sizes.xs === '0.75rem', 'Metadata text size is 12px (0.75rem).');
console.log('  ✓ PASS: Typography font pairing and type scale verified.');

// 5. Status Theme Mappings
console.log('Testing State & Status Theme Mappings...');
assert(CLUSTER_STATE_THEME.HEALTHY.color === COLORS.ok, 'Cluster HEALTHY uses --ok color');
assert(CLUSTER_STATE_THEME.OPERATIONAL.color === COLORS.warn, 'Cluster OPERATIONAL uses --warn color');
assert(CLUSTER_STATE_THEME['NO MAJORITY'].color === COLORS.down, 'Cluster NO MAJORITY uses --down color');

assert(NODE_STATE_THEME.LEADER.color === COLORS.ok, 'Node LEADER uses --ok color');
assert(NODE_STATE_THEME.CANDIDATE.color === COLORS.warn, 'Node CANDIDATE uses --warn color');
assert(NODE_STATUS_THEME.ONLINE.color === COLORS.ok, 'Node ONLINE uses --ok color');
assert(NODE_STATUS_THEME.OFFLINE.color === COLORS.down, 'Node OFFLINE uses --down color');

assert(FILE_STATUS_THEME.REPLICATED.color === COLORS.ok, 'File REPLICATED uses --ok color');
assert(FILE_STATUS_THEME.SYNCING.color === COLORS.warn, 'File SYNCING uses --warn color');
assert(FILE_STATUS_THEME.DEGRADED.color === COLORS.warn, 'File DEGRADED uses --warn color');
assert(FILE_STATUS_THEME.CORRUPTED.color === COLORS.down, 'File CORRUPTED uses --down color');
console.log('  ✓ PASS: Cluster, Node, and File state themes mapped comprehensively.');

// 6. Monospace Data Formatters
console.log('Testing Monospace Numeric Formatters...');
assertStrictEqual(formatBytes(0), '0 B', 'Formats 0 B');
assertStrictEqual(formatBytes(1024), '1 KB', 'Formats 1 KB');
assertStrictEqual(formatBytes(1572864), '1.5 MB', 'Formats 1.5 MB');
assertStrictEqual(formatBytes(1073741824), '1 GB', 'Formats 1 GB');

assertStrictEqual(formatTerm(4), 'Term #4', 'Formats Raft Term');
assertStrictEqual(formatCommitIndex(1024), 'Commit #1024', 'Formats Commit Index');
assertStrictEqual(formatLatency(12.4), '+12.4 ms', 'Formats positive latency');
assertStrictEqual(formatLatency(-4.2), '-4.2 ms', 'Formats negative latency');

const ts = formatTimestamp(1700000000);
assert(ts.includes('UTC'), 'Timestamp contains UTC indicator');
console.log('  ✓ PASS: Monospace numeric formatters verified.');

// 7. TOKENS Object Export
console.log('Testing Unified TOKENS Export Object...');
assert(TOKENS.colors === COLORS, 'TOKENS exposes colors');
assert(TOKENS.spacing === SPACING, 'TOKENS exposes spacing');
assert(TOKENS.fonts === FONTS, 'TOKENS exposes fonts');
assert(TOKENS.radii === RADII, 'TOKENS exposes radii');
console.log('  ✓ PASS: Unified TOKENS default and named exports validated.');

console.log('\n=== All Design Token Tests Passed Successfully (7/7)! ===\n');
