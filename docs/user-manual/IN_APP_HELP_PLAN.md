# In-App Help Plan

**Date:** 2026-05-18  
**Status:** Design only — not yet implemented

---

## Goal

Allow users to access context-sensitive help directly from each ERP workspace without leaving the app.

---

## Help Button Design

Add a `?` icon button to the workspace header of each module. Clicking it opens a help panel or links to the relevant manual section.

Location: Top-right of each workspace header (next to the workspace title and action buttons).

```tsx
// Workspace header (existing component)
<WorkspaceHeader title="Production" helpHref="/help/production" />
```

---

## Link from Route/Tab to Manual Section

Each workspace and tab maps to a specific manual anchor:

| Route | Help URL |
|---|---|
| /dashboard/production | /help/production |
| /dashboard/production?tab=orders | /help/production#orders-tab |
| /dashboard/inventory | /help/inventory |
| /dashboard/admin?tab=users | /help/admin#users-tab |

Mapping stored in `frontend/src/lib/helpLinks.ts`:
```ts
export const HELP_LINKS: Record<string, string> = {
  "/dashboard/production": "/help/production",
  "/dashboard/production?tab=orders": "/help/production#orders-tab",
  // ...
};
```

---

## Searchable Help Center

`/help` route (public, no auth required) serves static HTML/Markdown help pages.

Search: client-side full-text search via FlexSearch or Fuse.js over help page content.

---

## Role-Based Help

If user is logged in, show help sections relevant to their role:
- Production user → see production, BOM, shop floor help
- Admin → see full help

Powered by the permission context already available in the frontend.

---

## Screenshot Thumbnails

Help panels show a small thumbnail of the relevant screenshot. On click, opens full-size image overlay.

```tsx
<HelpPanel
  screenshot="/help/images/021_production_orders.png"
  alt="Production Orders tab"
  manualUrl="/help/production#orders-tab"
/>
```

---

## Future: Training Videos

Placeholder `[▶ Watch video]` links in help panels. Videos hosted on a private YouTube or internal server. Not implemented in Phase 1.

---

## Versioned Manual Pages

Manual content versioned alongside software releases. When a breaking UI change ships, bump the help content version and archive the old version at `/help/v1/...`.

---

## Admin-Controlled Help Content (Phase 3)

Admin panel section to override help text per workspace without a code deploy. Stored in database as markdown blobs. Allows operations team to add local context (e.g., "our PO approval policy requires 2 signatures").

---

## Implementation Phases

| Phase | What | When |
|---|---|---|
| 1 | `?` button on workspace header, links to static manual | Post go-live week 2 |
| 2 | In-app help panel overlay with screenshot thumbnail | Post go-live month 2 |
| 3 | Search, role-based filtering, video links | Post go-live month 3 |
| 4 | Admin-editable help content | Future |

---

## Do Not Implement Yet

Do not modify any workspace components until:
1. Manual content is finalized and reviewed
2. Go-live is stable
3. UI change is approved by product owner
