# GAP-012 Document Management / Knowledge System Audit

## Summary
GAP-012 is not starting from an empty module. The repository already has a real document metadata/versioning surface, a knowledge base surface, electronic-signature models/endpoints, document expiry and compliance frontend pages, and dashboard navigation entries.

The implementation is still only partial for an enterprise FMCG ERP/MES document-control system. The largest risks are migration ownership, uneven auth/permission enforcement, lack of scoped access, metadata-only file handling, weak e-sign governance, and inconsistent frontend/backed parity. Documents are guarded better than knowledge base and e-signature, but none of the three surfaces yet behaves like a fully controlled SOP/specification/quality-record system.

## Business Importance
Document control is a regulated manufacturing foundation. SOPs, work instructions, QC documents, customs/shipment documents, HR documents, and compliance certificates must be versioned, approved, searchable, expirable, traceable, and access-controlled.

For FMCG operations this gap affects:
- shop-floor SOP and work-instruction control
- quality and HACCP documentation
- supplier/customer/regulatory compliance files
- expiry-driven certificate management
- internal knowledge articles and operator guidance
- approval evidence and electronic-signature workflows
- audit readiness

Without hardened document governance, the ERP can show document pages but cannot reliably prove which document version was effective, who approved it, who signed it, or whether users only accessed documents within their role and operational scope.

## Files Inspected
Backend files inspected:
- `backend/app/api/v1/endpoints/documents.py`
- `backend/app/api/v1/endpoints/knowledge_base.py`
- `backend/app/api/v1/endpoints/esign.py`
- `backend/app/models/documents.py`
- `backend/app/models/knowledge_base.py`
- `backend/app/models/esign.py`
- `backend/app/schemas/documents.py`
- `backend/app/schemas/esign.py`
- `backend/app/core/module_registry.py`
- `backend/app/db/seed.py`
- `backend/alembic/versions/*` search results for document, knowledge-base, and e-sign table ownership
- `backend/tests/*` search results for document, knowledge-base, and e-sign focused tests

Frontend files inspected:
- `frontend/src/lib/documents.ts`
- `frontend/src/lib/knowledge_base.ts`
- `frontend/src/lib/esign.ts`
- `frontend/src/components/documents/DocumentPanel.tsx`
- `frontend/src/app/dashboard/documents/page.tsx`
- `frontend/src/app/dashboard/documents/new/page.tsx`
- `frontend/src/app/dashboard/documents/[id]/page.tsx`
- `frontend/src/app/dashboard/documents/expiring/page.tsx`
- `frontend/src/app/dashboard/documents/compliance/page.tsx`
- `frontend/src/app/dashboard/knowledge-base/page.tsx`
- `frontend/src/app/dashboard/knowledge-base/[id]/page.tsx`
- `frontend/src/app/dashboard/knowledge-base/articles/page.tsx`
- `frontend/src/app/dashboard/knowledge-base/articles/new/page.tsx`
- `frontend/src/app/dashboard/esign/page.tsx`
- `frontend/src/components/nav-config.tsx`

## Existing Backend Coverage
Documents:
- `documents.py` exposes a substantial document API:
  - list/search/filter
  - related-entity lookup
  - create
  - detail
  - update
  - approve
  - obsolete
  - archive
  - create new version
  - stats
  - version history
  - expiring documents
  - tag add/remove/list/search
- `documents.py` uses `require_permission("documents", "...")` on the inspected endpoints.
- `Document` supports categories, version, revision notes, previous-version link, latest flag, status, effective date, expiry date, owner, approver, related entity type/id, and file metadata.
- `DocumentTag` supports many tags per document.

Knowledge base:
- `knowledge_base.py` exposes category, article, revision, search, and stats endpoints.
- `KBCategory`, `KBArticle`, and `KBArticleRevision` exist.
- Articles support slug, title, summary, markdown content, category, tags, status, version, author/editor, publish date, view count, featured flag, and access level.
- Article revisions are recorded on updates.

Electronic signatures:
- `esign.py` exposes signature request create/list/dashboard/detail/sign/decline flows.
- `SignatureRequest` and `SignatureRecord` exist.
- Signature requests include request number, document reference, requester, subject/message, status, expiry, required/signed/declined counts.
- Signature records include signer, status, signed/declined timestamps, IP address, user agent, and signature data.

## Existing Frontend Coverage
Documents:
- Document dashboard/list, new document page, detail page, expiring page, compliance page, and document panel component exist.
- The document client includes list, by-entity, get, stats, create, update, approve, obsolete, archive, new-version, and version methods.
- Document pages use `RequirePermission`/`PermissionGuard` patterns for at least the main documents surfaces.

Knowledge base:
- Knowledge-base list, article list/new, and detail pages exist.
- `frontend/src/lib/knowledge_base.ts` provides a typed client surface.
- Sidebar navigation currently exposes the knowledge base under an unrelated broad permission in the inspected nav config.

Electronic signatures:
- An e-sign dashboard page exists.
- `frontend/src/lib/esign.ts` provides client methods, but it uses raw `fetch` rather than the shared API client pattern used by most newer modules.
- Sidebar navigation exposes e-signature using document view permission rather than a dedicated e-sign permission.

## Existing Permissions / Roles / Scopes
Existing permission coverage found:
- `backend/app/db/seed.py` defines document permissions including `documents.view`, `documents.create`, `documents.edit`, and `documents.approve`.
- `backend/app/core/module_registry.py` currently registers `documents`, `esign`, and `knowledge_base` as endpoint route definitions, not full module definitions.
- The frontend navigation uses `documents.view` for Documents, Document Expiry, Document Compliance, and E-Signatures.
- The frontend navigation uses `hr.view` for Knowledge Base, which is not an appropriate source of truth for knowledge articles.

Permission gaps found:
- No dedicated `knowledge_base.view`, `knowledge_base.create`, `knowledge_base.edit`, `knowledge_base.delete`, or `knowledge_base.publish` permission contract was found in the inspected seed/registry search.
- No dedicated `esign.view`, `esign.request`, `esign.sign`, `esign.cancel`, or `esign.admin` permission contract was found in the inspected seed/registry search.
- Knowledge-base endpoints depend on authentication only and do not use `require_permission`.
- E-sign endpoints depend on authentication and signer/requester checks in some actions, but do not use a module permission model for creating, listing, dashboard access, or administration.
- Scope enforcement is not present for company, department, factory, quality, HR, supplier, customer, or related-entity document ownership.

## Existing Migrations
Searches of `backend/alembic/versions` did not find a clear migration that creates the core `documents`, `document_tags`, `kb_*`, `signature_requests`, or `signature_records` tables.

This is a major ownership risk because the ORM models exist, and endpoints assume the tables exist, but schema creation is not clearly tied to Alembic history. The next design/migration tasks must reconcile this carefully with existing development databases before adding or changing behavior.

Related document-like tables exist elsewhere, such as supplier portal, ESS, logistics, and landed-cost document references, but those do not replace the core document-control, knowledge-base, and e-signature table ownership.

## Existing Tests
No focused backend tests were found for:
- document lifecycle permissions/status transitions
- document versioning and latest-version behavior
- document expiry/compliance queries
- knowledge-base permissions and revision behavior
- e-sign signer/requester authorization
- e-sign expiry/status locking
- migration presence for the document/KB/e-sign tables

No focused frontend tests were found for:
- documents page guards
- knowledge-base permission visibility
- e-sign page permission visibility
- document expiry/compliance UI behavior

## Existing Documentation
The GAP planning files mention document management and internal knowledge-system work as a high-importance operational gap. A dedicated GAP-012 implementation/audit document was not present before this audit.

The code itself has descriptive route comments in `esign.py`, but there is no complete developer/admin/user documentation for:
- canonical document-control workflow
- approval and versioning rules
- expiry/compliance review process
- knowledge-base authoring and publishing workflow
- e-signature evidence and retention rules
- permissions and scopes
- migration ownership
- file storage configuration

## Key Finding 1: Document Management Exists but Migration Ownership Is Unclear
The document model and endpoints are more mature than a stub. They include categories, statuses, versioning fields, owner/approver relationships, related entity links, tags, approval, obsolete/archive actions, version history, expiring-document support, and stats.

The main problem is foundation reliability. The inspected migration history did not clearly create the core document tables. For a serious ERP, table ownership must be deterministic through Alembic. Before adding richer lifecycle rules, GAP-012B/C must decide whether to add an additive reconciliation migration and how to handle databases where `Base.metadata.create_all` may already have created these tables.

## Key Finding 2: Knowledge Base Exists but Permission Model Is Too Broad
The knowledge base has real models and endpoints, including category and article revision support. However, the backend currently relies on `get_current_user` rather than module-specific permissions for create/update/delete/search/admin operations.

On the frontend, the Knowledge Base nav item is guarded by `hr.view`, which means HR visibility is being reused as a proxy for internal knowledge access. That is too broad and semantically wrong for a cross-functional ERP knowledge system.

The knowledge base needs its own permission contract, publishing workflow, access-level enforcement, and module registry ownership.

## Key Finding 3: E-Signature Exists but Needs Governance and Evidence Hardening
The e-signature implementation has real request and signer-record mechanics. Signers are checked before sign/decline actions, and signer evidence includes IP address and user agent.

The implementation is not yet production-grade for regulated approval evidence:
- no dedicated e-sign permission contract was found
- request create/list/dashboard/detail endpoints are not governed by e-sign-specific permissions
- detail responses include signature data
- no cryptographic document hash or signed payload hash was found
- expiry enforcement appears incomplete because pending requests can still be checked by status, but automatic expiry/status transition is not clearly centralized
- no immutable audit chain was found for signature events
- e-sign routes are not clearly bound to document approval/version lifecycle

This should be hardened before relying on e-signature for controlled SOPs, QC release, finance approvals, or regulatory records.

## Key Finding 4: File Storage / Upload Pipeline Is Still Metadata-Only
The document model stores `file_url`, `file_name`, `file_size_bytes`, and `mime_type`. The document create endpoint accepts file metadata, but the inspected backend surface does not include a real upload/storage pipeline.

Missing or unclear pieces include:
- upload endpoint or signed upload flow
- storage adapter abstraction
- file checksum/hash
- malware/content scanning status
- file version immutability
- MIME/type allowlist enforcement
- maximum file size policy
- retention/legal-hold fields
- secure download authorization

For an enterprise document-control module, file metadata alone is not enough.

## Key Finding 5: Frontend Coverage Exists but Has Permission and Client Gaps
The documents frontend is ahead of the other surfaces: documents pages exist and use permission guards, and the client supports most lifecycle calls.

Gaps remain:
- document client does not expose all backend endpoints found, such as expiring list and tag operations
- knowledge-base pages are not protected by a dedicated knowledge-base permission
- e-sign page is not protected by a dedicated e-sign permission
- e-sign client uses raw `fetch` rather than the shared API client convention
- frontend route/nav visibility is not aligned with backend-owned module metadata
- no clear "view only" UX appears for scoped document restrictions

## Missing Pieces
- Alembic ownership for core document, knowledge-base, and e-signature tables.
- Dedicated module registry definitions for `documents`, `knowledge_base`, and `esign`.
- Dedicated knowledge-base and e-sign permission keys and seed role contracts.
- Scope model for document access by company, branch, department, factory, product category, supplier, customer, HR record, quality record, or related module entity.
- Central document-control service for lifecycle rules.
- Central e-signature service for request/sign/decline/expire evidence logic.
- File upload, storage, checksum, secure download, and scanning workflow.
- Document retention, legal hold, archive policy, and disposal workflow.
- Strong version-lineage rules and immutable approved file/version behavior.
- Knowledge-base publishing/access-level enforcement.
- E-signature evidence hardening with document hash and immutable audit trail.
- Focused backend tests for documents, knowledge base, e-signature, and permissions.
- Focused frontend tests for document/KB/e-sign navigation and action visibility.
- Admin/user/developer documentation.

## Partial Pieces
- Document lifecycle exists, but status transitions and direct update payloads need tightening.
- Document versioning exists, but latest-version and lineage integrity need constraints and service ownership.
- Document expiry exists, but compliance workflow and review responsibility need clearer design.
- Knowledge-base revisions exist, but permission, publication, and access-level enforcement are weak.
- E-sign records exist, but evidence, permission, expiry, and audit controls are not complete.
- Frontend documents pages exist, but KB/e-sign guards and clients need alignment.
- Seed permissions exist for documents only, not for KB/e-sign.

## Risks
- A fresh database may fail at runtime if core document/KB/e-sign tables are missing from Alembic history.
- Authenticated users may create, update, or delete knowledge-base content without a dedicated permission.
- Authenticated users may see e-sign dashboards or request details beyond the intended workflow.
- Signature data may be exposed more broadly than necessary.
- Users may approve or obsolete documents without scope checks for the underlying company, department, factory, quality, HR, supplier, or customer context.
- Approved documents may still be mutable through generic update paths unless service-layer rules prevent it.
- File URLs may point to unverified or externally accessible content if storage/download rules are not centralized.
- Frontend nav may show or hide pages based on unrelated permissions.

## Recommended GAP-012B Design Direction
GAP-012B should design a reconciliation-first architecture rather than a rewrite.

Recommended direction:
- Keep existing `Document`, `DocumentTag`, `KBCategory`, `KBArticle`, `KBArticleRevision`, `SignatureRequest`, and `SignatureRecord` concepts.
- Add an Alembic reconciliation plan for any missing table ownership and missing governance columns.
- Promote `documents`, `knowledge_base`, and `esign` into full module registry definitions with dedicated route prefixes, nav metadata, and permissions.
- Define permission contracts:
  - `documents.view`, `documents.create`, `documents.edit`, `documents.approve`, `documents.archive`, `documents.export`
  - `knowledge_base.view`, `knowledge_base.create`, `knowledge_base.edit`, `knowledge_base.publish`, `knowledge_base.delete`
  - `esign.view`, `esign.request`, `esign.sign`, `esign.admin`
- Add scope fields to documents/signature requests where practical, such as company, branch, department, factory, product category, related module, and related entity.
- Add document service rules for draft/edit/approve/obsolete/archive/new-version transitions.
- Add e-sign service rules for request authorization, signer authorization, expiry, immutable evidence, and audit.
- Add file governance fields before implementing binary storage deeply: checksum, storage provider/key, scan status, locked file flag, retention/legal-hold fields.
- Standardize frontend clients on the shared API client and guard all surfaces by dedicated permissions.

## Acceptance Criteria for GAP-012 Completion
GAP-012 should be considered complete only when:
- Core document, knowledge-base, and e-signature schemas are owned by safe Alembic migrations.
- The backend imports cleanly with document/KB/e-sign models and routes.
- `documents`, `knowledge_base`, and `esign` permissions are registered and seeded idempotently.
- Knowledge-base create/update/delete/publish operations require dedicated permissions.
- E-sign create/list/admin/sign/decline flows enforce dedicated permission and signer/requester rules.
- Documents enforce status lifecycle, version immutability, approval/archive rules, and scoped access where available.
- File metadata has checksum/storage governance fields and secure download/upload behavior is documented or implemented according to scope.
- Frontend nav/pages use dedicated permissions and shared auth/API helpers.
- Focused tests cover document lifecycle, KB permission contract, e-sign signer rules, migration ownership, and frontend permission wiring where tooling supports it.
- Documentation explains document-control workflow, knowledge-base workflow, e-signature workflow, permissions/scopes, tests, and known limitations.
