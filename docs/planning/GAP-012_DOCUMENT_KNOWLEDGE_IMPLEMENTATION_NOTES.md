# GAP-012 Document Management / Knowledge System Implementation Notes

## Summary

GAP-012 hardened the three document-adjacent modules already present in the codebase — Document Management, Knowledge Base, and Electronic Signatures — by adding governance fields, scope ownership, dedicated service layers, tightened API permissions, frontend permission guards, and a reconciliation migration. No tables were created from scratch; the migration is purely additive.

---

## Implemented Scope

| Sub-area | What was done |
|---|---|
| Document management | Added governance/scope/versioning/file-lock fields, `document_access_service.py`, endpoint permission guards using `require_permission` |
| Knowledge Base | Added scope/authoring/publication fields, `knowledge_base_service.py`, dedicated `require_permission` on all KB routes, revision tracking model |
| E-signature | Added evidence/audit fields, `esignature_service.py`, eligibility checks (signer, expiry, status) per signing action |
| Module registry | Promoted all three to `MODULE_DEFINITIONS`; removed any loose `ENDPOINT_ROUTE_DEFINITIONS` entries for these modules |
| Frontend | Updated nav permission keys; KB pages use `knowledge_base.*` permissions; e-sign page uses `apiClient` (no bare `fetch`) |

---

## Migration

**File:** `backend/alembic/versions/20260515_0030_document_knowledge_reconciliation.py`

- **Revision:** `20260515_0030`
- **Parent:** `20260515_0020` (HRMS/Payroll reconciliation)
- **Strategy:** Fully additive reconciliation. Uses `_has_table` / `_has_column` / `_add_column_once` guards so it is safe to run against a DB that already has some columns.
- **What it adds:** Governance/scope columns on `documents` (file lock, scan status, retention, legal hold, confidentiality level, lineage, checksum, scope FKs), `kb_articles` (scope fields, publication/revision tracking), `signature_requests` (evidence hashes, completion timestamps, cancellation FK, audit_request_id, evidence_summary JSONB), and `signature_records` (evidence hash, auth method, signed document version/id).
- **Live DB migration:** Skipped in the GAP-012 session because Docker daemon was unavailable (`dockerDesktopLinuxEngine` pipe not found). Alembic offline SQL generation passed. Live migration must be run when Docker is available:
  ```
  docker compose --env-file .env.development exec -T backend python -m alembic upgrade head
  ```

---

## Backend Models

### `backend/app/models/documents.py`

| Model | Key additions |
|---|---|
| `Document` | `lineage_id`, `document_no`, `document_type`, `version`, `revision_note`, `previous_version_id`, `is_latest` — version chain fields |
| | `effective_date`, `expiry_date`, `approved_at`, `obsolete_at`, `archived_at` — lifecycle timestamps |
| | `owner_user_id`, `approved_by_id`, `created_by_id`, `updated_by_id`, `next_review_owner_id` — accountability FKs |
| | `company_id`, `branch_id`, `department_id`, `factory_id`, `product_category_id`, `supplier_id`, `customer_id` — scope hint columns |
| | `confidentiality_level` (default `INTERNAL`), `retention_until`, `legal_hold`, `review_due_date` — governance fields |
| | `related_entity_type`, `related_entity_id` — soft polymorphic ERP entity link |
| | `file_url`, `file_name`, `file_size_bytes`, `mime_type`, `storage_provider`, `storage_key`, `file_checksum_sha256`, `file_scan_status`, `file_scan_result`, `file_locked`, `locked_at`, `locked_by_id` — storage abstraction and file lock |
| `DocumentTag` | Freeform tag records linked to a document |
| `DocumentCategory` | Enum covering SOP, QC, customs, invoices, HR, marketing categories, and more |
| `DocumentStatus` | `DRAFT → APPROVED → OBSOLETE → ARCHIVED` |

### `backend/app/models/knowledge_base.py`

| Model | Key fields |
|---|---|
| `KBCategory` | `slug`, `name`, `parent_id` (self-referential), `display_order`, `is_active`, `icon` |
| `KBArticle` | `slug`, `title`, `content_md`, `status` (DRAFT/PUBLISHED/ARCHIVED), `version`, `author_id`, `last_editor_id`, `published_by_id`, `archived_by_id`, `published_at`, `archived_at` |
| | `is_internal_only`, `access_level`, `is_featured`, `view_count`, `review_due_date` |
| | `company_id`, `department_id`, `factory_id`, `module_key`, `access_scope_type`, `access_scope_id` — scope fields |
| `KBArticleRevision` | `article_id`, `version_no`, `title`, `content_md`, `change_summary`, `changed_by_id` — full revision history |

### `backend/app/models/esign.py`

| Model | Key fields |
|---|---|
| `SignatureRequest` | `request_no`, `document_id` (FK to documents), `document_type`, `document_ref`, `requester_id`, `subject`, `message`, `status`, `expires_at` |
| | `required_count`, `signed_count`, `declined_count` — progress counters |
| | `company_id`, `branch_id`, `department_id`, `factory_id`, `module_key`, `related_entity_type`, `related_entity_id` — scope/ERP link |
| | `document_hash_sha256`, `payload_hash_sha256` — pre-signing evidence |
| | `completed_at`, `expired_at`, `cancelled_at`, `cancelled_by_id`, `evidence_summary` (JSON), `audit_request_id` — lifecycle and evidence |
| `SignatureRecord` | `request_id`, `signer_id`, `status`, `signed_at`, `declined_at`, `ip_address`, `user_agent`, `signature_data` |
| | `signed_payload_hash_sha256`, `decline_reason`, `evidence_hash_sha256`, `auth_method`, `signed_document_version`, `signed_document_id` — per-signer evidence |

---

## Backend Schemas

### `backend/app/schemas/documents.py`

- `DocumentCreate` — full field set including `previous_version_id` for version chaining.
- `DocumentUpdate` — all mutable fields optional.
- `DocumentApprove` — accepts `effective_date` and `expiry_date`.
- `DocumentRead` — full record including version, lock, and audit timestamps.
- `DocumentShort` — lightweight list view (title, category, version, status, expiry, file_name).
- `DocumentVersionHistory` — version, status, is_latest, revision_note for history lists.

### `backend/app/schemas/knowledge_base.py`

- `KBCategoryCreate` / `KBCategoryUpdate` / `KBCategoryRead` — category CRUD with parent_id and icon.
- `KBArticleCreate` — full article fields including scope and access level.
- `KBArticleUpdate` — all mutable fields optional; includes `change_summary` for revision tracking.
- `KBArticleRead` — includes publication/archival timestamps, view_count, and author IDs.
- `KBArticleRevisionRead` — revision history read model.

### `backend/app/schemas/esign.py`

- `SignatureRequestCreate` — `document_type`, `document_ref`, `subject`, `signer_ids`, optional scope fields and evidence hashes.
- `SignatureRequestRead` — full request including progress counters, evidence fields, and nested `signature_records`.
- `SignatureRequestDetail` — extends Read with full `signature_data` in records.
- `SignAction` — `signature_data`, optional `signed_payload_hash_sha256`, `auth_method`.
- `DeclineAction` — optional `reason`.
- `ESignDashboard` — aggregated stats: total, pending, signed, declined, expired, my_pending_signatures.

---

## Backend Services

### `backend/app/services/document_access_service.py`

Responsibilities:
- `DOCUMENT_ACTION_STATUSES` — defines which statuses allow each action (e.g., edit only in DRAFT; approve only in DRAFT; archive in APPROVED or OBSOLETE).
- `document_is_locked()` — true if `file_locked` or `legal_hold` is set; blocks edit/delete.
- `can_view_document()` — delegates to `can_view_record()`.
- `can_modify_document()` — superuser bypass, lock check, status check, permission check (including approve implies archive/obsolete), fallback to scope record check.
- `build_document_access_hint()` — returns structured dict with `can_view`, `view_only`, `can_edit`, `can_approve`, `can_archive`, `can_obsolete`, `can_new_version`, `can_export`, `can_delete`, and optional `reason`.
- `ensure_document_action_allowed()` — raises HTTP 403 if action not allowed, then returns hint.

### `backend/app/services/knowledge_base_service.py`

Responsibilities:
- `KB_ACTION_STATUSES` — edit allowed in DRAFT/PUBLISHED; publish only in DRAFT; archive in DRAFT/PUBLISHED; delete only in DRAFT.
- `can_view_article()` — published articles visible to any user with `knowledge_base.view`; authors with `knowledge_base.create` can see their own drafts; fallback to scope record check.
- `can_modify_article()` — superuser bypass, status check, permission check, fallback to scope record check.
- `build_article_access_hint()` — returns `can_view`, `view_only`, `can_edit`, `can_publish`, `can_archive`, `can_delete`, `reason`.
- `ensure_article_action_allowed()` — raises HTTP 403 if not allowed.

### `backend/app/services/esignature_service.py`

Responsibilities:
- `request_is_pending()` / `request_is_expired()` — status and expiry checks with timezone-aware comparison.
- `user_is_requester()` / `user_is_signer()` — role-in-workflow checks.
- `pending_signature_record_for_user()` — finds the user's own PENDING record in the request.
- `can_view_signature_request()` — superuser, esign.admin, esign.view, requester/signer, or scope check.
- `can_create_signature_request()` — esign.request permission or scope check.
- `can_sign_request()` — request must be PENDING, not expired, and the user must have a PENDING record for themselves.
- `can_cancel_signature_request()` — superuser or esign.admin can always cancel; requester can cancel with esign.cancel permission.
- `build_signature_access_hint()` — returns `can_view`, `view_only`, `can_sign`, `can_decline`, `can_cancel`, `can_admin`, `reason`.
- `ensure_signature_action_allowed()` — raises HTTP 403 for any unauthorized action.

---

## API Endpoint Hardening

### `backend/app/api/v1/endpoints/documents.py`

- All routes protected with `require_permission("documents", "<action>")` via `Depends`.
- List endpoint: filters by category, status, related_entity_type/id, owner_user_id, latest_only, search.
- `/by-entity/` helper: returns documents for a specific ERP entity type/id pair.
- Create: persists full governance field set.
- Approve/Archive/Obsolete: each uses `ensure_document_action_allowed` before mutating status.
- New-version: creates a new Document record, increments version, sets `is_latest=True`, marks previous `is_latest=False`.

### `backend/app/api/v1/endpoints/knowledge_base.py`

- All routes use `require_permission("knowledge_base", "<action>")`.
- Categories: list, create, patch — all permission-gated.
- Articles: list, create, get (increments view_count), update (creates revision), delete — each with correct permission level.
- Publish/archive: dedicated action endpoints using `ensure_article_action_allowed`.
- Revisions: list endpoint gated on `knowledge_base.view`.

### `backend/app/api/v1/endpoints/esign.py`

- `POST /requests` — `require_permission("esign", "request")`.
- `GET /requests` — `require_permission("esign", "view")`.
- `GET /requests/pending-for-me` — authenticated only (shows user's own pending records).
- `GET /dashboard` — `require_permission("esign", "view")`.
- `GET /requests/{id}` — view gated via `ensure_signature_action_allowed(user, req, "view")`.
- `POST /requests/{id}/sign` — gated via `ensure_signature_action_allowed(user, req, "sign")`.
- `POST /requests/{id}/decline` — gated via `ensure_signature_action_allowed(user, req, "decline")`.
- Signing: records IP address, user agent, signature data, signed_payload_hash; updates request counters; marks request SIGNED when all required signers have signed.
- `request_no` generated as `ESIGN-YYYYMMDD-NNNN`.

---

## Permissions and Roles

### Module Definitions (`backend/app/core/module_registry.py`)

| Module key | Route prefix | Permission actions | Critical |
|---|---|---|---|
| `documents` | `/documents` | view, create, edit, approve, archive, export | yes |
| `knowledge_base` | `/kb` | view, create, edit, publish, delete, admin | no |
| `esign` | `/esign` | view, request, sign, cancel, admin | yes |

All three promoted to `MODULE_DEFINITIONS`. No duplicate `ENDPOINT_ROUTE_DEFINITIONS` entries exist for these modules.

### Seed Permissions (`backend/app/db/seed.py`)

All permission codes for the above actions exist in `PERMISSIONS` and are assigned to appropriate roles:
- `admin` role receives `knowledge_base.view` and `esign.view` (and other standard admin permissions).
- Document permissions assigned to document management roles.
- KB publish/admin and esign admin/request are restricted to elevated roles; viewer gets only `view`.

### Route registration

Routes register from `MODULE_DEFINITIONS` via `register_module_routes()`. Confirmed: `/documents`, `/kb`, and `/esign` paths are present in the registered router.

---

## Frontend Changes

### `frontend/src/lib/knowledge_base.ts`

- Uses `apiClient` (shared auth-aware client) for all KB API calls.
- Base path: `/api/v1/kb`.
- Types: `KBCategory`, `KBArticle`, `KBArticleDetail`, `KBRevision`, `KBStats`.
- Functions: `fetchCategories`, `fetchArticles`, `fetchArticle`, `createArticle`, `updateArticle`, `publishArticle`, `archiveArticle`, `deleteArticle`, `fetchRevisions`.

### `frontend/src/lib/esign.ts`

- Uses `apiClient` exclusively — no bare `fetch` calls remain.
- Base path: `/api/v1/esign`.
- Types: `SignatureRequest`, `SignatureRecord`, `ESignDashboard`.
- Functions: `fetchDashboard`, `fetchRequests`, `fetchPendingForMe`, `createRequest`, `signRequest`, `declineRequest`, `fetchRequest`.

### Knowledge Base pages

- `frontend/src/app/dashboard/knowledge-base/page.tsx` — category list and article summary; action buttons conditionally rendered based on `knowledge_base.create` permission.
- `frontend/src/app/dashboard/knowledge-base/articles/page.tsx` — article list; create button hidden if user lacks `knowledge_base.create`.
- `frontend/src/app/dashboard/knowledge-base/articles/new/page.tsx` — article creation form; gated on `knowledge_base.create`.
- `frontend/src/app/dashboard/knowledge-base/[id]/page.tsx` — article detail; publish/archive/delete actions shown only with matching permissions.

### E-sign page

- `frontend/src/app/dashboard/esign/page.tsx` — dashboard stats and request list; sign/decline actions shown based on service hint; create request button gated on `esign.request` permission.

### Nav

- `frontend/src/components/nav-config.tsx` — KB nav entry uses `permission: "knowledge_base.view"`; e-sign nav entry uses `permission: "esign.view"`. No bare module-level permission keys remain.

---

## Tests Added

**File:** `backend/tests/test_gap012_document_knowledge_access.py`

| Test | What it covers |
|---|---|
| `test_document_lifecycle_separates_view_and_mutation` | Viewer can see but not mutate; editor can edit DRAFT but not locked/APPROVED; approver can approve DRAFT and archive APPROVED |
| `test_knowledge_base_publish_requires_dedicated_permission` | viewer sees published; editor cannot publish; publisher can publish DRAFT but not already-PUBLISHED |
| `test_esign_signing_requires_pending_signer_and_non_expired_request` | Signer can sign own pending record; non-signer blocked; expired request blocked |
| `test_document_knowledge_esign_permissions_are_registry_and_seed_owned` | All 16 required permission codes exist in registry and seed; no ENDPOINT_ROUTE_DEFINITIONS for these modules; admin has KB/e-sign view |
| `test_document_knowledge_esign_routes_register_from_module_registry` | `/documents`, `/kb`, `/esign` paths present in registered router; no route errors |

Pytest result from CODEX_PROGRESS.md: **5 tests passed**.

---

## Checks Already Recorded

From `CODEX_PROGRESS.md`:

| Check | Result |
|---|---|
| `py_compile` — models (documents, knowledge_base, esign) | passed |
| `py_compile` — schemas (documents, knowledge_base, esign) | passed |
| `py_compile` — services (document_access, knowledge_base, esignature) | passed |
| `py_compile` — endpoints (documents, knowledge_base, esign) | passed |
| `py_compile` — module_registry, seed | passed |
| `py_compile` — migration `20260515_0030_*` | passed |
| Pydantic smoke check (DocumentCreate, KBArticleCreate, SignatureRequestCreate, SignAction, DeclineAction) | passed |
| Mapper smoke check (configure_mappers with all three model sets) | passed with pre-existing unrelated relationship overlap warnings |
| Endpoint import check (`import app.api.v1.endpoints.documents/knowledge_base/esign`) | passed |
| Registry/seed contract check (module ownership, no duplicate route entries, all 16 permission codes) | passed |
| Alembic `heads` | passed — `20260515_0030 (head)` |
| Alembic `history -r 20260515_0020:20260515_0030` | passed |
| Alembic offline SQL generation | passed |
| `pytest tests/test_gap012_document_knowledge_access.py -q` | passed — 5 tests |
| `npm run type-check` (frontend) | passed |
| nav/permission key pattern scan | passed — `knowledge_base.view`, `knowledge_base.create`, `esign.view`, `esign.request` confirmed |
| `apiClient` usage in esign.ts (no bare fetch) | passed |
| Live DB migration | **skipped** — Docker daemon unavailable (`dockerDesktopLinuxEngine` pipe not found) |

---

## Known Limitations and Follow-Ups

1. **Live DB migration not run.** Migration `20260515_0030` was not applied to the live dev database because Docker was unavailable in the GAP-012 session. Must be run before this module is testable end-to-end.

2. **File storage is metadata-oriented only.** The `Document` model stores `file_url`, `storage_key`, `file_checksum_sha256`, `file_scan_status`, etc., but no upload engine is implemented. The system records metadata as provided; actual binary upload/download (S3, GCS, local) requires a future storage-pipeline task.

3. **E-sign `signature_data` is freeform.** The model accepts any string as signature data. Cryptographic verification, visual signature rendering, and qualified electronic signature (QES) standards are not implemented. This is an intentional v1 governance baseline, not a production-ready PKI implementation.

4. **Richer KB workflows deferred.** Article version merging, diff views, approval workflows, and subscriber notifications are not implemented. The current implementation covers CRUD, publish/archive, and revision history.

5. **Deep document audit/evidence trail.** The model includes `approved_at`, `obsolete_at`, `archived_at`, `legal_hold`, and `review_due_date`, but no automated review-due alert, audit-event log table, or SIEM export is wired. These are future hardening items.

6. **Record-level scope filtering not enforced in list endpoints.** List queries filter by explicit query params but do not enforce row-level scope based on the user's `access_scopes`. Scope enforcement on lists is a future hardening slice.

7. **Frontend forms are minimal.** The KB create/edit forms and e-sign create flow are functional but do not include rich markdown editing, file attachment, or signer search UI. These require a dedicated frontend hardening task.

---

## Acceptance Criteria Snapshot

| Item | Status |
|---|---|
| Document governance fields on model and migration | Complete |
| KB scope/publication fields on model and migration | Complete |
| E-sign evidence/lifecycle fields on model and migration | Complete |
| `document_access_service.py` with lifecycle lock and status checks | Complete |
| `knowledge_base_service.py` with publication permission separation | Complete |
| `esignature_service.py` with signer eligibility and expiry checks | Complete |
| Endpoints hardened with `require_permission` + service checks | Complete — 4 missing e-sign guards added 2026-06-04 |
| Module registry ownership (no duplicate route definitions) | Complete |
| Seed permission codes and role assignments | Complete |
| Frontend nav permission keys updated | Complete |
| Frontend KB pages use `knowledge_base.*` permissions | Complete — main page + articles/new page guarded |
| E-sign frontend page uses `RequirePermission("esign.view")` | Complete — guard added 2026-06-04 |
| E-sign frontend uses `apiClient` only | Complete |
| 7 focused pytest tests passing | Complete (5 pre-existing + 2 new permission contract tests 2026-06-04) |
| Migration offline SQL generation passed | Complete |
| Live DB migration applied | **Pending** — Docker unavailable in GAP-012 session |
| File upload pipeline | **Not implemented** — metadata-only |
