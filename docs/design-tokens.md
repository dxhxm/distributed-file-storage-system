# DFSS Design Tokens & Type System Specification

This document defines the visual language, design token architecture, and type system rules for the **Distributed Fault-Tolerant File Storage System (DFSS)** Web UI.

---

## 1. Visual Philosophy & Design Identity

The DFSS UI is designed as a **pure systems tool for distributed infrastructure**:
- **Identity from Consensus:** The visual language reflects the Raft cluster state: nodes keeping pulse, electing leaders, and replicating file chunks.
- **Zero "AI Dashboard" Slop:** No diffuse multi-layer box shadows, no glowing neon accents, no rounded data cards (`0px` border-radius on data rows, tables, panels, and containers).
- **Hairline Precision:** Structural panels and tables use hairline `1px solid var(--color-line)` dividers on deep slate-charcoal backgrounds (`#0F1210`, `#171B18`).
- **Strict Dual Font Pairing:**
  - **JetBrains Mono:** Dedicated exclusively to all numeric, telemetry, and system data (Node IDs, Raft terms, commit indices, byte sizes, timestamps, network latency, checksums, status codes, ports). Monospace numbers use tabular alignment (`tabular-nums`).
  - **Inter:** Dedicated to descriptive and interface copy (labels, section titles, table column headers, helper text, empty states, alerts, modal dialogs).

---

## 2. Locked Color Palette

> **Strict Rule:** No ad-hoc hex values anywhere in the codebase. All styles must reference the locked CSS custom properties or TypeScript token constants.

### Base Canvas & Surfaces
| Token (CSS) | TypeScript Key | Hex Value | Purpose |
| :--- | :--- | :--- | :--- |
| `--color-bg` (`--bg`) | `COLORS.bg` | `#0F1210` | Base canvas background (near-black with subtle slate-green cast) |
| `--color-surface` (`--surface`) | `COLORS.surface` | `#171B18` | Primary panel, card, and table background |
| `--color-surface-subtle` | `COLORS.surfaceSubtle` | `#131714` | Inset table headers, nested panels, and code blocks |
| `--color-surface-hover` | `COLORS.surfaceHover` | `#1E231F` | Interactive row and button hover state |
| `--color-surface-active` | `COLORS.surfaceActive` | `#242A25` | Pressed and selected item state |
| `--color-surface-muted` | `COLORS.surfaceMuted` | `#1A1F1B` | Secondary recessed surface |

### Hairline Structural Dividers
| Token (CSS) | TypeScript Key | Hex Value | Purpose |
| :--- | :--- | :--- | :--- |
| `--color-line` (`--line`) | `COLORS.line` | `#2A2F2B` | Canonical 1px divider and panel border |
| `--color-line-subtle` | `COLORS.lineSubtle` | `#1F2420` | Nested cell dividers and sub-borders |
| `--color-line-bright` | `COLORS.lineBright` | `#3D443E` | Focused, active, or highlighted element border |

### Ink & Typography
| Token (CSS) | TypeScript Key | Hex Value | Purpose |
| :--- | :--- | :--- | :--- |
| `--color-ink` (`--ink`) | `COLORS.ink` | `#E8ECE9` | High-contrast primary text, metrics, and data values |
| `--color-ink-secondary` | `COLORS.inkSecondary` | `#C2C9C3` | Secondary descriptive text and section descriptions |
| `--color-muted` (`--muted`) | `COLORS.muted` | `#8A928C` | Low-contrast labels, units, and timestamps |
| `--color-ink-disabled` | `COLORS.inkDisabled` | `#4E5550` | Disabled text and unavailable metrics |

### Semantic Status Tokens (Muted Systems Hues)
| Token (CSS) | TypeScript Key | Hex Value | Semantic State |
| :--- | :--- | :--- | :--- |
| `--color-ok` (`--ok`) | `COLORS.ok` | `#5FB88A` | Cluster `HEALTHY`, Node `LEADER`, Node `ONLINE`, File `REPLICATED` |
| `--color-ok-bg` | `COLORS.okBg` | `#14291E` | Muted green badge background |
| `--color-ok-border` | `COLORS.okBorder` | `#23543A` | Muted green badge border |
| `--color-warn` (`--warn`) | `COLORS.warn` | `#D9A441` | Cluster `OPERATIONAL`, Node `CANDIDATE`, File `SYNCING` / `DEGRADED` |
| `--color-warn-bg` | `COLORS.warnBg` | `#2B2211` | Muted amber badge background |
| `--color-warn-border` | `COLORS.warnBorder` | `#57431B` | Muted amber badge border |
| `--color-down` (`--down`) | `COLORS.down` | `#C15B4A` | Cluster `NO MAJORITY`, Node `OFFLINE`, File `CORRUPTED` |
| `--color-down-bg` | `COLORS.downBg` | `#291614` | Muted crimson badge background |
| `--color-down-border` | `COLORS.downBorder` | `#522520` | Muted crimson badge border |
| `--color-info` (`--info`) | `COLORS.info` | `#6499B8` | Passive telemetry, informational links, follower indicator |
| `--color-info-bg` | `COLORS.infoBg` | `#13242E` | Muted slate-blue badge background |
| `--color-info-border` | `COLORS.infoBorder` | `#20455B` | Muted slate-blue badge border |

---

## 3. Typography & Font Pairing Rules

```
                      ┌──────────────────────────────────────────────┐
                      │                 DFSS UI TYPE                 │
                      └──────────────────────┬───────────────────────┘
                                             │
                   ┌─────────────────────────┴─────────────────────────┐
                   ▼                                                   ▼
         ┌───────────────────┐                               ┌───────────────────┐
         │   JetBrains Mono  │                               │       Inter       │
         ├───────────────────┤                               ├───────────────────┤
         │ • Node IDs        │                               │ • Section Headers │
         │ • Byte Sizes      │                               │ • Labels / Keys   │
         │ • Timestamps      │                               │ • Column Headers  │
         │ • Raft Terms      │                               │ • Explanations    │
         │ • Latency (+ms)   │                               │ • Empty States    │
         │ • Hashes/Checksums│                               │ • Modal Messages  │
         │ • Ports & URLs    │                               │ • Form Tooltips   │
         └───────────────────┘                               └───────────────────┘
```

### Type Scale
| Token | Rem Value | Pixel Value | Typical Application |
| :--- | :--- | :--- | :--- |
| `--text-2xs` | `0.6875rem` | 11px | Micro lane markers, compact status dots |
| `--text-xs` | `0.75rem` | 12px | Column headers, units, secondary labels |
| `--text-sm` | `0.8125rem` | 13px | Standard table rows, timestamps, node IDs, values |
| `--text-base` | `0.875rem` | 14px | Primary body text, interactive controls |
| `--text-md` | `1.000rem` | 16px | Subheadings, modal titles, panel captions |
| `--text-lg` | `1.125rem` | 18px | Panel titles, metric summaries |
| `--text-xl` | `1.250rem` | 20px | Section headers, cluster health summary |
| `--text-2xl` | `1.500rem` | 24px | System dashboard title |

---

## 4. Spacing Scale (4px Base Grid)

| Token | Rem | Pixels | Application |
| :--- | :--- | :--- | :--- |
| `--space-1` | `0.25rem` | 4px | Inline icon gaps, badge vertical padding |
| `--space-1-5` | `0.375rem` | 6px | Dense list item spacing |
| `--space-2` | `0.50rem` | 8px | Standard button padding, badge horizontal padding |
| `--space-2-5` | `0.625rem` | 10px | Table cell padding |
| `--space-3` | `0.75rem` | 12px | Compact container padding, card header margin |
| `--space-4` | `1.00rem` | 16px | Panel padding, standard component gutter |
| `--space-5` | `1.25rem` | 20px | Section gap |
| `--space-6` | `1.50rem` | 24px | Grid column spacing |
| `--space-8` | `2.00rem` | 32px | Major layout container padding |
| `--space-12` | `3.00rem` | 48px | Page margins |

---

## 5. Geometry, Radii & Elevation Rules

- `--radius-none: 0px` — **Mandatory** on all data panels, data rows, tables, dividers, and status strips.
- `--radius-sm: 2px` — Micro badges and status indicator pills.
- `--radius-md: 4px` — **Only** for interactive inputs (`<input>`, `<select>`) and action buttons (`<button>`).
- `--shadow-none: none` — **No diffuse drop shadows** or blurred elevation layers.

---

## 6. How to Use Tokens

### In CSS
```css
@import './styles/tokens.css';

.my-node-panel {
  background-color: var(--color-surface);
  border: 1px solid var(--color-line);
  border-radius: var(--radius-none);
  padding: var(--space-4);
}

.my-node-id {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--color-ink);
}

.my-node-label {
  font-family: var(--font-sans);
  font-size: var(--text-xs);
  color: var(--color-muted);
}
```

### In TypeScript / JavaScript
```typescript
import {
  TOKENS,
  COLORS,
  CLUSTER_STATE_THEME,
  formatBytes,
  formatTimestamp,
  formatLatency,
} from 'dfss-frontend';

// Applying locked color programmatically
const leaderColor = TOKENS.colors.ok; // '#5FB88A'

// Mapping cluster status to theme
const visual = CLUSTER_STATE_THEME['HEALTHY'];
console.log(visual.badgeClass, visual.color); // 'badge-ok', '#5FB88A'

// Monospace numeric formatting
const sizeStr = formatBytes(1048576); // '1 MB'
const tsStr = formatTimestamp(1700000000); // '2023-11-14 22:13:20.000 UTC'
const latencyStr = formatLatency(12.4); // '+12.4 ms'
```

---

## 7. Anti-Patterns Checklist

| Prohibited Anti-Pattern | Correct DFSS Design Token Practice |
| :--- | :--- |
| ❌ Inline hex values (e.g. `color: #00ff88`) | ✅ Use `var(--color-ok)` or `COLORS.ok` |
| ❌ `border-radius: 8px` / `12px` on data tables | ✅ `border-radius: var(--radius-none)` (`0px`) |
| ❌ `box-shadow: 0 10px 30px rgba(0,0,0,0.5)` | ✅ Hairline borders `border: 1px solid var(--color-line)` |
| ❌ Neon gradients or colorful blurred backgrounds | ✅ Pure flat background `var(--color-bg)` |
| ❌ Rendering IDs or byte sizes in `Inter` | ✅ Use `var(--font-mono)` with `tabular-nums` |
| ❌ Rendering labels or descriptions in `Mono` | ✅ Use `var(--font-sans)` (`Inter`) |
