# GAP-004 E2E Role Expectations

## Decision

GAP-004I does not need new production permissions or test-only roles. The current scoped access-control seed contract already supports the E2E workflow personas required for browser and backend workflow tests.

The E2E suite must use real users that are provisioned through normal development seed/admin flows. It must not hardcode credentials, weaken production roles, or grant broad mutation access just to make browser tests easier.

## Required Personas

### Admin-compatible user

Use for full shell, navigation, and broad smoke tests.

- Environment: `E2E_ADMIN_USERNAME` / `E2E_ADMIN_PASSWORD`
- Fallback: `E2E_USERNAME` / `E2E_PASSWORD`
- Expected role: `owner`, `admin`, or another superuser-equivalent role
- Expected access: all modules and global `AccessScope`

### Limited warehouse user

Use for scoped permission browser checks.

- Environment: `E2E_LIMITED_USERNAME` / `E2E_LIMITED_PASSWORD`
- Expected role: `warehouse_manager`
- Expected permissions:
  - `inventory.view_all`
  - `warehouses.view_all`
  - `inventory.edit_own_scope`
  - `inventory.adjust_own_scope`
  - `inventory.receive_own_scope`
  - `inventory.dispatch_own_scope`
  - `inventory.transfer_own_scope`
  - `cycle_count.perform_own_scope`
- Expected scope setup:
  - one assigned warehouse with mutation flags such as `can_edit`, `can_adjust`, `can_receive`, and `can_dispatch`
  - optional additional warehouse scopes with `can_view=true` and mutation flags false for view-only row checks

### Read-only auditor

Use for future view-only workflow checks where useful.

- Expected role: `read_only_auditor`
- Expected permissions: assigned-scope view permissions and optional `auditor.export`
- Expected mutation access: none

## Seed Contract

The seed definitions keep production security intact:

- `owner` and `admin` receive global default scopes.
- Operational roles such as `warehouse_manager`, `production_manager`, `quality_manager`, `procurement_manager`, `regional_sales_manager`, and `scoped_finance_manager` require explicit `AccessScope` assignment.
- Read-only users do not receive mutation permissions.
- E2E credentials remain environment-driven and are skipped when missing.

## Checks

The backend E2E contract tests verify:

- warehouse manager roles have broad inventory visibility but scoped mutation permissions
- operational E2E roles do not receive default global scopes
- read-only auditor roles do not contain mutation permissions

