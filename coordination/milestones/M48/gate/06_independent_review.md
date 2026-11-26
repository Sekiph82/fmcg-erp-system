# M48 gate — independent review of candidate 933ffaf (2026-11-26)

**Reviewer:** independent code-review agent (feature-dev:code-reviewer). It worked read-only and saw the code only, not the implementers' conclusions.

**Verdict:** ACCEPT_WITH_FIXES.

## Findings and dispositions

1. **HIGH — card payments.** Unapproved LIVE Pesapal credentials still create real orders, which `_settle` then books as test money.
   - Fix: a LIVE config that is not approved must refuse checkout.
   - Owner: card agent.
2. **HIGH — ads.** Pausing a LIVE tree while live is gated off sends nothing to the provider but reports PAUSED.
   - Fix: force a real send, or refuse.
   - Owner: ads agent.
3. **MEDIUM — card payments.** An IPN inside the requery gap is acknowledged without verification, and there is no periodic re-query of PENDING payments.
   - Owner: card agent.
4. **MEDIUM — ads.** Reconcile resolves PENDING ledger rows that are still in flight, which allows a duplicate create.
   - Fix: grace period and root lock.
   - Owner: ads agent.
5. **MEDIUM — warehouse.** The two-admin approval is not independent of the person who set the secret, and LIVE hosts are not pinned to the official endpoints.
   - Owner: warehouse agent.
6. **MEDIUM — cycle count.** An auto-post failure strands the adjustment and blocks recounts, and concurrent duplicate scans can double-post.
   - Owner: remediation agent.
7. **LOW/MEDIUM — e-sign.** Envelope list, get and files ignore commercial record scope, and contract sends lack a scope check.
   - Owner: e-sign agent.
8. **LOW — inventory.** The transfer replay ignores the lot.
   - Owner: remediation agent.

Each fix needs its own regression test. Re-review of the fixes is recorded below once done.
- 7 FIXED: esign scope (visible_envelopes, 404 out-of-scope on get/files/reconcile/cancel, contract send scope); test_envelope_reads_and_contract_sends_respect_record_scope; 18 passed (t009 + gap012).
- 2 FIXED: a LIVE tree always uses real HTTP; a pause that cannot really be sent is refused 409 with no ledger row. 4 FIXED: CLAIM_GRACE 2 min before reconcile; per-tree advisory lock (released in finally) on submit/set_status/reconcile. Tests: 3 regressions in test_m48_s01_t001_meta_ads.py; 37 passed (M48 ads + M44 ads).
- 5 FIXED: secret_set_by column; approver must differ from creator and from whoever set the secret; a credential change resets approval; approved_hosts are re-checked at run time; LIVE hosts pinned to official Snowflake/BigQuery/Google token hosts (overrides only with egress=local); hosts shown in the approval UI. Tests: 22 passed (DB) + 20 passed / 4 skipped (no DB).
- 1 FIXED: unapproved LIVE credentials put the mode in BLOCKED; checkout returns 503, no order is sent; only SANDBOX is simulated; the pay page hides the card button unless the mode is LIVE or SIMULATED. 3 FIXED: an IPN inside the requery gap on a non-final payment gets 500 so Pesapal retries; poll_open in hub_tick settles PENDING/EXPIRED/INVALID payments and open refunds. Tests: 10 passed (t010) + 10 passed (M45/M46/M47 regressions).
- 6 FIXED: count entry, adjustment, stock and GL commit in one transaction (failure stores nothing); task row FOR UPDATE; approve/reject lock the entry row. 8 FIXED: transfer_replay compares the lot. Tests: 3 new; 9 M48 tests passed + 18/18 legacy files passed.

## Second independent review: 933ffaf..16b109c

**Verdict: ACCEPT_WITH_FIXES.** All 8 original findings are CLOSED, and T020 is correct.

New findings, all fixed in the gate:

- **N1 (medium-low):** the e-sign envelope list applied `limit(200)` before the scope filter.
  - Fix: page through the query until 200 visible envelopes are collected.
- **N2 (low):** if the ads `root_lock` unlock failed, a pooled connection could keep holding the advisory lock.
  - Fix: on failure the connection is invalidated, never returned to the pool.
- **Note → fixed:** cycle-count posting read the stock row without a lock, so concurrent adjustments could lose an update.
  - Fix: `_count_stock_rows(for_update=True)` on the posting path, `SELECT … FOR UPDATE` with `populate_existing`.

Regression after the fixes: m05_s03_t002 7, m05_s03_t003 5, m06_s03_t001 5, m48 t001 13, t009 11, t014 3, t018/t019 5 — all PASS (db_results_20261126_125300.md).

Owner note, which belongs to the activation register and is not a software defect: the TikTok minimum (USD 50, applied as 50 in account currency) equals the default `ADS_MAX_DAILY_BUDGET` of 50. The owner must raise the guardrail before real TikTok use.
