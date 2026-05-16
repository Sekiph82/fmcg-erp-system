/**
 * NEON LIQUID GLASS — reusable theme constants.
 * Use these in workspace components, tab content, and module pages
 * to maintain visual consistency across all consolidated workspaces.
 *
 * The dark-theme CSS classes in globals.css already override .bg-white → glass.
 * These constants make intent explicit and avoid drift.
 */

// ── Glass surfaces ─────────────────────────────────────────────────────────────

/** Primary glass panel — section cards, filter bars, info panels */
export const glassPanelClass =
  "liquid-glass";

/** Slightly stronger glass — KPI cards, feature cards with glow */
export const glassCardClass =
  "glow-card";

/** Drawer/modal glass — strongest blur, max opacity */
export const glassModalClass =
  "glass-modal";

/** Table container glass */
export const glassTableClass =
  "glass-table";

// ── Glow effects ───────────────────────────────────────────────────────────────

/** Hover glow only — use on rows, list items */
export const glowHoverClass =
  "glow-hover";

/** Neon border ring */
export const neonBorderClass =
  "neon-border";

// ── Buttons ────────────────────────────────────────────────────────────────────

/** Primary CTA button — blue/indigo gradient with glow */
export const glowButtonClass =
  "glow-button";

/** Secondary / ghost button — glass bg, neon border */
export const glowButtonSecondaryClass =
  "glow-button-secondary";

// ── Workspace shell ────────────────────────────────────────────────────────────

/** Workspace page outer shell */
export const workspaceShellClass =
  "flex flex-col h-full min-h-0";

/** Workspace header bar */
export const workspaceHeaderClass =
  "flex items-center justify-between px-6 py-4 shrink-0 border-b border-cyan-500/20 bg-[rgba(15,23,42,0.70)] backdrop-blur-xl";

/** Workspace tab bar */
export const workspaceTabBarClass =
  "relative flex items-center border-b border-cyan-500/20 bg-[rgba(15,23,42,0.65)] backdrop-blur-xl overflow-x-auto scrollbar-hide";

/** Inactive tab button */
export const workspaceTabClass =
  "relative flex items-center whitespace-nowrap px-4 py-3 text-sm font-medium transition-colors duration-150 shrink-0 text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]";

/** Active tab button — neon cyan accent */
export const workspaceActiveTabClass =
  "relative flex items-center whitespace-nowrap px-4 py-3 text-sm font-medium transition-colors duration-150 shrink-0 text-cyan-300 after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:bg-gradient-to-r after:from-cyan-500 after:to-blue-500";

/** Workspace content area */
export const workspaceContentClass =
  "flex-1 min-h-0 overflow-auto p-6 lg:p-8";

// ── Drawer ─────────────────────────────────────────────────────────────────────

/** Drawer side panel */
export const workspaceDrawerClass =
  "fixed right-0 top-0 bottom-0 glass-modal flex flex-col border-l border-cyan-500/25";

/** Drawer backdrop overlay */
export const workspaceDrawerBackdropClass =
  "fixed inset-0 bg-black/60 backdrop-blur-[2px] z-40 transition-opacity";

/** Drawer header */
export const workspaceDrawerHeaderClass =
  "flex items-center justify-between px-6 py-4 shrink-0 border-b border-cyan-500/20";

// ── Section / card primitives ──────────────────────────────────────────────────

/** Section card — wraps a table or list block */
export const workspaceSectionClass =
  "glass-panel p-0 overflow-hidden";

/** Inline glass card for metrics / info blocks */
export const workspaceMetricCardClass =
  "glow-card p-4";

// ── Empty state ────────────────────────────────────────────────────────────────

/** Icon container for empty states */
export const emptyIconContainerClass =
  "rounded-full border border-blue-500/25 bg-blue-500/10 p-4 mb-4";

/** Empty state heading */
export const emptyHeadingClass =
  "text-sm font-medium text-slate-300";

/** Empty state body text */
export const emptyBodyClass =
  "mt-1 text-sm text-slate-500 max-w-xs";

// ── Permission gate ────────────────────────────────────────────────────────────

/** Wrapper shown when permission is denied */
export const permissionDeniedClass =
  "flex flex-col items-center justify-center h-full py-24 text-slate-500";

// ── Status badge colors ────────────────────────────────────────────────────────

/** Map status → border-l color for glow-card stripe */
export const statusBorderColor = {
  ok:       "border-l-emerald-500",
  warning:  "border-l-amber-500",
  critical: "border-l-red-500",
  info:     "border-l-blue-500",
  pending:  "border-l-violet-500",
} as const;

/** Text colors for status pills */
export const statusTextColor = {
  DRAFT:       "text-blue-300",
  CONFIRMED:   "text-cyan-300",
  IN_PROGRESS: "text-amber-300",
  COMPLETED:   "text-emerald-300",
  CANCELLED:   "text-red-400",
  ON_HOLD:     "text-orange-300",
} as const;

/** Background colors for status pills */
export const statusBgColor = {
  DRAFT:       "bg-blue-500/15 border border-blue-500/30",
  CONFIRMED:   "bg-cyan-500/15 border border-cyan-500/30",
  IN_PROGRESS: "bg-amber-500/15 border border-amber-500/30",
  COMPLETED:   "bg-emerald-500/15 border border-emerald-500/30",
  CANCELLED:   "bg-red-500/15 border border-red-500/30",
  ON_HOLD:     "bg-orange-500/15 border border-orange-500/30",
} as const;
