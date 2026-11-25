# M43 gate — step 6: independent review and remediation (2026-11-25)

## Who reviewed and how

- Reviewer: a separate read-only reviewer agent (`feature-dev:code-reviewer`) that did not write the code.
- Scope: the M43 diff since `6bd7314`, covering public endpoints, OAuth, RBAC/scope, data integrity, consent and privacy.
- Method: static reading only; the reviewer ran nothing.
- Verdict: **ACCEPT_WITH_FIXES**.

## Findings and what was done

| # | Severity | Finding | Remediation |
|---|---|---|---|
| 1 | High | A tracking opt-out for an address with no consent row created SUBSCRIBED (marketing consent) | The row is created as `NO_CONSENT`. Test: `test_tracking_optout_never_grants_marketing_consent` |
| 2 | High | PATCH consent withdrawal and the retention purge left transcript segments, insights and coaching clips | PATCH now routes through `withdraw_consent`; the purge clears segments and language and deletes insights |
| 3 | Medium | `convert_to_opportunity` skipped the stage approval gate | Approval check added on convert |
| 4 | Medium | One approval was reusable, and the deal value could be raised afterwards | Approvals are CONSUMED on the move and store `approved_value`. Raising the value in a gated stage needs a new approval. Test in `test_m43_s01_t014_routing_db.py` |
| 5 | Medium | The frequency cap ignored in-flight (SENDING) mail and unflushed claims | SENDING always counts; each claim is flushed before the next check |
| 6 | Medium | OAuth state was not bound to the browser, so a user could attach someone else's mailbox | HttpOnly SameSite=Lax cookie holding the state hash, set on start and required on callback |
| 7 | Medium | SSRF through a user-supplied recording URL; download not capped | Live egress resolves the host and refuses private, loopback, link-local and reserved addresses; streamed download with a 50 MB cap. Test: `test_live_mode_refuses_internal_addresses` |
| 8 | Medium | Handoff briefs and acknowledge ignored the record scope | Filtered and checked with `can_view_record` / `_scoped_record` |
| 9 | Medium | Split shares with more than 2 decimals rounded on storage; splits editable after win | `decimal_places=2` (test added); a won deal's split can be changed only by a CRM manager |
| 10 | Low | The 401 retry dropped extra headers (Graph sendMail) | Headers are read once before the loop |
| 11 | Low | Playbook numbers accepted NaN/Infinity; a bad mapped date gave a 500 | Finite and bounded numbers only; dates validated in `check_answers` |
| 12 | Low | `render_html` dropped text after a URL ending at a quote or bracket | The cut-off text is kept (checked) |
| 13 | Low | Quota PUT duplicate gave a 500; currency could change under existing snapshots; any rep could snapshot | 409 on duplicate; currency locked once history exists; snapshots for editors only |
| 14 | Low | `callback_ok` compared `str` (500 on non-ASCII); associations to non-record objects were unchecked; `send_time` was readable for any contact | Compared as bytes; company-wide rights plus existence check; limited to contacts the user e-mailed (or managers) |
| 15 | Low | Backfill used untrimmed lower(email); a long e-mail could abort the migration | `trim()` plus `left(..., 254)` |

## Deferred (recorded in TASKS.md as M44.S01.T014)

- Some foreign-key inputs give a 500 instead of a 422: team members, saved-view team, dialer ids, split user.
- The Africa's Talking callback secret travels in the URL query: the provider does not sign callbacks. Access-log redaction for that path.
- The migration downgrade is destructive by design; this is documented.

## Re-test after remediation

- Migration:
  - Downgrade and upgrade on the head DB: clean.
  - Seeded `20261124_0071` → head: 14/14 checks.
- M43 DB tests: 15/15 files, 60 tests.
- Backend suite: 1759 passed, 446 skipped.
- Engagement file re-run after fix #12: pass.
