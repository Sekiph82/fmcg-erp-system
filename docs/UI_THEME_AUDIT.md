# UI Theme Audit

Generated: 2026-05-16

## Design System: NEON LIQUID GLASS

Full-system dark theme. Deep navy background (#020817 / #071426) with glass-effect panels, cyan/blue/indigo/purple neon glow accents, and backdrop-blur surfaces.

---

## 1. Glass-Effect Classes

| Class | Source | Description |
|-------|--------|-------------|
| `.liquid-glass` | globals.css | Base glass panel: bg rgba(15,23,42,0.58), blur(18px) saturate(170%), border rgba(96,165,250,0.24), rounded-[18px] |
| `.glass-panel` | globals.css | Lighter glass panel: blur(14px), border rgba(96,165,250,0.22), rounded-[16px] |
| `.glass-table` | globals.css | Glass table wrapper: blur(14px), thead bg rgba(15,23,42,0.70), th cyan, row hover blue glow |
| `.glass-modal` | globals.css | Strong glass for modals/drawers: blur(24px) saturate(180%), border rgba(96,165,250,0.35), rounded-[20px] |
| `[data-theme="dark"] .bg-white` | globals.css | Auto-override: any `bg-white` in dark scope becomes glass surface |
| `[data-theme="dark"] .bg-gray-50` | globals.css | Becomes rgba(8,20,50,0.65) with blur(8px) |

---

## 2. Glow-Effect Classes

| Class | Source | Description |
|-------|--------|-------------|
| `.glow-card` | globals.css | Card with multi-layer box-shadow glow (blue+purple). Hover: lift + stronger glow |
| `.glow-hover` | globals.css | Adds glow on hover: translateY(-1px), shadow cyan/purple |
| `.neon-border` | globals.css | 1px border rgba(96,165,250,0.35) + subtle box-shadow glow |
| `.neon-focus:focus` | globals.css | Focus ring: border cyan, box-shadow blue ring + glow |
| `.sidebar-text-glow` | globals.css | Text + text-shadow glow on hover/active, cyan/indigo palette |

CSS Custom Properties for glow:
```
--glow-cyan: 34,211,238
--glow-blue: 59,130,246
--glow-indigo: 99,102,241
--glow-purple: 139,92,246
--glow-pink: 217,70,239
--glow-primary: 0 0 14px rgba(0,180,255,0.45)
--glow-primary-lg: 0 0 28px rgba(0,180,255,0.35), 0 0 60px rgba(0,180,255,0.12)
```

---

## 3. Gradient Background Patterns

Main background (applied to `[data-theme="dark"] main`):
```css
radial-gradient(circle at 12% 8%, rgba(59,130,246,0.18) 0%, transparent 35%),
radial-gradient(circle at 88% 90%, rgba(139,92,246,0.16) 0%, transparent 35%),
radial-gradient(circle at 55% 45%, rgba(0,160,255,0.05) 0%, transparent 55%),
linear-gradient(135deg, #020817 0%, #071426 45%, #020817 100%)
```

Glow button gradient:
```css
linear-gradient(135deg, rgba(37,99,235,0.85) 0%, rgba(79,70,229,0.80) 50%, rgba(109,40,217,0.75) 100%)
```

KPI card status accents: `border-l-emerald-500`, `border-l-amber-500`, `border-l-red-500`

Blob accent pattern (optional): `radial-gradient` blobs at corners for visual depth.

---

## 4. Card Styles

| Style | Usage |
|-------|-------|
| `.glow-card` | KPICard, feature cards. Has `border-l-4` status stripe, `active:scale-[0.98]` press effect |
| `.liquid-glass` | Section cards, filter panels, info panels |
| `.glass-panel` | Lighter content areas, sub-panels |

KPICard pattern (from `components/dashboard/KPICard.tsx`):
```tsx
<div className="glow-card relative flex flex-col justify-between gap-2 border-l-4 border-l-emerald-500 p-4">
  <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">{label}</p>
  <p className="text-2xl font-bold text-slate-100">{value}</p>
</div>
```

---

## 5. Button Styles

| Class | Usage |
|-------|-------|
| `.glow-button` | Primary CTA. Blue/indigo gradient, neon glow, hover lift |
| `.glow-button-secondary` | Secondary action. Glass bg, neon border, hover glow |

Both buttons already used in WorkspaceHeader actions.

---

## 6. Tab Styles (Current / Required)

Current (plain):
- Tab bar: `bg-white border-b border-gray-200`
- Active: `text-blue-700 after:bg-blue-600`
- Inactive: `text-gray-500 hover:bg-gray-50`

Required (glass/neon):
- Tab bar: `bg-[rgba(15,23,42,0.65)] backdrop-blur-xl border-b border-cyan-500/20`
- Active: `text-cyan-300` + neon underline gradient
- Inactive: `text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]`

---

## 7. Table/List Panel Styles

Use `.glass-table`:
- Container: `glass-table` class
- Header: `text-cyan-400/85` column headers, uppercase, 0.75rem
- Rows: hover `rgba(59,130,246,0.08)` tint
- Borders: `rgba(96,165,250,0.07)` between rows

---

## 8. Sidebar/Search Styles

Sidebar background: `#020c18` with `border-r border-cyan-500/10`
Active item: neon glow via `.sidebar-text-glow.active`
CommandPalette/search: glass-modal styling

---

## 9. Light/Dark Mode Behavior

The app is **dark-mode first**. `[data-theme="dark"]` is applied to the right-column div in DashboardShell. CSS overrides in globals.css map light classes to dark equivalents:
- `.bg-white` → `var(--glass-bg)` + blur
- `.bg-gray-50` → `rgba(8,20,50,0.65)` + blur
- `.text-gray-900` → `#def0ff`
- `.text-gray-600` → `#6aaad0`

Light mode: uses default Tailwind classes. Not a design target for this app.

---

## 10. Recommended Reusable Theme Classes

See `frontend/src/lib/ui-theme.ts` for TypeScript constants.

### Key patterns:

**Glass panel:**
```
liquid-glass  (from globals.css)
glass-panel   (lighter variant)
glass-modal   (drawers, modals)
glass-table   (data tables)
```

**Glow cards:**
```
glow-card     (KPI and feature cards)
glow-hover    (hover-only glow)
```

**Buttons:**
```
glow-button           (primary)
glow-button-secondary (secondary)
```

**Tab bar (explicit dark):**
```
bg-[rgba(15,23,42,0.65)] backdrop-blur-xl border-b border-cyan-500/20
```

**Active tab:**
```
text-cyan-300 + pseudo-element gradient underline
```

**Text hierarchy:**
```
text-slate-100   heading
text-slate-300   body
text-slate-400   muted / label
text-cyan-400    column header accent
```

---

## Cluster Visual Notes

### Marketing
- Campaigns, ads, promotions use colored badge pills (blue/green/amber/red)
- KPI cards use glow-card with brand-specific glow tints

### Finance/Accounting
- Accounting uses blue/emerald accent gradients on cards
- Invoice and ledger tables use glass-table
- Report tiles use soft glass-panel with border-l accent

### Production
- Status pills: amber (in-progress), green (completed), red (cancelled), blue (draft)
- Machine/shift cards: high-contrast status glow with border-l-4 pattern

### Utility-Management
- Energy meters: color-coded glow (electricity=yellow, water=blue, solar=emerald, steam=orange)
- KPI center: glow-card grid layout
