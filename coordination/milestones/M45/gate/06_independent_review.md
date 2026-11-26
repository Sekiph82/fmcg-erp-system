# M45 gate — step 6: independent review (2026-11-26)

- **Reviewer:** a separate code-review agent with read-only access. It did not see the implementer's conclusions.
- **Scope:** commits cf1468b..a6408e4 (M45.S01.T001–T024).
- **Verdict:** ACCEPT_WITH_FIXES. No unauthenticated data leak and no money-settlement hole were found.

## Findings and disposition

| # | Sev | Finding | Disposition |
|---|---|---|---|
| 1 | med | CPQ level approvals survived a later discount increase made through PATCH | **Fixed**: an approval counts only for the discount it approved. Stale approvals are dropped on re-approve. Regression test added (t014). |
| 2 | med | Impersonation had no privilege ceiling, and approvals were possible while impersonating | **Fixed**: the target's rights must be a subset of the actor's (unless superuser). CPQ level approval and AI-request decisions are refused while impersonating. Regression test added (t023). |
| 3 | med | SSO accepted a token without `email_verified` | **Fixed**: requires `email_verified is True`. Regression test added: missing claim refused (t016). |
| 4 | med | SSO: state not bound to the browser (login CSRF); privileged-2FA users could be locked out | **Fixed**: a state cookie is set at /sso/start and compared at the callback. Privileged-2FA accounts are refused via SSO with a clear message (they use break-glass password + TOTP). Regression test added: callback from another browser is refused. |
| 5 | med | Add-in lookup listed other reps' deals and activities | **Fixed**: only deals the user may see, and their activities. Regression test added (t012). |
| 6 | med | An unpinned sales-doc link served a newer CONFIDENTIAL version | **Fixed**: confidentiality is re-checked on the served version. Regression test added (t013). |
| 7 | med | A sales editor could run syncs that change credit limit, terms, KRA PIN and active flag | **Fixed**: those fields need crm.edit_all. Unit test added (t011). |
| 8 | med | Data-sync rollback overwrote later edits; Decimal phantom diffs | **Fixed**: a field is restored only if it is unchanged since the run; Decimals are normalised. |
| 9 | med | Two approvers racing on one AI request | **Fixed**: row lock in `decide`. |
| 10 | med | Concurrent warehouse runs of one job | **Fixed**: per-job advisory lock. A second run is SKIPPED. |
| 11 | low-med | PostgreSQL DSN `?host=` could bypass the egress check | **Fixed**: DSNs with query parameters are refused. |
| 12 | low | MCP batch size unbounded; LIKE wildcards; limit before filter | **Fixed**: max 20 messages per batch, escaped LIKE, filter before the cap. |
| 13 | low | Payment links: STK spam; LinkError treated as paid; GAVE_UP unreachable | **Fixed**: max 5 pushes per link per hour; billing marks PAID only when nothing is left; GAVE_UP reachable. Pending-attempt timeout → M46 carry-over. |
| 14 | low | Config bundle: non-unique natural keys → 500 | **Fixed**: first match, no crash. Workflow graphs may embed user ids → documented. |
| 15 | low | Daily job guard tied to the health snapshot | Deferred to M46 carry-over: a per-step daily ledger. |
| 16 | low | Data-sync webhook compare_digest TypeError on non-ASCII | **Fixed**: compare as bytes. |

After the fixes:
- All M45 DB-gated files pass (`02_db_tests_rerun.txt`, `02_db_tests_rerun2.txt`).
- The full backend suite passes: 1807 passed, 0 failed (`02_backend_suite_rerun.txt`).
