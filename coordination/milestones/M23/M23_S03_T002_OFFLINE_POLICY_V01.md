# M23.S03.T002 — Shop-floor offline policy

## Decision

The initial virtual Shop Floor release is **online-only** for both live work-order reads and all authoritative execution writes. It does not promise offline production operation.

When connectivity is lost:

- Do not start, pause, resume, complete, consume materials, record QC/scrap/downtime, or append notes from an offline queue.
- Do not present cached queue/session data as current, and do not display a success state until the server confirms the write.
- Preserve unsent form input in the current view when practical, but do not persist it as an authoritative or replayable production record.
- After reconnecting, refresh the selected work order and operation, revalidate the authenticated session and permissions, and reconcile the server state before enabling a retry.
- If a request may have reached the server before the connection failed, treat its outcome as unknown. Do not blindly replay it; the safe retry/idempotency task must make retries duplicate-safe, while the UI first refreshes authoritative state.

## Rationale and boundaries

The Shop Floor actions affect traceability, QC gates, consumed materials, and production completion. An offline queue would need conflict resolution, identity/session expiry rules, idempotency, and explicit operator feedback; the current M23 execution model does not define those guarantees. Online-only writes keep server authorization and transaction state authoritative without inventing an offline synchronization protocol.

This is a conservative product requirement for the virtual ERP, not a claim that a real factory network or device was evaluated. A future offline mode needs a separate task defining durable local storage, encryption, session expiry, conflict handling, operator identity, synchronization, and duplicate prevention before implementation.

## Follow-on

M23.S03.T003 must implement safe retry/idempotency consistent with this policy for ambiguous network outcomes. M23.S03.T004 must make connection/server failures and recovery state clear to the operator. M23.S04 validates these behaviors with the consolidated milestone suite and independent review.
