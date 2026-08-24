/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Strongly Typed Design Tokens & Visual Theme System
 *
 * Locked Design Language:
 * - Color Palette: Strict earth/slate tones (zero neon, zero gradients)
 * - Typography: Dual-font pairing (JetBrains Mono for data/numbers, Inter for body/labels)
 * - Elevation & Radius: Hairline 1px borders, 0px data panels, 4px interactive controls
 */

import type {
  ClusterState,
  NodeState,
  NodeStatus,
  FileStatus,
} from '../types/api.ts';

/**
 * Locked Color Palette Hex Values
 */
export const COLORS = {
  // Canvas & Surfaces
  bg: '#0F1210',
  surface: '#171B18',
  surfaceSubtle: '#131714',
  surfaceHover: '#1E231F',
  surfaceActive: '#242A25',
  surfaceMuted: '#1A1F1B',

  // Hairline Dividers & Borders
  line: '#2A2F2B',
  lineSubtle: '#1F2420',
  lineBright: '#3D443E',

  // Typography Inks
  ink: '#E8ECE9',
  inkSecondary: '#C2C9C3',
  muted: '#8A928C',
  inkDisabled: '#4E5550',

  // Semantic Status Tokens
  ok: '#5FB88A',
  okBg: '#14291E',
  okBorder: '#23543A',

  warn: '#D9A441',
  warnBg: '#2B2211',
  warnBorder: '#57431B',

  down: '#C15B4A',
  downBg: '#291614',
  downBorder: '#522520',

  info: '#6499B8',
  infoBg: '#13242E',
  infoBorder: '#20455B',
} as const;

export type ColorKey = keyof typeof COLORS;
export type ColorValue = typeof COLORS[ColorKey];

/**
 * 4px-Grid Spacing Scale
 */
export const SPACING = {
  0: '0px',
  1: '4px',     // 0.25rem
  1.5: '6px',   // 0.375rem
  2: '8px',     // 0.5rem
  2.5: '10px',  // 0.625rem
  3: '12px',    // 0.75rem
  4: '16px',    // 1rem
  5: '20px',    // 1.25rem
  6: '24px',    // 1.5rem
  8: '32px',    // 2rem
  10: '40px',   // 2.5rem
  12: '48px',   // 3rem
  16: '64px',   // 4rem
} as const;

export type SpacingKey = keyof typeof SPACING;

/**
 * Font Families: Strict Pairing Architecture
 */
export const FONTS = {
  /**
   * Descriptive & interface text (labels, headers, table headers, copy, modals)
   */
  sans: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif",

  /**
   * All numeric & system telemetry (node IDs, byte sizes, timestamps, terms, commit indices, hashes)
   */
  mono: "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
} as const;

/**
 * Strict Typography Scale
 */
export const TYPOGRAPHY = {
  sizes: {
    '2xs': '0.6875rem', // 11px
    xs: '0.75rem',       // 12px
    sm: '0.8125rem',     // 13px
    base: '0.875rem',    // 14px
    md: '1rem',          // 16px
    lg: '1.125rem',      // 18px
    xl: '1.25rem',       // 20px
    '2xl': '1.5rem',     // 24px
  },
  weights: {
    regular: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
  lineHeights: {
    none: 1,
    tight: 1.25,
    snug: 1.375,
    normal: 1.5,
    relaxed: 1.625,
  },
  letterSpacing: {
    tight: '-0.015em',
    normal: '0em',
    wide: '0.025em',
    wider: '0.05em',
    widest: '0.1em',
  },
} as const;

/**
 * Geometry & Radii
 * (Anti 'AI Dashboard' Rule: 0px data rows/panels, 4px interactive controls only)
 */
export const RADII = {
  none: '0px',
  sm: '2px',
  md: '4px',
} as const;

/**
 * Borders & Hairline Dividers
 */
export const BORDERS = {
  hairline: `1px solid ${COLORS.line}`,
  subtle: `1px solid ${COLORS.lineSubtle}`,
  bright: `1px solid ${COLORS.lineBright}`,
} as const;

/**
 * Status Theme Configuration
 * Directly maps Raft state, node health, and file statuses to locked visual tokens.
 */
export interface StatusVisual {
  color: ColorValue;
  bg: ColorValue;
  border: ColorValue;
  label: string;
  badgeClass: string;
  dotClass: string;
}

export const CLUSTER_STATE_THEME: Record<ClusterState, StatusVisual> = {
  HEALTHY: {
    color: COLORS.ok,
    bg: COLORS.okBg,
    border: COLORS.okBorder,
    label: 'HEALTHY',
    badgeClass: 'badge-ok',
    dotClass: 'dot-ok',
  },
  OPERATIONAL: {
    color: COLORS.warn,
    bg: COLORS.warnBg,
    border: COLORS.warnBorder,
    label: 'OPERATIONAL',
    badgeClass: 'badge-warn',
    dotClass: 'dot-warn',
  },
  'NO MAJORITY': {
    color: COLORS.down,
    bg: COLORS.downBg,
    border: COLORS.downBorder,
    label: 'NO MAJORITY',
    badgeClass: 'badge-down',
    dotClass: 'dot-down',
  },
};

export const NODE_STATE_THEME: Record<NodeState, StatusVisual> = {
  LEADER: {
    color: COLORS.ok,
    bg: COLORS.okBg,
    border: COLORS.okBorder,
    label: 'LEADER',
    badgeClass: 'badge-ok',
    dotClass: 'dot-ok',
  },
  CANDIDATE: {
    color: COLORS.warn,
    bg: COLORS.warnBg,
    border: COLORS.warnBorder,
    label: 'CANDIDATE',
    badgeClass: 'badge-warn',
    dotClass: 'dot-warn',
  },
  FOLLOWER: {
    color: COLORS.inkSecondary,
    bg: COLORS.surfaceSubtle,
    border: COLORS.line,
    label: 'FOLLOWER',
    badgeClass: 'badge-info',
    dotClass: 'dot-muted',
  },
};

export const NODE_STATUS_THEME: Record<NodeStatus, StatusVisual> = {
  ONLINE: {
    color: COLORS.ok,
    bg: COLORS.okBg,
    border: COLORS.okBorder,
    label: 'ONLINE',
    badgeClass: 'badge-ok',
    dotClass: 'dot-ok',
  },
  OFFLINE: {
    color: COLORS.down,
    bg: COLORS.downBg,
    border: COLORS.downBorder,
    label: 'OFFLINE',
    badgeClass: 'badge-down',
    dotClass: 'dot-down',
  },
};

export const FILE_STATUS_THEME: Record<FileStatus, StatusVisual> = {
  REPLICATED: {
    color: COLORS.ok,
    bg: COLORS.okBg,
    border: COLORS.okBorder,
    label: 'REPLICATED',
    badgeClass: 'badge-ok',
    dotClass: 'dot-ok',
  },
  SYNCING: {
    color: COLORS.warn,
    bg: COLORS.warnBg,
    border: COLORS.warnBorder,
    label: 'SYNCING',
    badgeClass: 'badge-warn',
    dotClass: 'dot-warn',
  },
  DEGRADED: {
    color: COLORS.warn,
    bg: COLORS.warnBg,
    border: COLORS.warnBorder,
    label: 'DEGRADED',
    badgeClass: 'badge-warn',
    dotClass: 'dot-warn',
  },
  CORRUPTED: {
    color: COLORS.down,
    bg: COLORS.downBg,
    border: COLORS.downBorder,
    label: 'CORRUPTED',
    badgeClass: 'badge-down',
    dotClass: 'dot-down',
  },
};

/**
 * Formatting & Type Helpers for JetBrains Mono Numeric Data Display
 */

/**
 * Format bytes into human-readable monospace string (B, KB, MB, GB).
 */
export function formatBytes(bytes: number, decimals: number = 2): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const val = parseFloat((bytes / Math.pow(k, i)).toFixed(dm));
  return `${val} ${sizes[i]}`;
}

/**
 * Format timestamp into ISO UTC / relative monospace string.
 */
export function formatTimestamp(timestampMsOrSec: number): string {
  const ms = timestampMsOrSec < 1e11 ? timestampMsOrSec * 1000 : timestampMsOrSec;
  return new Date(ms).toISOString().replace('T', ' ').replace('Z', ' UTC');
}

/**
 * Format latency offset in milliseconds.
 */
export function formatLatency(latencyMs: number): string {
  const prefix = latencyMs >= 0 ? '+' : '';
  return `${prefix}${latencyMs.toFixed(1)} ms`;
}

/**
 * Format Raft Term and Index.
 */
export function formatTerm(term: number): string {
  return `Term #${term}`;
}

export function formatCommitIndex(index: number): string {
  return `Commit #${index}`;
}

/**
 * Unified Design System Tokens Object Export
 */
export const TOKENS = {
  colors: COLORS,
  spacing: SPACING,
  fonts: FONTS,
  typography: TYPOGRAPHY,
  radii: RADII,
  borders: BORDERS,
  status: {
    cluster: CLUSTER_STATE_THEME,
    nodeState: NODE_STATE_THEME,
    nodeStatus: NODE_STATUS_THEME,
    fileStatus: FILE_STATUS_THEME,
  },
  formatters: {
    bytes: formatBytes,
    timestamp: formatTimestamp,
    latency: formatLatency,
    term: formatTerm,
    commitIndex: formatCommitIndex,
  },
} as const;

export default TOKENS;
