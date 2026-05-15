# GAP-012 Document Management / Knowledge System Schema Design

## Summary
GAP-012 should harden the existing document management, knowledge-base, and e-signature surfaces without replacing them. The current code already has useful ORM concepts and frontend pages, so the correct path is a reconciliation-first design:

- preserve the existing models and API paths where practical
- add Alembic ownership for missing core tables
- add additive governance fields needed by production document control
- split document, knowledge-base, and e-signature permissions cleanly
- add scope and lifecycle rules without blocking existing dev data
- move sensitive behavior into services before broad endpoint changes

No migration should drop or rename existing document/KB/e-sign tables during GAP-012C. Destructive cleanup can only happen later after live database inventory and explicit approval.

## Design Goals
- Make document-control schema deterministic under Alembic.
- Keep existing `Document`, `DocumentTag`, `KBCategory`, `KBArticle`, `KBArticleRevision`, `SignatureRequest`, and `SignatureRecord` concepts.
- Support SOP/work-instruction/QC/HR/compliance document lifecycle.
- Support expiry and compliance review workflows.
- Support knowledge-base authoring, publishing, revision history, and access levels.
- Support e-sign request, sign, decline, expiry, evidence, and audit behavior.
- Add ERP-wide permission and scope compatibility.
- Avoid a second parallel document system.

## Current Model Baseline
Existing document models:
- `Document`
- `DocumentTag`
- `DocumentCategory`
- `DocumentStatus`

Existing knowledge-base models:
- `KBCategory`
- `KBArticle`
- `KBArticleRevision`
- `KBArticleStatus`

Existing e-signature models:
- `SignatureRequest`
- `SignatureRecord`
- `SignatureRequestStatus`
- `SignatureRecordStatus`

The design below extends these models rather than replacing them.

## Alembic Reconciliation Strategy
GAP-012C should add a safe additive reconciliation migration that:

1. Creates missing core tables only if they do not already exist:
   - `documents`
   - `document_tags`
   - `kb_categories`
   - `kb_articles`
   - `kb_article_revisions`
   - `signature_requests`
   - `signature_records`
2. Adds missing columns with `if_not_exists`-style helpers where the project migration pattern supports it.
3. Adds indexes and constraints only after verifying the target columns exist.
4. Avoids dropping, renaming, or rewriting existing data.
5. Keeps enum creation offline-safe and duplicate-safe, following the enum strategy used in recent WMS/HR migrations.

The migration should include helper functions similar to prior reconciliation migrations:
- `table_exists`
- `column_exists`
- `index_exists`
- `constraint_exists`
- `create_enum_if_needed`

Live DB migration should be run only against local development PostgreSQL when Docker is available and safe.

## Document Model Extensions
Extend `Document` additively with governance, storage, scope, and lifecycle fields.

Recommended fields:
- `document_no` nullable unique/indexed business identifier
- `lineage_id` nullable UUID/string to group all versions of the same controlled document
- `document_type` nullable string for future custom taxonomy without expanding enums constantly
- `department_id` nullable UUID/string scope reference
- `company_id` nullable UUID/string scope reference
- `branch_id` nullable UUID/string scope reference
- `factory_id` nullable UUID/string scope reference
- `product_category_id` nullable UUID/string scope reference
- `supplier_id` nullable UUID/string scope reference
- `customer_id` nullable UUID/string scope reference
- `confidentiality_level` nullable string, default `INTERNAL`
- `retention_until` nullable date
- `legal_hold` boolean default false
- `review_due_date` nullable date
- `next_review_owner_id` nullable FK to `users.id`
- `approved_at` nullable timezone-aware datetime
- `obsolete_at` nullable timezone-aware datetime
- `archived_at` nullable timezone-aware datetime
- `locked_at` nullable timezone-aware datetime
- `locked_by_id` nullable FK to `users.id`
- `storage_provider` nullable string
- `storage_key` nullable text
- `file_checksum_sha256` nullable string(64)
- `file_scan_status` nullable string, default `NOT_SCANNED`
- `file_scan_result` nullable text
- `file_locked` boolean default false
- `created_by_id` nullable FK to `users.id`
- `updated_by_id` nullable FK to `users.id`

Recommended indexes:
- `documents.document_no`
- `documents.lineage_id`
- `documents.status`
- `documents.category`
- `documents.expiry_date`
- `documents.review_due_date`
- `documents.company_id`
- `documents.branch_id`
- `documents.factory_id`
- `documents.department_id`
- `(related_entity_type, related_entity_id)`
- `(lineage_id, version)`

Recommended constraints:
- `version > 0`
- `file_size_bytes >= 0`
- One latest version per lineage if the database supports a safe partial unique index:
  - unique `(lineage_id)` where `is_latest = true`

If existing data has no lineage, GAP-012F should fill `lineage_id` lazily or during a safe backfill task. GAP-012C should not assume a destructive backfill.

## Document Status Lifecycle
Keep the existing `DocumentStatus` values for compatibility:
- `DRAFT`
- `APPROVED`
- `OBSOLETE`
- `ARCHIVED`

Service-layer rules should enforce:
- `DRAFT` documents can be edited by users with document edit permission and matching scope.
- `APPROVED` documents cannot have core file/version fields edited directly.
- New versions should be created through the new-version flow, not by overwriting approved files.
- `OBSOLETE` and `ARCHIVED` documents should be read-only except for controlled administrative metadata.
- `legal_hold = true` prevents archive/disposal.
- `file_locked = true` prevents direct storage/file metadata mutation.

`DocumentUpdate` should stop accepting direct `status` changes in a later schema/API slice, or endpoint logic must ignore/reject direct lifecycle changes and require explicit lifecycle endpoints.

## Document Scope Model
Documents should use the existing ERP-wide scope helpers from GAP-SEC-001. Scope resolution order:

1. Explicit document fields:
   - company
   - branch
   - factory
   - department
   - product category
   - supplier
   - customer
2. Related entity mapping:
   - if `related_entity_type` maps to a known module, resolve scope through the related record service when available
3. Owner fallback:
   - owner/creator can view draft documents if no broader document scope exists
4. Deny by default for mutation

View and mutation must remain separate:
- broad view can show many documents
- create/edit/approve/archive/export must require scoped permission or explicit global permission

Recommended permission to scope mapping:
- `documents.view` -> general document view
- `documents.view_all` -> global/broad view
- `documents.view_own_scope` -> scoped view
- `documents.create_all` / `documents.create_own_scope`
- `documents.edit_all` / `documents.edit_own_scope`
- `documents.approve_all` / `documents.approve_own_scope`
- `documents.archive_all` / `documents.archive_own_scope`
- `documents.export_all` / `documents.export_own_scope`

Keep legacy `documents.create`, `documents.edit`, and `documents.approve` working as compatibility aliases while new scoped permissions roll out.

## Document Tags and Classification
`DocumentTag` can remain as the basic freeform tagging model.

Recommended additive improvements:
- unique constraint or partial unique index on `(document_id, tag)` where practical
- normalize tag case in service layer
- optionally add `tag_type` later if controlled taxonomy becomes necessary

For GAP-012, avoid replacing tags with a full taxonomy system.

## Knowledge Base Model Extensions
Keep `KBCategory`, `KBArticle`, and `KBArticleRevision`.

Recommended additive fields on `KBArticle`:
- `company_id` nullable string/UUID scope reference
- `department_id` nullable string/UUID scope reference
- `factory_id` nullable string/UUID scope reference
- `module_key` nullable string for module-specific articles
- `published_by_id` nullable FK to `users.id`
- `archived_by_id` nullable FK to `users.id`
- `archived_at` nullable datetime
- `review_due_date` nullable date
- `access_scope_type` nullable string
- `access_scope_id` nullable string
- `is_internal_only` boolean default true

Recommended improvements:
- migrate `status` from loose string behavior to validated schema/service rules; if changing the DB enum is too risky, keep string column but validate strictly through schemas/services.
- keep revisions immutable.
- increment version only through service-managed updates.

Knowledge-base permissions:
- `knowledge_base.view`
- `knowledge_base.create`
- `knowledge_base.edit`
- `knowledge_base.publish`
- `knowledge_base.delete`
- `knowledge_base.admin`

Access-level enforcement should be service-owned:
- published articles are visible to users with view permission and matching access/scope
- draft articles are visible only to author/editor/admin roles
- archived articles require admin/editor permission

## E-Signature Model Extensions
Keep `SignatureRequest` and `SignatureRecord`.

Recommended additive fields on `SignatureRequest`:
- `company_id` nullable string/UUID scope reference
- `branch_id` nullable string/UUID scope reference
- `department_id` nullable string/UUID scope reference
- `factory_id` nullable string/UUID scope reference
- `module_key` nullable string
- `related_entity_type` nullable string
- `related_entity_id` nullable string
- `document_hash_sha256` nullable string(64)
- `payload_hash_sha256` nullable string(64)
- `completed_at` nullable datetime
- `expired_at` nullable datetime
- `cancelled_at` nullable datetime
- `cancelled_by_id` nullable FK to `users.id`
- `evidence_summary` nullable JSON/text depending on project convention
- `audit_request_id` nullable string for request-id correlation

Recommended additive fields on `SignatureRecord`:
- `signed_payload_hash_sha256` nullable string(64)
- `decline_reason` nullable text
- `evidence_hash_sha256` nullable string(64)
- `auth_method` nullable string
- `signed_document_version` nullable integer
- `signed_document_id` nullable FK/string if not already covered

Recommended constraints/indexes:
- index `signature_requests.status`
- index `signature_requests.document_id`
- index scope fields used by dashboards
- unique `(request_id, signer_id)` where `signer_id` is not null

E-signature permissions:
- `esign.view`
- `esign.request`
- `esign.sign`
- `esign.cancel`
- `esign.admin`

Signer eligibility remains required even when a user has `esign.sign`.

## E-Signature Lifecycle
Service-layer rules:
- Request creation requires `esign.request` plus matching document/scope permission.
- Sign requires:
  - authenticated user
  - active signer record for current user
  - pending request
  - not expired
  - document/payload hash still matches if attached to a document
- Decline requires the same signer eligibility.
- Cancellation requires requester/admin permission and pending status.
- Expiry should be computed consistently and persisted when a pending request passes `expires_at`.
- Detail response should not expose raw `signature_data` to users who are not requester, signer, or e-sign admin.

## File Storage and Download Governance
GAP-012 should not build an entire storage system in the schema task, but the schema should prepare for it.

Recommended minimum design:
- `storage_provider`: `local`, `s3`, `gcs`, `azure`, `external`
- `storage_key`: provider-local object key/path
- `file_url`: retained for backward compatibility, but not trusted as an authorization boundary
- `file_checksum_sha256`: content integrity
- `file_scan_status`: `NOT_SCANNED`, `PENDING`, `CLEAN`, `QUARANTINED`, `FAILED`
- `file_locked`: prevents file replacement after approval

Secure download should be an endpoint-mediated operation in GAP-012G/F, not raw URL exposure for protected documents.

## Module Registry and Permission Design
Promote these from loose endpoint-route definitions to full module definitions:
- `documents`
- `knowledge_base`
- `esign`

Each module definition should include:
- route prefix
- import path
- label
- sidebar group
- icon key
- permission actions
- enabled flag
- critical flag for document/e-sign governance where applicable

Route compatibility:
- Keep `/api/v1/documents`
- Keep `/api/v1/kb`
- Keep `/api/v1/esign`

Frontend route compatibility:
- Keep `/dashboard/documents`
- Keep `/dashboard/knowledge-base`
- Keep `/dashboard/esign`

## Schema and API Compatibility
Backward-compatible requirements:
- Existing document create/read/update payloads should continue to work.
- Existing file metadata fields should remain readable.
- Existing document categories/status values should remain valid.
- Existing KB article/category endpoints should keep their paths while adding permission checks.
- Existing e-sign endpoints should keep their paths while adding permission and response-filtering rules.
- Existing `documents.create`, `documents.edit`, and `documents.approve` permissions should remain as aliases until all role templates use scoped permissions.

Breaking changes to avoid during GAP-012:
- dropping `file_url`
- removing `status` from `DocumentUpdate` before endpoint behavior is adjusted
- replacing `KBArticle.status` storage type destructively
- renaming `/api/v1/kb` or `/api/v1/esign`
- deleting existing e-sign signature data without retention planning

## Service Layer Design
Add service modules rather than growing endpoint files:

Recommended backend services:
- `backend/app/services/document_access_service.py`
- `backend/app/services/document_lifecycle_service.py`
- `backend/app/services/knowledge_base_service.py`
- `backend/app/services/esignature_service.py`

Responsibilities:
- resolve document/KB/e-sign scopes
- compute access hints for frontend rows
- enforce lifecycle/status transitions
- create immutable revisions/new versions
- centralize e-sign expiry/sign/decline/cancel behavior
- emit audit records where existing audit infrastructure supports it

Endpoint files should become thin wrappers around these services.

## Frontend Design Implications
GAP-012H should:
- keep existing pages and layout patterns
- update nav permissions:
  - Documents -> `documents.view`
  - Document Expiry -> `documents.view`
  - Document Compliance -> `documents.view`
  - Knowledge Base -> `knowledge_base.view`
  - E-Signatures -> `esign.view`
- switch e-sign client from raw `fetch` to the shared API client convention
- add view-only badges/action hiding where backend returns access hints
- add permission guards to KB and e-sign pages
- expose document expiry/compliance actions only where permissions allow

## Migration Scope for GAP-012C
GAP-012C should include:
- create-if-missing core document, KB, and e-sign tables
- additive governance/scope/storage columns
- indexes for lifecycle/status/scope/expiry fields
- safe uniqueness constraints where they will not break existing dirty dev data
- no destructive data migration

Suggested migration name:
- `20260515_0030_document_knowledge_reconciliation.py`

If live DB already has tables from prior `create_all`, migration must avoid duplicate table/column failures.

## Test Strategy
GAP-012J should include focused tests for:
- permission contract registration for documents, KB, and e-sign
- KB create/update/delete blocked without dedicated permissions
- e-sign sign/decline restricted to eligible signers
- e-sign request/list/detail respects requester/signer/admin rules
- document lifecycle prevents direct edits to approved/archived/obsolete records
- document scoped mutation denial outside assigned scope
- schema/reconciliation migration imports and offline SQL generation
- frontend nav permission keys and view-only wiring where tooling supports it

Prefer service/contract tests first; add endpoint tests where safe fixtures already exist.

## Documentation Requirements
GAP-012K should document:
- document lifecycle
- versioning/new-version workflow
- expiry/compliance review workflow
- secure file storage/download assumptions
- knowledge-base authoring/publishing workflow
- e-signature request/sign/decline workflow
- permissions and scope rules
- admin setup and seed roles
- tests/check commands
- known limitations

## Acceptance Criteria for GAP-012B
GAP-012B is complete when:
- The current model baseline is documented.
- The additive migration strategy is clear.
- Document governance, storage, lifecycle, scope, and permission fields are designed.
- Knowledge-base governance and permission model are designed.
- E-signature evidence, lifecycle, and permission model are designed.
- Frontend permission/nav implications are documented.
- Compatibility and non-destructive migration rules are explicit.
- GAP-012C has a precise migration scope.
