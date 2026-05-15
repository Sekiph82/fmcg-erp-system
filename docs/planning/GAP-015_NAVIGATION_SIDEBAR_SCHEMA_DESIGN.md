# GAP-015 Navigation and Sidebar — Schema Design

## Decision: No Database Changes Required

Navigation is entirely frontend-config driven (`nav-config.tsx`). No new backend tables, models, schemas, or services are needed.

GAP-015C (migration), GAP-015D (models), GAP-015E (schemas), GAP-015F (services), GAP-015G (endpoints), GAP-015I (permissions) are all **SKIPPED**.

---

## Changes Scoped for GAP-015H (Frontend)

### 1. Add Missing High-Value Nav Entries

The following routes exist and work but are not reachable via sidebar. Add them to appropriate existing sections:

| Route | Section to add to | Permission key |
|---|---|---|
| `/dashboard/reports` | `analytics` section | `reports.view` |
| `/dashboard/esign` | `administration` section | `esign.view` |
| `/dashboard/knowledge-base` | `administration` section | `knowledge_base.view` |
| `/dashboard/approvals` | existing `approvals` section if exists, else `administration` | `approvals.view` or `utilities.view` |
| `/dashboard/companies` | `administration` section | `utilities.view` |
| `/dashboard/wms` | `warehouse` section | `wms.view` |

### 2. Fix Admin Section Permission Guard

Current: section guard is `utilities.view`
Problem: items inside use `hr.view`, `users.view`, `audit.view`, `finance.view`, `knowledge_base.view`, `documents.view`, `esign.view`

Fix: change section guard to `users.view` (most restrictive common denominator that admin users will have, keeping the section visible to system admins without requiring all 7 domain permissions to be checked at section level — items still individually gate).

Alternative: split into sub-sections. But that's a larger structural change; single guard fix is surgical.

### 3. Fix Warehouse Section — Add Section-Level Permission

Current: no `permission` field on the warehouse section
Fix: add `permission: "inventory.view"` at the section level (warehouse is an inventory-adjacent module; all warehouse users have `inventory.view`).

### 4. Minor: Fix Tax Section Cross-Domain Items

Items inside the `tax` section that require `finance.view` should be either:
- Moved to the finance section, or
- Have their permission changed to `tax.view` if they are tax-scoped reports

Scope: inspect the 2 offending items and fix the permission to `tax.view` if appropriate.

---

## What NOT to Change

- Marketing section fragmentation: 15 permission codes reflect 15 genuinely distinct sub-modules; consolidating them would require a backend permission redesign. Record as known limitation.
- The 68-section vs 20-module mismatch: by design — nav is finer-grained than the registry. Not a defect.
- Remaining 30+ orphaned routes: some are intentionally deep-linked admin pages or under construction. Add only the 6 high-value ones above.
