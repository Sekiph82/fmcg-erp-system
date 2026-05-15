# GAP-012 Document Management / Knowledge System Implementation Notes

Status: GAP-012K documentation complete
Phase: Phase 3 - High-importance operational modules
Business priority: High
Technical area: Documents / Knowledge / E-Signature

## Summary

GAP-012 hardens the existing document management, knowledge-base, and electronic-signature surfaces without replacing their current routes, models, or frontend pages. The repository already had useful document, article, and signature mechanics; this slice adds deterministic migration ownership, governance fields, dedicated module permissions, service-owned workflow checks, frontend permission alignment, and focused contract tests.

The implementation keeps these API routes stable:

- `/api/v1/documents`
- `/api/v1/kb`
- `/api/v1/esign`

The implementation keeps these frontend routes stable:

- `/dashboard/documents`
- `/dashboard/documents/expiring`
- `/dashboard/documents/compliance`
- `/dashboard/knowledge-base`
- `/dashboard/knowledge-base/articles`
- `/dashboard/esign`

## Audit Findings From GAP-012A

The audit found real but uneven coverage:

- Documents already had lifecycle, versioning, expiry, tags, stats, and frontend pages.
- Knowledge base already had categories, articles, revisions, search, stats, and pages.
- E-signature already had request, signer, sign, decline, and dashboard mechanics.
- Core Alembic ownership for document, KB, and e-signature tables was unclear.
- Knowledge-base and e-signature permissions were too broad or authentication-only.
- E-signature evidence existed but needed stronger governance fields and centralized eligibility rules.
- Document storage remained metadata-first rather than a secure binary upload/download pipeline.
- Frontend navigation used unrelated permissions for knowledge-base and e-sign surfaces.

## Design Decision From GAP-012B

The chosen design was reconciliation-first:

- Reuse `Document`, `DocumentTag`, `KBCategory`, `KBArticle`, `KBArticleRevision`, `SignatureRequest`, and `SignatureRecord`.
- Add a safe additive Alembic migration instead of recreating the module.
- Promote `documents`, `knowledge_base`, and `esign` into module registry ownership.
- Add service helpers for lifecycle, publication, signer eligibility, expiry, and access hints.
- Keep compatibility fields and route paths intact.
- Document storage/download remains a follow-up; this slice adds governance metadata but does not implement full binary storage.

## Migration and Schema Changes

Migration file:

- `backend/alembic/versions/20260515_0030_document_knowledge_reconciliation.py`

The migration is additive and duplicate-safe for local development databases. It creates missing core tables when absent, adds governance columns when absent, and avoids destructive data changes.

Major schema coverage includes:

- document identifiers, lineage/version metadata, lifecycle timestamps, legal hold, review ownership, scope fields, storage provider/key, checksum, scan status, and file lock metadata
- knowledge-base publication/archive metadata, module/scope fields, review date, internal-only flag, and article revision ownership
- e-signature scope fields, document/payload hashes, completion/expiry/cancellation metadata, evidence summary, signature-record evidence hashes, decline reason, and signed document references

Live DB migration was not run in this session because Docker was unavailable when GAP-012C was executed. The migration passed py_compile, Alembic head/history, and offline SQL generation checks.

## Backend Models and Schemas

Updated model files:

- `backend/app/models/documents.py`
- `backend/app/models/knowledge_base.py`
- `backend/app/models/esign.py`

Updated schema files:

- `backend/app/schemas/documents.py`
- `backend/app/schemas/knowledge_base.py`
- `backend/app/schemas/esign.py`

The schemas expose the new governance and evidence fields while preserving existing create/read/update payload compatibility.

## Backend Service Behavior

New service files:

- `backend/app/services/document_access_service.py`
- `backend/app/services/knowledge_base_service.py`
- `backend/app/services/esignature_service.py`

Document behavior:

- separates view from mutation
- blocks edits on approved, obsolete, archived, file-locked, or legal-hold records where action rules require it
- limits approve/archive/obsolete/new-version behavior by status and permission
- returns access hints for frontend view-only behavior

Knowledge-base behavior:

- published articles can be viewed with `knowledge_base.view`
- draft author visibility is supported for creators
- publish/delete/archive/edit behavior is permission and status aware
- access hints indicate whether an article is view-only

E-signature behavior:

- request viewing honors e-sign admin/view permissions plus requester/signer eligibility
- signing and declining require a pending signer record and a non-expired pending request
- cancelling requires requester plus `esign.cancel`, or e-sign admin
- access hints expose sign, decline, cancel, admin, and view-only state

## API Endpoint Behavior

Updated endpoint files:

- `backend/app/api/v1/endpoints/documents.py`
- `backend/app/api/v1/endpoints/knowledge_base.py`
- `backend/app/api/v1/endpoints/esign.py`

Permission hardening:

- document list/detail/stats/history/tag reads use `documents.view`
- document create/new-version uses `documents.create`
- document edit/tag mutations use `documents.edit`
- document approve/obsolete/archive uses document approval authority and service rules
- knowledge-base category/article reads use `knowledge_base.view`
- knowledge-base create/edit/delete operations use dedicated KB permissions
- e-sign request creation uses `esign.request`
- e-sign dashboard/list views use `esign.view` where broad access is needed
- e-sign detail/sign/decline uses service eligibility rules so signer/requester context remains enforced

The endpoint files still preserve existing payload styles in places where a later API-cleanup pass can introduce stricter Pydantic request models.

## Module Registry and Permissions

`backend/app/core/module_registry.py` now owns three first-class modules:

- `documents`
- `knowledge_base`
- `esign`

They are no longer duplicate loose endpoint-route definitions.

Seed permissions in `backend/app/db/seed.py` include:

- `documents.view`
- `documents.create`
- `documents.edit`
- `documents.approve`
- `documents.archive`
- `documents.export`
- `knowledge_base.view`
- `knowledge_base.create`
- `knowledge_base.edit`
- `knowledge_base.publish`
- `knowledge_base.delete`
- `knowledge_base.admin`
- `esign.view`
- `esign.request`
- `esign.sign`
- `esign.cancel`
- `esign.admin`

Role grants are conservative:

- admin receives the full document, KB, and e-sign permission set
- quality/compliance style roles receive document governance and read access to KB/e-sign where appropriate
- HR/manager/operator-style roles receive view-oriented document/KB access and signing authority where useful
- broad KB admin and e-sign admin permissions are not granted to normal roles by default

## Frontend Behavior

Updated frontend files include:

- `frontend/src/components/nav-config.tsx`
- `frontend/src/lib/knowledge_base.ts`
- `frontend/src/lib/esign.ts`
- `frontend/src/app/dashboard/knowledge-base/page.tsx`
- `frontend/src/app/dashboard/knowledge-base/articles/page.tsx`
- `frontend/src/app/dashboard/knowledge-base/articles/new/page.tsx`
- `frontend/src/app/dashboard/knowledge-base/[id]/page.tsx`
- `frontend/src/app/dashboard/esign/page.tsx`

Navigation now uses dedicated permissions:

- Documents: `documents.view`
- Expiry Tracker: `documents.view`
- Compliance Docs: `documents.view`
- Knowledge Base: `knowledge_base.view`
- KB Articles: `knowledge_base.view`
- E-Signatures: `esign.view`

The e-sign client now follows the shared API client pattern instead of raw `fetch`. KB and e-sign pages use dedicated permission guards/action visibility rather than unrelated HR or document permissions.

## Tests Added

Focused test file:

- `backend/tests/test_gap012_document_knowledge_access.py`

Coverage includes:

- document lifecycle view versus mutation behavior
- knowledge-base publish permission separation
- e-sign pending signer and expiry eligibility
- module registry and seed permission ownership
- route registration from module definitions for `/documents`, `/kb`, and `/esign`

Commands already recorded for GAP-012J:

- `cd backend; .\venv\Scripts\python.exe -m py_compile tests\test_gap012_document_knowledge_access.py app\services\document_access_service.py app\services\knowledge_base_service.py app\services\esignature_service.py app\core\module_registry.py app\db\seed.py`
- `cd backend; .\venv\Scripts\python.exe -m pytest tests\test_gap012_document_knowledge_access.py -q`

Result:

- 5 focused GAP-012 tests passed.

## Known Limitations and Follow-Up

- Live Alembic upgrade for `20260515_0030` still needs verification when Docker/PostgreSQL is available.
- Document file storage is still metadata-governed; full upload/download authorization, checksum calculation, scanning, and provider storage remain follow-up work.
- Document scope enforcement is present through shared helpers but should be expanded with deeper related-entity scope resolution.
- Knowledge-base endpoint payloads still use some dict-style request bodies; stricter request schemas can be added later without changing route paths.
- E-signature evidence now has hash/evidence fields, but immutable audit-chain integration and document hash verification should be expanded before regulated signature reliance.
- Detail responses may still expose signature data to eligible request viewers; a later privacy-hardening pass should reduce raw signature exposure where possible.
- Frontend view-only handling is started but not comprehensive across every document/KB/e-sign action surface.

## Acceptance Criteria Snapshot

- Core document, KB, and e-sign schema ownership: done via additive reconciliation migration.
- Backend imports and focused route contracts: done.
- Dedicated module registry ownership: done.
- Seeded permissions and role grants: done.
- KB and e-sign permission hardening: done for current routes.
- Document lifecycle service checks: done for this slice.
- Frontend nav/page permission alignment: done.
- E-sign shared API client alignment: done.
- Focused tests added and passing: done.
- Implementation documentation: done.
- Live DB verification: pending local Docker/PostgreSQL availability.
