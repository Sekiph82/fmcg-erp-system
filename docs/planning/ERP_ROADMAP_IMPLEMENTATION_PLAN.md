# ERP Roadmap Implementation Plan

Source: `C:/Users/sekip/Desktop/fmcg-erp-system-main/docs/planning/butun modulleri yaptir.docx`
Generated: 2026-05-10T22:18:26

## Execution Order

1. PHASE 0 - Planning and automation setup
2. PHASE 1 - Documentation manual workflow
3. PHASE 2 - Critical ERP foundations
4. PHASE 3 - High-importance operational modules
5. PHASE 4 - UX/reporting/extensibility
6. PHASE 5 - FMCG/regulatory polish
7. PHASE 6 - Advanced/future roadmap

## Main Roadmap Items

### GAP-001: Enterprise-Grade Accounting Core Depth

- Tier: Tier 1 - Critical Gaps
- Phase: Phase 2 - Critical ERP foundations
- Business priority: Critical
- Technical area: Finance / Accounting
- Files likely involved: `backend/app/models`, `backend/app/schemas`, `backend/app/api/v1/endpoints/finance.py`, `backend/app/services`, `frontend/src/app/dashboard/finance`, `alembic/versions`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-001A: Audit current implementation: Enterprise-Grade Accounting Core Depth

- Status: DONE
- Dependencies: USER_OVERRIDE_AFTER_GAP-028K_BLOCKED
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-001B: Design data model/schema: Enterprise-Grade Accounting Core Depth

- Status: DONE
- Dependencies: GAP-001A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs in `docs/planning/GAP-001_ACCOUNTING_CORE_SCHEMA_DESIGN.md`.

#### GAP-001C: Add or update database migrations: Enterprise-Grade Accounting Core Depth

- Status: DONE
- Dependencies: GAP-001B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result. Added `backend/alembic/versions/20260511_0010_enterprise_accounting_core.py`; live DB upgrade was blocked because Docker/PostgreSQL was not running.

#### GAP-001D: Add or update backend models: Enterprise-Grade Accounting Core Depth

- Status: DONE
- Dependencies: GAP-001C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths. Updated `backend/app/models/finance.py`.

#### GAP-001E: Add or update schemas: Enterprise-Grade Accounting Core Depth

- Status: DONE
- Dependencies: GAP-001D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior. Updated `backend/app/schemas/finance.py`.

#### GAP-001F: Add or update services/business logic: Enterprise-Grade Accounting Core Depth

- Status: DONE
- Dependencies: GAP-001E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules. Added accounting controls to `backend/app/services/finance_service.py`.

#### GAP-001G: Add or update API endpoints: Enterprise-Grade Accounting Core Depth

- Status: DONE
- Dependencies: GAP-001F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions. Updated `backend/app/api/v1/endpoints/finance.py`.

#### GAP-001H: Add or update frontend screens/components: Enterprise-Grade Accounting Core Depth

- Status: DONE
- Dependencies: GAP-001G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior. Added `frontend/src/app/dashboard/finance/accounting/controls/page.tsx`.

#### GAP-001I: Add or update permissions/roles: Enterprise-Grade Accounting Core Depth

- Status: DONE
- Dependencies: GAP-001H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes. Added `finance.configure` for accounting controls.

#### GAP-001J: Add or update tests: Enterprise-Grade Accounting Core Depth

- Status: DONE
- Dependencies: GAP-001I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands. Added `backend/tests/test_gap001_accounting_core.py`.

#### GAP-001K: Add or update documentation: Enterprise-Grade Accounting Core Depth

- Status: DONE
- Dependencies: GAP-001J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Added `docs/planning/GAP-001_ACCOUNTING_CORE_IMPLEMENTATION_NOTES.md`.

#### GAP-001L: Run checks and record result: Enterprise-Grade Accounting Core Depth

- Status: DONE
- Dependencies: GAP-001K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Commands/results recorded in `CODEX_PROGRESS.md`; live DB migration is blocked until Docker/PostgreSQL is available.

### GAP-002: Accounting-to-Inventory-to-Manufacturing Posting Integration

- Tier: Tier 1 - Critical Gaps
- Phase: Phase 2 - Critical ERP foundations
- Business priority: Critical
- Technical area: Finance / Inventory / Manufacturing
- Files likely involved: `backend/app/services`, `backend/app/models`, `backend/app/api/v1/endpoints/inventory.py`, `backend/app/api/v1/endpoints/production.py`, `backend/tests`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-002A: Audit current implementation: Accounting-to-Inventory-to-Manufacturing Posting Integration

- Status: DONE
- Dependencies: GAP-001L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix. Added `docs/planning/GAP-002_POSTING_INTEGRATION_AUDIT.md`.

#### GAP-002B: Design data model/schema: Accounting-to-Inventory-to-Manufacturing Posting Integration

- Status: DONE
- Dependencies: GAP-002A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions. Content check passed for posting event table, account mapping table, posting/journal links, idempotency, period enforcement, and key posting examples.
- Documentation requirements: Document model decisions and migration needs. Added `docs/planning/GAP-002_POSTING_INTEGRATION_SCHEMA_DESIGN.md`.

#### GAP-002C: Add or update database migrations: Accounting-to-Inventory-to-Manufacturing Posting Integration

- Status: DONE
- Dependencies: GAP-002B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration compile, Alembic head/history, and offline SQL generation passed. Live `alembic upgrade head` is blocked because PostgreSQL refused the local connection.
- Documentation requirements: Record migration command and result. Added `backend/alembic/versions/20260511_0020_operational_posting_integration.py`.

#### GAP-002D: Add or update backend models: Accounting-to-Inventory-to-Manufacturing Posting Integration

- Status: DONE
- Dependencies: GAP-002C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models compile/import successfully; mapper configuration and required table/column smoke checks passed.
- Documentation requirements: Document model paths. Updated `backend/app/models/finance.py`, `backend/app/models/inventory.py`, `backend/app/models/procurement.py`, `backend/app/models/production.py`, `backend/app/models/landed_cost.py`, and `backend/app/models/__init__.py`.

#### GAP-002E: Add or update schemas: Accounting-to-Inventory-to-Manufacturing Posting Integration

- Status: DONE
- Dependencies: GAP-002D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schema compile and Pydantic smoke validation passed, including account-mapping scope validation.
- Documentation requirements: Document API schema behavior. Updated finance, inventory, procurement, production, and landed-cost schemas with posting event, account mapping, posting-link, and posting-status read fields.

#### GAP-002F: Add or update services/business logic: Accounting-to-Inventory-to-Manufacturing Posting Integration

- Status: DONE
- Dependencies: GAP-002E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Service compile and smoke checks passed for deterministic keys, account-mapping specificity, and posting-link application. Existing workflows are not rewired yet.
- Documentation requirements: Document business rules. Added finance service helpers for idempotency, account mapping lookup, operational posting events, posting links, and posted/failed status updates.

#### GAP-002G: Add or update API endpoints: Accounting-to-Inventory-to-Manufacturing Posting Integration

- Status: DONE
- Dependencies: GAP-002F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Finance endpoint compile and route smoke checks passed.
- Documentation requirements: Document endpoints and permissions. Added `finance.view` audit endpoints for operational posting events and `finance.configure` inventory account mapping create/update endpoints.

#### GAP-002H: Add or update frontend screens/components: Accounting-to-Inventory-to-Manufacturing Posting Integration

- Status: DONE
- Dependencies: GAP-002G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: Frontend type-check passed.
- Documentation requirements: Document frontend paths and user behavior. Extended `frontend/src/app/dashboard/finance/accounting/controls/page.tsx` and `frontend/src/lib/finance.ts` for operational posting event visibility and inventory account mapping configuration.

#### GAP-002I: Add or update permissions/roles: Accounting-to-Inventory-to-Manufacturing Posting Integration

- Status: DONE
- Dependencies: GAP-002H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Permission surface inspection passed. New endpoints use existing `finance.view` and `finance.configure`; no unsafe execute endpoint was added.
- Documentation requirements: Document role matrix changes. Existing CFO and finance manager seed role templates already include `finance.configure`; no new role template change required.

#### GAP-002J: Add or update tests: Accounting-to-Inventory-to-Manufacturing Posting Integration

- Status: DONE
- Dependencies: GAP-002I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Focused GAP-002 tests passed; GAP-001/GAP-002 regression test pair passed.
- Documentation requirements: Document test files and commands. Added `backend/tests/test_gap002_posting_integration.py`.

#### GAP-002K: Add or update documentation: Accounting-to-Inventory-to-Manufacturing Posting Integration

- Status: DONE
- Dependencies: GAP-002J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Documentation content check passed and explicitly states live operational GL auto-posting is not fully wired yet.
- Documentation requirements: Documentation updated. Added `docs/planning/GAP-002_POSTING_INTEGRATION_IMPLEMENTATION_NOTES.md`.

#### GAP-002L: Run checks and record result: Accounting-to-Inventory-to-Manufacturing Posting Integration

- Status: DONE
- Dependencies: GAP-002K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Backend compile, focused/regression pytest, Alembic heads/history/offline SQL, frontend type-check, and docs checks passed. Live `alembic upgrade head` remains blocked by PostgreSQL connection refusal.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-003: Permission and Security Hardening Across All New Modules

- Tier: Tier 1 - Critical Gaps
- Phase: Phase 2 - Critical ERP foundations
- Business priority: Critical
- Technical area: Security / RBAC
- Files likely involved: `backend/app/core/deps.py`, `backend/app/core/module_registry.py`, `backend/app/api/v1`, `backend/tests`, `frontend/src/components/Sidebar.tsx`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-003A: Audit current implementation: Permission and Security Hardening Across All New Modules

- Status: DONE
- Dependencies: GAP-002L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix. Added `docs/planning/GAP-003_PERMISSION_SECURITY_AUDIT.md`.

#### GAP-003B: Design data model/schema: Permission and Security Hardening Across All New Modules

- Status: TODO
- Dependencies: GAP-003A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-003C: Add or update database migrations: Permission and Security Hardening Across All New Modules

- Status: TODO
- Dependencies: GAP-003B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-003D: Add or update backend models: Permission and Security Hardening Across All New Modules

- Status: TODO
- Dependencies: GAP-003C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-003E: Add or update schemas: Permission and Security Hardening Across All New Modules

- Status: TODO
- Dependencies: GAP-003D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-003F: Add or update services/business logic: Permission and Security Hardening Across All New Modules

- Status: TODO
- Dependencies: GAP-003E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-003G: Add or update API endpoints: Permission and Security Hardening Across All New Modules

- Status: TODO
- Dependencies: GAP-003F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-003H: Add or update frontend screens/components: Permission and Security Hardening Across All New Modules

- Status: TODO
- Dependencies: GAP-003G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-003I: Add or update permissions/roles: Permission and Security Hardening Across All New Modules

- Status: TODO
- Dependencies: GAP-003H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-003J: Add or update tests: Permission and Security Hardening Across All New Modules

- Status: TODO
- Dependencies: GAP-003I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-003K: Add or update documentation: Permission and Security Hardening Across All New Modules

- Status: TODO
- Dependencies: GAP-003J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-003L: Run checks and record result: Permission and Security Hardening Across All New Modules

- Status: TODO
- Dependencies: GAP-003K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-004: End-to-End Workflow Completion Testing

- Tier: Tier 1 - Critical Gaps
- Phase: Phase 2 - Critical ERP foundations
- Business priority: Critical
- Technical area: Testing / ERP workflows
- Files likely involved: `backend/tests`, `frontend/tests`, `demo-data`, `docs`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-004A: Audit current implementation: End-to-End Workflow Completion Testing

- Status: TODO
- Dependencies: GAP-003L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-004B: Design data model/schema: End-to-End Workflow Completion Testing

- Status: TODO
- Dependencies: GAP-004A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-004C: Add or update database migrations: End-to-End Workflow Completion Testing

- Status: TODO
- Dependencies: GAP-004B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-004D: Add or update backend models: End-to-End Workflow Completion Testing

- Status: TODO
- Dependencies: GAP-004C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-004E: Add or update schemas: End-to-End Workflow Completion Testing

- Status: TODO
- Dependencies: GAP-004D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-004F: Add or update services/business logic: End-to-End Workflow Completion Testing

- Status: TODO
- Dependencies: GAP-004E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-004G: Add or update API endpoints: End-to-End Workflow Completion Testing

- Status: TODO
- Dependencies: GAP-004F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-004H: Add or update frontend screens/components: End-to-End Workflow Completion Testing

- Status: TODO
- Dependencies: GAP-004G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-004I: Add or update permissions/roles: End-to-End Workflow Completion Testing

- Status: TODO
- Dependencies: GAP-004H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-004J: Add or update tests: End-to-End Workflow Completion Testing

- Status: TODO
- Dependencies: GAP-004I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-004K: Add or update documentation: End-to-End Workflow Completion Testing

- Status: TODO
- Dependencies: GAP-004J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-004L: Run checks and record result: End-to-End Workflow Completion Testing

- Status: TODO
- Dependencies: GAP-004K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-005: Production-Grade Frontend Parity With Backend

- Tier: Tier 1 - Critical Gaps
- Phase: Phase 2 - Critical ERP foundations
- Business priority: Critical
- Technical area: Frontend / API parity
- Files likely involved: `frontend/src/app/dashboard`, `frontend/src/components`, `backend/app/api/v1`, `docs/planning`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-005A: Audit current implementation: Production-Grade Frontend Parity With Backend

- Status: TODO
- Dependencies: GAP-004L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-005B: Design data model/schema: Production-Grade Frontend Parity With Backend

- Status: TODO
- Dependencies: GAP-005A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-005C: Add or update database migrations: Production-Grade Frontend Parity With Backend

- Status: TODO
- Dependencies: GAP-005B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-005D: Add or update backend models: Production-Grade Frontend Parity With Backend

- Status: TODO
- Dependencies: GAP-005C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-005E: Add or update schemas: Production-Grade Frontend Parity With Backend

- Status: TODO
- Dependencies: GAP-005D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-005F: Add or update services/business logic: Production-Grade Frontend Parity With Backend

- Status: TODO
- Dependencies: GAP-005E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-005G: Add or update API endpoints: Production-Grade Frontend Parity With Backend

- Status: TODO
- Dependencies: GAP-005F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-005H: Add or update frontend screens/components: Production-Grade Frontend Parity With Backend

- Status: TODO
- Dependencies: GAP-005G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-005I: Add or update permissions/roles: Production-Grade Frontend Parity With Backend

- Status: TODO
- Dependencies: GAP-005H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-005J: Add or update tests: Production-Grade Frontend Parity With Backend

- Status: TODO
- Dependencies: GAP-005I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-005K: Add or update documentation: Production-Grade Frontend Parity With Backend

- Status: TODO
- Dependencies: GAP-005J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-005L: Run checks and record result: Production-Grade Frontend Parity With Backend

- Status: TODO
- Dependencies: GAP-005K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-006: Real Integrations Instead of Stub/Placeholder Integrations

- Tier: Tier 1 - Critical Gaps
- Phase: Phase 2 - Critical ERP foundations
- Business priority: Critical
- Technical area: Integrations / AI / IoT
- Files likely involved: `backend/app/api/v1/endpoints`, `backend/app/services`, `frontend/src/app/dashboard`, `docs`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-006A: Audit current implementation: Real Integrations Instead of Stub/Placeholder Integrations

- Status: TODO
- Dependencies: GAP-005L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-006B: Design data model/schema: Real Integrations Instead of Stub/Placeholder Integrations

- Status: TODO
- Dependencies: GAP-006A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-006C: Add or update database migrations: Real Integrations Instead of Stub/Placeholder Integrations

- Status: TODO
- Dependencies: GAP-006B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-006D: Add or update backend models: Real Integrations Instead of Stub/Placeholder Integrations

- Status: TODO
- Dependencies: GAP-006C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-006E: Add or update schemas: Real Integrations Instead of Stub/Placeholder Integrations

- Status: TODO
- Dependencies: GAP-006D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-006F: Add or update services/business logic: Real Integrations Instead of Stub/Placeholder Integrations

- Status: TODO
- Dependencies: GAP-006E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-006G: Add or update API endpoints: Real Integrations Instead of Stub/Placeholder Integrations

- Status: TODO
- Dependencies: GAP-006F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-006H: Add or update frontend screens/components: Real Integrations Instead of Stub/Placeholder Integrations

- Status: TODO
- Dependencies: GAP-006G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-006I: Add or update permissions/roles: Real Integrations Instead of Stub/Placeholder Integrations

- Status: TODO
- Dependencies: GAP-006H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-006J: Add or update tests: Real Integrations Instead of Stub/Placeholder Integrations

- Status: TODO
- Dependencies: GAP-006I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-006K: Add or update documentation: Real Integrations Instead of Stub/Placeholder Integrations

- Status: TODO
- Dependencies: GAP-006J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-006L: Run checks and record result: Real Integrations Instead of Stub/Placeholder Integrations

- Status: TODO
- Dependencies: GAP-006K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-007: Advanced Manufacturing Capacity Planning / APS

- Tier: Tier 2 - High Importance
- Phase: Phase 3 - High-importance operational modules
- Business priority: High
- Technical area: Production Planning / APS
- Files likely involved: `backend/app/models`, `backend/app/api/v1/endpoints/production.py`, `frontend/src/app/dashboard/production`, `backend/tests`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-007A: Audit current implementation: Advanced Manufacturing Capacity Planning / APS

- Status: TODO
- Dependencies: GAP-006L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-007B: Design data model/schema: Advanced Manufacturing Capacity Planning / APS

- Status: TODO
- Dependencies: GAP-007A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-007C: Add or update database migrations: Advanced Manufacturing Capacity Planning / APS

- Status: TODO
- Dependencies: GAP-007B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-007D: Add or update backend models: Advanced Manufacturing Capacity Planning / APS

- Status: TODO
- Dependencies: GAP-007C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-007E: Add or update schemas: Advanced Manufacturing Capacity Planning / APS

- Status: TODO
- Dependencies: GAP-007D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-007F: Add or update services/business logic: Advanced Manufacturing Capacity Planning / APS

- Status: TODO
- Dependencies: GAP-007E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-007G: Add or update API endpoints: Advanced Manufacturing Capacity Planning / APS

- Status: TODO
- Dependencies: GAP-007F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-007H: Add or update frontend screens/components: Advanced Manufacturing Capacity Planning / APS

- Status: TODO
- Dependencies: GAP-007G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-007I: Add or update permissions/roles: Advanced Manufacturing Capacity Planning / APS

- Status: TODO
- Dependencies: GAP-007H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-007J: Add or update tests: Advanced Manufacturing Capacity Planning / APS

- Status: TODO
- Dependencies: GAP-007I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-007K: Add or update documentation: Advanced Manufacturing Capacity Planning / APS

- Status: TODO
- Dependencies: GAP-007J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-007L: Run checks and record result: Advanced Manufacturing Capacity Planning / APS

- Status: TODO
- Dependencies: GAP-007K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-008: Warehouse Management Depth

- Tier: Tier 2 - High Importance
- Phase: Phase 3 - High-importance operational modules
- Business priority: High
- Technical area: Inventory / WMS
- Files likely involved: `backend/app/api/v1/endpoints/warehouse.py`, `backend/app/models`, `frontend/src/app/dashboard/warehouse`, `backend/tests`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-008A: Audit current implementation: Warehouse Management Depth

- Status: TODO
- Dependencies: GAP-007L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-008B: Design data model/schema: Warehouse Management Depth

- Status: TODO
- Dependencies: GAP-008A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-008C: Add or update database migrations: Warehouse Management Depth

- Status: TODO
- Dependencies: GAP-008B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-008D: Add or update backend models: Warehouse Management Depth

- Status: TODO
- Dependencies: GAP-008C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-008E: Add or update schemas: Warehouse Management Depth

- Status: TODO
- Dependencies: GAP-008D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-008F: Add or update services/business logic: Warehouse Management Depth

- Status: TODO
- Dependencies: GAP-008E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-008G: Add or update API endpoints: Warehouse Management Depth

- Status: TODO
- Dependencies: GAP-008F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-008H: Add or update frontend screens/components: Warehouse Management Depth

- Status: TODO
- Dependencies: GAP-008G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-008I: Add or update permissions/roles: Warehouse Management Depth

- Status: TODO
- Dependencies: GAP-008H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-008J: Add or update tests: Warehouse Management Depth

- Status: TODO
- Dependencies: GAP-008I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-008K: Add or update documentation: Warehouse Management Depth

- Status: TODO
- Dependencies: GAP-008J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-008L: Run checks and record result: Warehouse Management Depth

- Status: TODO
- Dependencies: GAP-008K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-009: Procurement and Supplier Management Maturity

- Tier: Tier 2 - High Importance
- Phase: Phase 3 - High-importance operational modules
- Business priority: High
- Technical area: Procurement / Suppliers
- Files likely involved: `backend/app/api/v1/endpoints/procurement.py`, `frontend/src/app/dashboard/procurement`, `backend/tests`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-009A: Audit current implementation: Procurement and Supplier Management Maturity

- Status: TODO
- Dependencies: GAP-008L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-009B: Design data model/schema: Procurement and Supplier Management Maturity

- Status: TODO
- Dependencies: GAP-009A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-009C: Add or update database migrations: Procurement and Supplier Management Maturity

- Status: TODO
- Dependencies: GAP-009B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-009D: Add or update backend models: Procurement and Supplier Management Maturity

- Status: TODO
- Dependencies: GAP-009C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-009E: Add or update schemas: Procurement and Supplier Management Maturity

- Status: TODO
- Dependencies: GAP-009D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-009F: Add or update services/business logic: Procurement and Supplier Management Maturity

- Status: TODO
- Dependencies: GAP-009E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-009G: Add or update API endpoints: Procurement and Supplier Management Maturity

- Status: TODO
- Dependencies: GAP-009F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-009H: Add or update frontend screens/components: Procurement and Supplier Management Maturity

- Status: TODO
- Dependencies: GAP-009G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-009I: Add or update permissions/roles: Procurement and Supplier Management Maturity

- Status: TODO
- Dependencies: GAP-009H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-009J: Add or update tests: Procurement and Supplier Management Maturity

- Status: TODO
- Dependencies: GAP-009I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-009K: Add or update documentation: Procurement and Supplier Management Maturity

- Status: TODO
- Dependencies: GAP-009J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-009L: Run checks and record result: Procurement and Supplier Management Maturity

- Status: TODO
- Dependencies: GAP-009K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-010: CRM / Sales Pipeline Depth

- Tier: Tier 2 - High Importance
- Phase: Phase 3 - High-importance operational modules
- Business priority: High
- Technical area: CRM / Sales
- Files likely involved: `backend/app/api/v1/endpoints`, `frontend/src/app/dashboard/sales`, `frontend/src/app/dashboard/crm`, `backend/tests`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-010A: Audit current implementation: CRM / Sales Pipeline Depth

- Status: TODO
- Dependencies: GAP-009L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-010B: Design data model/schema: CRM / Sales Pipeline Depth

- Status: TODO
- Dependencies: GAP-010A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-010C: Add or update database migrations: CRM / Sales Pipeline Depth

- Status: TODO
- Dependencies: GAP-010B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-010D: Add or update backend models: CRM / Sales Pipeline Depth

- Status: TODO
- Dependencies: GAP-010C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-010E: Add or update schemas: CRM / Sales Pipeline Depth

- Status: TODO
- Dependencies: GAP-010D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-010F: Add or update services/business logic: CRM / Sales Pipeline Depth

- Status: TODO
- Dependencies: GAP-010E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-010G: Add or update API endpoints: CRM / Sales Pipeline Depth

- Status: TODO
- Dependencies: GAP-010F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-010H: Add or update frontend screens/components: CRM / Sales Pipeline Depth

- Status: TODO
- Dependencies: GAP-010G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-010I: Add or update permissions/roles: CRM / Sales Pipeline Depth

- Status: TODO
- Dependencies: GAP-010H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-010J: Add or update tests: CRM / Sales Pipeline Depth

- Status: TODO
- Dependencies: GAP-010I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-010K: Add or update documentation: CRM / Sales Pipeline Depth

- Status: TODO
- Dependencies: GAP-010J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-010L: Run checks and record result: CRM / Sales Pipeline Depth

- Status: TODO
- Dependencies: GAP-010K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-011: HRMS and Payroll Completeness

- Tier: Tier 2 - High Importance
- Phase: Phase 3 - High-importance operational modules
- Business priority: High
- Technical area: HR / Payroll
- Files likely involved: `backend/app/api/v1/endpoints/hr.py`, `frontend/src/app/dashboard/hr`, `backend/tests`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-011A: Audit current implementation: HRMS and Payroll Completeness

- Status: TODO
- Dependencies: GAP-010L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-011B: Design data model/schema: HRMS and Payroll Completeness

- Status: TODO
- Dependencies: GAP-011A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-011C: Add or update database migrations: HRMS and Payroll Completeness

- Status: TODO
- Dependencies: GAP-011B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-011D: Add or update backend models: HRMS and Payroll Completeness

- Status: TODO
- Dependencies: GAP-011C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-011E: Add or update schemas: HRMS and Payroll Completeness

- Status: TODO
- Dependencies: GAP-011D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-011F: Add or update services/business logic: HRMS and Payroll Completeness

- Status: TODO
- Dependencies: GAP-011E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-011G: Add or update API endpoints: HRMS and Payroll Completeness

- Status: TODO
- Dependencies: GAP-011F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-011H: Add or update frontend screens/components: HRMS and Payroll Completeness

- Status: TODO
- Dependencies: GAP-011G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-011I: Add or update permissions/roles: HRMS and Payroll Completeness

- Status: TODO
- Dependencies: GAP-011H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-011J: Add or update tests: HRMS and Payroll Completeness

- Status: TODO
- Dependencies: GAP-011I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-011K: Add or update documentation: HRMS and Payroll Completeness

- Status: TODO
- Dependencies: GAP-011J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-011L: Run checks and record result: HRMS and Payroll Completeness

- Status: TODO
- Dependencies: GAP-011K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-012: Document Management and Internal Knowledge System

- Tier: Tier 2 - High Importance
- Phase: Phase 3 - High-importance operational modules
- Business priority: High
- Technical area: Documents / Knowledge
- Files likely involved: `backend/app/api/v1/endpoints/documents.py`, `frontend/src/app/dashboard/documents`, `docs`, `backend/tests`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-012A: Audit current implementation: Document Management and Internal Knowledge System

- Status: TODO
- Dependencies: GAP-011L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-012B: Design data model/schema: Document Management and Internal Knowledge System

- Status: TODO
- Dependencies: GAP-012A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-012C: Add or update database migrations: Document Management and Internal Knowledge System

- Status: TODO
- Dependencies: GAP-012B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-012D: Add or update backend models: Document Management and Internal Knowledge System

- Status: TODO
- Dependencies: GAP-012C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-012E: Add or update schemas: Document Management and Internal Knowledge System

- Status: TODO
- Dependencies: GAP-012D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-012F: Add or update services/business logic: Document Management and Internal Knowledge System

- Status: TODO
- Dependencies: GAP-012E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-012G: Add or update API endpoints: Document Management and Internal Knowledge System

- Status: TODO
- Dependencies: GAP-012F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-012H: Add or update frontend screens/components: Document Management and Internal Knowledge System

- Status: TODO
- Dependencies: GAP-012G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-012I: Add or update permissions/roles: Document Management and Internal Knowledge System

- Status: TODO
- Dependencies: GAP-012H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-012J: Add or update tests: Document Management and Internal Knowledge System

- Status: TODO
- Dependencies: GAP-012I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-012K: Add or update documentation: Document Management and Internal Knowledge System

- Status: TODO
- Dependencies: GAP-012J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-012L: Run checks and record result: Document Management and Internal Knowledge System

- Status: TODO
- Dependencies: GAP-012K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-013: Custom Report Builder Depth

- Tier: Tier 3 - Medium Importance
- Phase: Phase 4 - UX/reporting/extensibility
- Business priority: Medium
- Technical area: Reporting / Analytics
- Files likely involved: `backend/app/api/v1/endpoints/reports.py`, `frontend/src/app/dashboard/reports`, `backend/tests`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-013A: Audit current implementation: Custom Report Builder Depth

- Status: TODO
- Dependencies: GAP-012L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-013B: Design data model/schema: Custom Report Builder Depth

- Status: TODO
- Dependencies: GAP-013A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-013C: Add or update database migrations: Custom Report Builder Depth

- Status: TODO
- Dependencies: GAP-013B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-013D: Add or update backend models: Custom Report Builder Depth

- Status: TODO
- Dependencies: GAP-013C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-013E: Add or update schemas: Custom Report Builder Depth

- Status: TODO
- Dependencies: GAP-013D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-013F: Add or update services/business logic: Custom Report Builder Depth

- Status: TODO
- Dependencies: GAP-013E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-013G: Add or update API endpoints: Custom Report Builder Depth

- Status: TODO
- Dependencies: GAP-013F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-013H: Add or update frontend screens/components: Custom Report Builder Depth

- Status: TODO
- Dependencies: GAP-013G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-013I: Add or update permissions/roles: Custom Report Builder Depth

- Status: TODO
- Dependencies: GAP-013H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-013J: Add or update tests: Custom Report Builder Depth

- Status: TODO
- Dependencies: GAP-013I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-013K: Add or update documentation: Custom Report Builder Depth

- Status: TODO
- Dependencies: GAP-013J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-013L: Run checks and record result: Custom Report Builder Depth

- Status: TODO
- Dependencies: GAP-013K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-014: Notification Center Completeness

- Tier: Tier 3 - Medium Importance
- Phase: Phase 4 - UX/reporting/extensibility
- Business priority: Medium
- Technical area: Notifications / Messaging
- Files likely involved: `backend/app/api/v1/endpoints/notifications.py`, `frontend/src/components`, `frontend/src/app/dashboard/notifications`, `backend/tests`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-014A: Audit current implementation: Notification Center Completeness

- Status: TODO
- Dependencies: GAP-013L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-014B: Design data model/schema: Notification Center Completeness

- Status: TODO
- Dependencies: GAP-014A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-014C: Add or update database migrations: Notification Center Completeness

- Status: TODO
- Dependencies: GAP-014B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-014D: Add or update backend models: Notification Center Completeness

- Status: TODO
- Dependencies: GAP-014C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-014E: Add or update schemas: Notification Center Completeness

- Status: TODO
- Dependencies: GAP-014D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-014F: Add or update services/business logic: Notification Center Completeness

- Status: TODO
- Dependencies: GAP-014E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-014G: Add or update API endpoints: Notification Center Completeness

- Status: TODO
- Dependencies: GAP-014F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-014H: Add or update frontend screens/components: Notification Center Completeness

- Status: TODO
- Dependencies: GAP-014G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-014I: Add or update permissions/roles: Notification Center Completeness

- Status: TODO
- Dependencies: GAP-014H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-014J: Add or update tests: Notification Center Completeness

- Status: TODO
- Dependencies: GAP-014I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-014K: Add or update documentation: Notification Center Completeness

- Status: TODO
- Dependencies: GAP-014J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-014L: Run checks and record result: Notification Center Completeness

- Status: TODO
- Dependencies: GAP-014K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-015: UI/UX Navigation and Sidebar Information Architecture

- Tier: Tier 3 - Medium Importance
- Phase: Phase 4 - UX/reporting/extensibility
- Business priority: Medium
- Technical area: Frontend Navigation / IA
- Files likely involved: `frontend/src/components/Sidebar.tsx`, `frontend/src/lib/modules.ts`, `backend/app/api/v1/endpoints/modules.py`, `backend/app/core/module_registry.py`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-015A: Audit current implementation: UI/UX Navigation and Sidebar Information Architecture

- Status: TODO
- Dependencies: GAP-014L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-015B: Design data model/schema: UI/UX Navigation and Sidebar Information Architecture

- Status: TODO
- Dependencies: GAP-015A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-015C: Add or update database migrations: UI/UX Navigation and Sidebar Information Architecture

- Status: TODO
- Dependencies: GAP-015B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-015D: Add or update backend models: UI/UX Navigation and Sidebar Information Architecture

- Status: TODO
- Dependencies: GAP-015C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-015E: Add or update schemas: UI/UX Navigation and Sidebar Information Architecture

- Status: TODO
- Dependencies: GAP-015D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-015F: Add or update services/business logic: UI/UX Navigation and Sidebar Information Architecture

- Status: TODO
- Dependencies: GAP-015E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-015G: Add or update API endpoints: UI/UX Navigation and Sidebar Information Architecture

- Status: TODO
- Dependencies: GAP-015F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-015H: Add or update frontend screens/components: UI/UX Navigation and Sidebar Information Architecture

- Status: TODO
- Dependencies: GAP-015G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-015I: Add or update permissions/roles: UI/UX Navigation and Sidebar Information Architecture

- Status: TODO
- Dependencies: GAP-015H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-015J: Add or update tests: UI/UX Navigation and Sidebar Information Architecture

- Status: TODO
- Dependencies: GAP-015I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-015K: Add or update documentation: UI/UX Navigation and Sidebar Information Architecture

- Status: TODO
- Dependencies: GAP-015J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-015L: Run checks and record result: UI/UX Navigation and Sidebar Information Architecture

- Status: TODO
- Dependencies: GAP-015K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-016: API Documentation and Developer Portal Maturity

- Tier: Tier 3 - Medium Importance
- Phase: Phase 4 - UX/reporting/extensibility
- Business priority: Medium
- Technical area: API Docs / Developer Portal
- Files likely involved: `backend/app/main.py`, `backend/app/api/v1`, `docs`, `frontend/src/app/dashboard/developer`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-016A: Audit current implementation: API Documentation and Developer Portal Maturity

- Status: TODO
- Dependencies: GAP-015L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-016B: Design data model/schema: API Documentation and Developer Portal Maturity

- Status: TODO
- Dependencies: GAP-016A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-016C: Add or update database migrations: API Documentation and Developer Portal Maturity

- Status: TODO
- Dependencies: GAP-016B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-016D: Add or update backend models: API Documentation and Developer Portal Maturity

- Status: TODO
- Dependencies: GAP-016C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-016E: Add or update schemas: API Documentation and Developer Portal Maturity

- Status: TODO
- Dependencies: GAP-016D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-016F: Add or update services/business logic: API Documentation and Developer Portal Maturity

- Status: TODO
- Dependencies: GAP-016E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-016G: Add or update API endpoints: API Documentation and Developer Portal Maturity

- Status: TODO
- Dependencies: GAP-016F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-016H: Add or update frontend screens/components: API Documentation and Developer Portal Maturity

- Status: TODO
- Dependencies: GAP-016G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-016I: Add or update permissions/roles: API Documentation and Developer Portal Maturity

- Status: TODO
- Dependencies: GAP-016H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-016J: Add or update tests: API Documentation and Developer Portal Maturity

- Status: TODO
- Dependencies: GAP-016I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-016K: Add or update documentation: API Documentation and Developer Portal Maturity

- Status: TODO
- Dependencies: GAP-016J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-016L: Run checks and record result: API Documentation and Developer Portal Maturity

- Status: TODO
- Dependencies: GAP-016K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-017: HACCP Audit-Grade Workflow Completion

- Tier: Tier 4 - FMCG-Specific & Regulatory
- Phase: Phase 5 - FMCG/regulatory polish
- Business priority: High
- Technical area: QMS / HACCP
- Files likely involved: `backend/app/api/v1/endpoints/qms.py`, `frontend/src/app/dashboard/quality`, `docs`, `backend/tests`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-017A: Audit current implementation: HACCP Audit-Grade Workflow Completion

- Status: TODO
- Dependencies: GAP-016L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-017B: Design data model/schema: HACCP Audit-Grade Workflow Completion

- Status: TODO
- Dependencies: GAP-017A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-017C: Add or update database migrations: HACCP Audit-Grade Workflow Completion

- Status: TODO
- Dependencies: GAP-017B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-017D: Add or update backend models: HACCP Audit-Grade Workflow Completion

- Status: TODO
- Dependencies: GAP-017C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-017E: Add or update schemas: HACCP Audit-Grade Workflow Completion

- Status: TODO
- Dependencies: GAP-017D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-017F: Add or update services/business logic: HACCP Audit-Grade Workflow Completion

- Status: TODO
- Dependencies: GAP-017E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-017G: Add or update API endpoints: HACCP Audit-Grade Workflow Completion

- Status: TODO
- Dependencies: GAP-017F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-017H: Add or update frontend screens/components: HACCP Audit-Grade Workflow Completion

- Status: TODO
- Dependencies: GAP-017G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-017I: Add or update permissions/roles: HACCP Audit-Grade Workflow Completion

- Status: TODO
- Dependencies: GAP-017H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-017J: Add or update tests: HACCP Audit-Grade Workflow Completion

- Status: TODO
- Dependencies: GAP-017I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-017K: Add or update documentation: HACCP Audit-Grade Workflow Completion

- Status: TODO
- Dependencies: GAP-017J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-017L: Run checks and record result: HACCP Audit-Grade Workflow Completion

- Status: TODO
- Dependencies: GAP-017K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-018: GS1 / Label Printing / Packaging Compliance

- Tier: Tier 4 - FMCG-Specific & Regulatory
- Phase: Phase 5 - FMCG/regulatory polish
- Business priority: High
- Technical area: GS1 / Labels / Packaging
- Files likely involved: `backend/app/api/v1/endpoints/gs1.py`, `frontend/src/app/dashboard/gs1`, `backend/tests`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-018A: Audit current implementation: GS1 / Label Printing / Packaging Compliance

- Status: TODO
- Dependencies: GAP-017L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-018B: Design data model/schema: GS1 / Label Printing / Packaging Compliance

- Status: TODO
- Dependencies: GAP-018A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-018C: Add or update database migrations: GS1 / Label Printing / Packaging Compliance

- Status: TODO
- Dependencies: GAP-018B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-018D: Add or update backend models: GS1 / Label Printing / Packaging Compliance

- Status: TODO
- Dependencies: GAP-018C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-018E: Add or update schemas: GS1 / Label Printing / Packaging Compliance

- Status: TODO
- Dependencies: GAP-018D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-018F: Add or update services/business logic: GS1 / Label Printing / Packaging Compliance

- Status: TODO
- Dependencies: GAP-018E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-018G: Add or update API endpoints: GS1 / Label Printing / Packaging Compliance

- Status: TODO
- Dependencies: GAP-018F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-018H: Add or update frontend screens/components: GS1 / Label Printing / Packaging Compliance

- Status: TODO
- Dependencies: GAP-018G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-018I: Add or update permissions/roles: GS1 / Label Printing / Packaging Compliance

- Status: TODO
- Dependencies: GAP-018H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-018J: Add or update tests: GS1 / Label Printing / Packaging Compliance

- Status: TODO
- Dependencies: GAP-018I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-018K: Add or update documentation: GS1 / Label Printing / Packaging Compliance

- Status: TODO
- Dependencies: GAP-018J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-018L: Run checks and record result: GS1 / Label Printing / Packaging Compliance

- Status: TODO
- Dependencies: GAP-018K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-019: Shelf-Life / FEFO / Expiry Control

- Tier: Tier 4 - FMCG-Specific & Regulatory
- Phase: Phase 5 - FMCG/regulatory polish
- Business priority: High
- Technical area: Inventory / Traceability
- Files likely involved: `backend/app/api/v1/endpoints/shelf_life.py`, `frontend/src/app/dashboard/inventory`, `backend/tests`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-019A: Audit current implementation: Shelf-Life / FEFO / Expiry Control

- Status: TODO
- Dependencies: GAP-018L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-019B: Design data model/schema: Shelf-Life / FEFO / Expiry Control

- Status: TODO
- Dependencies: GAP-019A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-019C: Add or update database migrations: Shelf-Life / FEFO / Expiry Control

- Status: TODO
- Dependencies: GAP-019B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-019D: Add or update backend models: Shelf-Life / FEFO / Expiry Control

- Status: TODO
- Dependencies: GAP-019C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-019E: Add or update schemas: Shelf-Life / FEFO / Expiry Control

- Status: TODO
- Dependencies: GAP-019D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-019F: Add or update services/business logic: Shelf-Life / FEFO / Expiry Control

- Status: TODO
- Dependencies: GAP-019E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-019G: Add or update API endpoints: Shelf-Life / FEFO / Expiry Control

- Status: TODO
- Dependencies: GAP-019F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-019H: Add or update frontend screens/components: Shelf-Life / FEFO / Expiry Control

- Status: TODO
- Dependencies: GAP-019G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-019I: Add or update permissions/roles: Shelf-Life / FEFO / Expiry Control

- Status: TODO
- Dependencies: GAP-019H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-019J: Add or update tests: Shelf-Life / FEFO / Expiry Control

- Status: TODO
- Dependencies: GAP-019I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-019K: Add or update documentation: Shelf-Life / FEFO / Expiry Control

- Status: TODO
- Dependencies: GAP-019J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-019L: Run checks and record result: Shelf-Life / FEFO / Expiry Control

- Status: TODO
- Dependencies: GAP-019K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-020: Consumer Complaint and Recall Linkage

- Tier: Tier 4 - FMCG-Specific & Regulatory
- Phase: Phase 5 - FMCG/regulatory polish
- Business priority: High
- Technical area: Quality / Recall / Customer Care
- Files likely involved: `backend/app/api/v1/endpoints/consumer_complaints.py`, `backend/app/api/v1/endpoints/recall.py`, `frontend/src/app/dashboard`, `backend/tests`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-020A: Audit current implementation: Consumer Complaint and Recall Linkage

- Status: TODO
- Dependencies: GAP-019L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-020B: Design data model/schema: Consumer Complaint and Recall Linkage

- Status: TODO
- Dependencies: GAP-020A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-020C: Add or update database migrations: Consumer Complaint and Recall Linkage

- Status: TODO
- Dependencies: GAP-020B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-020D: Add or update backend models: Consumer Complaint and Recall Linkage

- Status: TODO
- Dependencies: GAP-020C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-020E: Add or update schemas: Consumer Complaint and Recall Linkage

- Status: TODO
- Dependencies: GAP-020D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-020F: Add or update services/business logic: Consumer Complaint and Recall Linkage

- Status: TODO
- Dependencies: GAP-020E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-020G: Add or update API endpoints: Consumer Complaint and Recall Linkage

- Status: TODO
- Dependencies: GAP-020F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-020H: Add or update frontend screens/components: Consumer Complaint and Recall Linkage

- Status: TODO
- Dependencies: GAP-020G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-020I: Add or update permissions/roles: Consumer Complaint and Recall Linkage

- Status: TODO
- Dependencies: GAP-020H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-020J: Add or update tests: Consumer Complaint and Recall Linkage

- Status: TODO
- Dependencies: GAP-020I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-020K: Add or update documentation: Consumer Complaint and Recall Linkage

- Status: TODO
- Dependencies: GAP-020J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-020L: Run checks and record result: Consumer Complaint and Recall Linkage

- Status: TODO
- Dependencies: GAP-020K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-021: New Product Development / Formula Governance

- Tier: Tier 4 - FMCG-Specific & Regulatory
- Phase: Phase 5 - FMCG/regulatory polish
- Business priority: High
- Technical area: NPD / Formulation / Governance
- Files likely involved: `backend/app/api/v1/endpoints/npd.py`, `frontend/src/app/dashboard/npd`, `frontend/src/app/dashboard/ai/formulations`, `backend/tests`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-021A: Audit current implementation: New Product Development / Formula Governance

- Status: TODO
- Dependencies: GAP-020L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-021B: Design data model/schema: New Product Development / Formula Governance

- Status: TODO
- Dependencies: GAP-021A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-021C: Add or update database migrations: New Product Development / Formula Governance

- Status: TODO
- Dependencies: GAP-021B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-021D: Add or update backend models: New Product Development / Formula Governance

- Status: TODO
- Dependencies: GAP-021C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-021E: Add or update schemas: New Product Development / Formula Governance

- Status: TODO
- Dependencies: GAP-021D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-021F: Add or update services/business logic: New Product Development / Formula Governance

- Status: TODO
- Dependencies: GAP-021E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-021G: Add or update API endpoints: New Product Development / Formula Governance

- Status: TODO
- Dependencies: GAP-021F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-021H: Add or update frontend screens/components: New Product Development / Formula Governance

- Status: TODO
- Dependencies: GAP-021G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-021I: Add or update permissions/roles: New Product Development / Formula Governance

- Status: TODO
- Dependencies: GAP-021H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-021J: Add or update tests: New Product Development / Formula Governance

- Status: TODO
- Dependencies: GAP-021I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-021K: Add or update documentation: New Product Development / Formula Governance

- Status: TODO
- Dependencies: GAP-021J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-021L: Run checks and record result: New Product Development / Formula Governance

- Status: TODO
- Dependencies: GAP-021K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-022: True IoT / Machine Streaming

- Tier: Tier 5 - Advanced / Future Roadmap
- Phase: Phase 6 - Advanced/future roadmap
- Business priority: Future
- Technical area: IoT / Streaming / Utilities
- Files likely involved: `backend/app/api/v1/endpoints/iot.py`, `frontend/src/app/dashboard/iot`, `backend/tests`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-022A: Audit current implementation: True IoT / Machine Streaming

- Status: TODO
- Dependencies: GAP-021L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-022B: Design data model/schema: True IoT / Machine Streaming

- Status: TODO
- Dependencies: GAP-022A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-022C: Add or update database migrations: True IoT / Machine Streaming

- Status: TODO
- Dependencies: GAP-022B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-022D: Add or update backend models: True IoT / Machine Streaming

- Status: TODO
- Dependencies: GAP-022C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-022E: Add or update schemas: True IoT / Machine Streaming

- Status: TODO
- Dependencies: GAP-022D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-022F: Add or update services/business logic: True IoT / Machine Streaming

- Status: TODO
- Dependencies: GAP-022E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-022G: Add or update API endpoints: True IoT / Machine Streaming

- Status: TODO
- Dependencies: GAP-022F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-022H: Add or update frontend screens/components: True IoT / Machine Streaming

- Status: TODO
- Dependencies: GAP-022G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-022I: Add or update permissions/roles: True IoT / Machine Streaming

- Status: TODO
- Dependencies: GAP-022H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-022J: Add or update tests: True IoT / Machine Streaming

- Status: TODO
- Dependencies: GAP-022I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-022K: Add or update documentation: True IoT / Machine Streaming

- Status: TODO
- Dependencies: GAP-022J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-022L: Run checks and record result: True IoT / Machine Streaming

- Status: TODO
- Dependencies: GAP-022K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-023: ML-Based Predictive Maintenance

- Tier: Tier 5 - Advanced / Future Roadmap
- Phase: Phase 6 - Advanced/future roadmap
- Business priority: Future
- Technical area: Maintenance / ML
- Files likely involved: `backend/app/api/v1/endpoints/maintenance.py`, `backend/app/services`, `frontend/src/app/dashboard/maintenance`, `backend/tests`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-023A: Audit current implementation: ML-Based Predictive Maintenance

- Status: TODO
- Dependencies: GAP-022L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-023B: Design data model/schema: ML-Based Predictive Maintenance

- Status: TODO
- Dependencies: GAP-023A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-023C: Add or update database migrations: ML-Based Predictive Maintenance

- Status: TODO
- Dependencies: GAP-023B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-023D: Add or update backend models: ML-Based Predictive Maintenance

- Status: TODO
- Dependencies: GAP-023C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-023E: Add or update schemas: ML-Based Predictive Maintenance

- Status: TODO
- Dependencies: GAP-023D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-023F: Add or update services/business logic: ML-Based Predictive Maintenance

- Status: TODO
- Dependencies: GAP-023E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-023G: Add or update API endpoints: ML-Based Predictive Maintenance

- Status: TODO
- Dependencies: GAP-023F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-023H: Add or update frontend screens/components: ML-Based Predictive Maintenance

- Status: TODO
- Dependencies: GAP-023G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-023I: Add or update permissions/roles: ML-Based Predictive Maintenance

- Status: TODO
- Dependencies: GAP-023H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-023J: Add or update tests: ML-Based Predictive Maintenance

- Status: TODO
- Dependencies: GAP-023I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-023K: Add or update documentation: ML-Based Predictive Maintenance

- Status: TODO
- Dependencies: GAP-023J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-023L: Run checks and record result: ML-Based Predictive Maintenance

- Status: TODO
- Dependencies: GAP-023K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-024: AI Agent Governance and Prompt Registry

- Tier: Tier 5 - Advanced / Future Roadmap
- Phase: Phase 6 - Advanced/future roadmap
- Business priority: Future
- Technical area: AI Governance
- Files likely involved: `backend/app/ai`, `backend/app/api/v1/endpoints/ai.py`, `frontend/src/app/dashboard/ai`, `backend/tests`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-024A: Audit current implementation: AI Agent Governance and Prompt Registry

- Status: TODO
- Dependencies: GAP-023L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-024B: Design data model/schema: AI Agent Governance and Prompt Registry

- Status: TODO
- Dependencies: GAP-024A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-024C: Add or update database migrations: AI Agent Governance and Prompt Registry

- Status: TODO
- Dependencies: GAP-024B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-024D: Add or update backend models: AI Agent Governance and Prompt Registry

- Status: TODO
- Dependencies: GAP-024C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-024E: Add or update schemas: AI Agent Governance and Prompt Registry

- Status: TODO
- Dependencies: GAP-024D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-024F: Add or update services/business logic: AI Agent Governance and Prompt Registry

- Status: TODO
- Dependencies: GAP-024E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-024G: Add or update API endpoints: AI Agent Governance and Prompt Registry

- Status: TODO
- Dependencies: GAP-024F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-024H: Add or update frontend screens/components: AI Agent Governance and Prompt Registry

- Status: TODO
- Dependencies: GAP-024G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-024I: Add or update permissions/roles: AI Agent Governance and Prompt Registry

- Status: TODO
- Dependencies: GAP-024H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-024J: Add or update tests: AI Agent Governance and Prompt Registry

- Status: TODO
- Dependencies: GAP-024I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-024K: Add or update documentation: AI Agent Governance and Prompt Registry

- Status: TODO
- Dependencies: GAP-024J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-024L: Run checks and record result: AI Agent Governance and Prompt Registry

- Status: TODO
- Dependencies: GAP-024K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-025: Multi-Company / Multi-Branch / Franchise Scaling

- Tier: Tier 5 - Advanced / Future Roadmap
- Phase: Phase 6 - Advanced/future roadmap
- Business priority: Future
- Technical area: Multi-company / Branches
- Files likely involved: `backend/app/api/v1/endpoints/companies.py`, `frontend/src/app/dashboard/admin`, `backend/tests`

Requirements from planning document:
- Audit current implementation and derive exact missing requirements from the planning document and codebase.

Implementation subtasks:

#### GAP-025A: Audit current implementation: Multi-Company / Multi-Branch / Franchise Scaling

- Status: TODO
- Dependencies: GAP-024L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-025B: Design data model/schema: Multi-Company / Multi-Branch / Franchise Scaling

- Status: TODO
- Dependencies: GAP-025A
- Acceptance criteria: Define schema/model changes only if needed and review existing models first.
- Test requirements: Schema design notes reviewed against current ORM conventions.
- Documentation requirements: Document model decisions and migration needs.

#### GAP-025C: Add or update database migrations: Multi-Company / Multi-Branch / Franchise Scaling

- Status: TODO
- Dependencies: GAP-025B
- Acceptance criteria: Create Alembic migrations only for required schema changes.
- Test requirements: Migration applies on empty and existing dev DB without destructive data loss.
- Documentation requirements: Record migration command and result.

#### GAP-025D: Add or update backend models: Multi-Company / Multi-Branch / Franchise Scaling

- Status: TODO
- Dependencies: GAP-025C
- Acceptance criteria: Implement ORM/model changes following existing conventions.
- Test requirements: Models import successfully and relationships/enums are consistent.
- Documentation requirements: Document model paths.

#### GAP-025E: Add or update schemas: Multi-Company / Multi-Branch / Franchise Scaling

- Status: TODO
- Dependencies: GAP-025D
- Acceptance criteria: Implement request/response schemas and validation.
- Test requirements: Schemas validate required fields, enums, ranges, references, and nullability.
- Documentation requirements: Document API schema behavior.

#### GAP-025F: Add or update services/business logic: Multi-Company / Multi-Branch / Franchise Scaling

- Status: TODO
- Dependencies: GAP-025E
- Acceptance criteria: Implement service-layer or existing-pattern business logic.
- Test requirements: Business rules are testable and preserve existing workflows.
- Documentation requirements: Document business rules.

#### GAP-025G: Add or update API endpoints: Multi-Company / Multi-Branch / Franchise Scaling

- Status: TODO
- Dependencies: GAP-025F
- Acceptance criteria: Expose endpoints with auth, permissions, validation, and error handling.
- Test requirements: Endpoints satisfy acceptance criteria and reject unauthorized access.
- Documentation requirements: Document endpoints and permissions.

#### GAP-025H: Add or update frontend screens/components: Multi-Company / Multi-Branch / Franchise Scaling

- Status: TODO
- Dependencies: GAP-025G
- Acceptance criteria: Build UI using existing layout, table, form, modal, and dashboard patterns.
- Test requirements: UI supports expected workflows, loading/empty/error states, and role visibility.
- Documentation requirements: Document frontend paths and user behavior.

#### GAP-025I: Add or update permissions/roles: Multi-Company / Multi-Branch / Franchise Scaling

- Status: TODO
- Dependencies: GAP-025H
- Acceptance criteria: Register permissions and update role templates/UI visibility as required.
- Test requirements: Dangerous actions require explicit permission and high-risk approval where needed.
- Documentation requirements: Document role matrix changes.

#### GAP-025J: Add or update tests: Multi-Company / Multi-Branch / Franchise Scaling

- Status: TODO
- Dependencies: GAP-025I
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-025K: Add or update documentation: Multi-Company / Multi-Branch / Franchise Scaling

- Status: TODO
- Dependencies: GAP-025J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-025L: Run checks and record result: Multi-Company / Multi-Branch / Franchise Scaling

- Status: TODO
- Dependencies: GAP-025K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-026: Manual Audit / Repo Analysis

- Tier: Manual Workflow
- Phase: Phase 1 - Documentation manual workflow
- Business priority: Critical
- Technical area: Documentation / Audit
- Files likely involved: `docs/user-manual/MANUAL_AUDIT.md`, `frontend/src`, `backend/app`

Requirements from planning document:
- Create docs/user-manual/MANUAL_AUDIT.md before writing the final manual.
- Inventory frontend routes, sidebar/menu items, visible buttons/actions, forms, tables, filters, modals, dashboards, and related file paths.
- Inventory backend routers, endpoints, schemas, models, services, permissions, auth dependencies, statuses, and mock/stub logic.
- Create module completeness, button/action, workflow/status, role/permission, and mock/stub/dev-only inventories.
- Update TASKS.md with manual audit completion and next screenshot task.

Implementation subtasks:

#### GAP-026A: Audit current implementation: Manual Audit / Repo Analysis

- Status: TODO
- Dependencies: PHASE0-002
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-026J: Add or update tests: Manual Audit / Repo Analysis

- Status: TODO
- Dependencies: GAP-026A
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-026K: Add or update documentation: Manual Audit / Repo Analysis

- Status: TODO
- Dependencies: GAP-026J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-026L: Run checks and record result: Manual Audit / Repo Analysis

- Status: TODO
- Dependencies: GAP-026K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-027: Screenshot Automation / Playwright Capture

- Tier: Manual Workflow
- Phase: Phase 1 - Documentation manual workflow
- Business priority: Critical
- Technical area: Documentation / Screenshot Tooling
- Files likely involved: `docs/user-manual/screenshots`, `frontend/scripts`, `frontend/package.json`

Requirements from planning document:
- Create Playwright screenshot crawler that logs in using MANUAL_TEST_BASE_URL, MANUAL_TEST_USERNAME, and MANUAL_TEST_PASSWORD.
- Create docs/user-manual/screenshots, README.md, routes.json, and screenshots-index.json.
- Discover routes from frontend code and MANUAL_AUDIT.md where possible.
- Capture full-page screenshots safely without creating, editing, deleting, approving, sending, or changing business data.
- Extract visible action labels and record capture status/errors in screenshots-index.json.
- Add package script where appropriate and update TASKS.md.

Implementation subtasks:

#### GAP-027A: Audit current implementation: Screenshot Automation / Playwright Capture

- Status: TODO
- Dependencies: GAP-026L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-027J: Add or update tests: Screenshot Automation / Playwright Capture

- Status: TODO
- Dependencies: GAP-027A
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-027K: Add or update documentation: Screenshot Automation / Playwright Capture

- Status: TODO
- Dependencies: GAP-027J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-027L: Run checks and record result: Screenshot Automation / Playwright Capture

- Status: TODO
- Dependencies: GAP-027K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.

### GAP-028: Full User Manual Generation

- Tier: Manual Workflow
- Phase: Phase 1 - Documentation manual workflow
- Business priority: Critical
- Technical area: Documentation / User Manual
- Files likely involved: `docs/user-manual`, `docs/user-manual/MANUAL_AUDIT.md`, `docs/user-manual/screenshots/screenshots-index.json`

Requirements from planning document:
- Generate docs/user-manual INDEX and chapter files 00 through 24 based on code, MANUAL_AUDIT.md, screenshots-index.json, routes.json, and existing docs.
- Use the required module chapter structure: purpose, users, navigation, screen overview, fields, actions, steps, scenarios, statuses, related modules, permissions, mistakes, troubleshooting, admin notes, implementation notes.
- Clearly mark missing, partial, mock/stub, or not discoverable features; do not invent features.
- Reference only captured screenshots from screenshots-index.json.
- Create troubleshooting, glossary, and admin technical appendix chapters.
- Update TASKS.md with full manual generation completion and review next steps.

Implementation subtasks:

#### GAP-028A: Audit current implementation: Full User Manual Generation

- Status: TODO
- Dependencies: GAP-027L
- Acceptance criteria: Record what exists, what is partial, and what is missing for this gap.
- Test requirements: No business logic changes; documentation-only audit accepted.
- Documentation requirements: Document audit findings and update status matrix.

#### GAP-028J: Add or update tests: Full User Manual Generation

- Status: TODO
- Dependencies: GAP-028A
- Acceptance criteria: Add focused backend/frontend tests for the implemented behavior.
- Test requirements: Relevant tests fail before fix when practical and pass after implementation.
- Documentation requirements: Document test files and commands.

#### GAP-028K: Add or update documentation: Full User Manual Generation

- Status: TODO
- Dependencies: GAP-028J
- Acceptance criteria: Update user/admin/developer docs for this change.
- Test requirements: Docs match actual behavior and do not claim incomplete features are done.
- Documentation requirements: Documentation updated.

#### GAP-028L: Run checks and record result: Full User Manual Generation

- Status: TODO
- Dependencies: GAP-028K
- Acceptance criteria: Run relevant compile, lint, type, test, migration, or smoke checks.
- Test requirements: Checks pass or failures are recorded with BLOCKED/NEEDS_USER_REVIEW.
- Documentation requirements: Record commands/results in CODEX_PROGRESS.md.
