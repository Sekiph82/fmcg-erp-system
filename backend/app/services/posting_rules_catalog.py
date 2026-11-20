"""Proposed accounting rule set and the "mandatory once approved" switch (owner 2026-11-20).

Claude prepares the rule set; finance reviews it, changes any account on the Finance → Posting Rules screen and
approves it. Proposed rules are stored inactive (draft). Approving activates them and switches posting to
mandatory: from then on an event whose rule is missing is refused (422) instead of being saved without a ledger entry.
Before approval the old behaviour stays (event saved, "not booked" logged), so work never stops while finance reviews.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select

log = logging.getLogger(__name__)
MANDATORY_KEY = "finance.posting_rules_mandatory"
PROPOSED_NOTE = "PROPOSED by the system - review the accounts, then approve the rule set."

# (module, event, name, debit, credit, tax, clearing, what it books)  — account codes from the seeded chart
CATALOG: list[tuple[str, str, str, Optional[str], Optional[str], Optional[str], Optional[str], str]] = [
    ("sales", "SALES_INVOICE_ISSUED", "Sales invoice", "1100", "4100", "2200", None,
     "Customer owes us: Dr receivables, Cr sales revenue and VAT output."),
    ("sales", "CUSTOMER_PAYMENT_RECEIVED_CASH", "Customer payment - cash", None, "1100", None, "1020",
     "Cash received: Dr cash, Cr receivables."),
    ("sales", "CUSTOMER_PAYMENT_RECEIVED_BANK", "Customer payment - bank", None, "1100", None, "1010",
     "Bank transfer received (also marketplace payouts): Dr bank, Cr receivables."),
    ("sales", "CUSTOMER_PAYMENT_RECEIVED_MPESA", "Customer payment - M-Pesa", None, "1100", None, "1030",
     "M-Pesa received: Dr M-Pesa clearing, Cr receivables."),
    ("pos", "POS_SALE", "Counter (POS) sale", "1020", "4100", "2200", None,
     "Till takings: Dr cash/till, Cr sales revenue and VAT output; a void posts the reversal."),
    ("procurement", "PURCHASE_INVOICE_POSTED", "Supplier invoice", None, "2010", "1300", None,
     "Supplier invoice matched to goods received: Cr trade payables, Dr VAT input (goods side from the GRNI mapping)."),
    ("procurement", "SUPPLIER_PAYMENT_MADE", "Supplier payment", "2010", "1010", None, None,
     "Paying a supplier: Dr trade payables, Cr bank."),
    ("payroll", "PAYROLL_APPROVED", "Payroll (employee side)", "5600", "2300", "2310", None,
     "Approved payroll: Dr salaries (gross), Cr net pay payable and PAYE/SHIF/NSSF/housing levy payable."),
    ("payroll", "EMPLOYER_CONTRIBUTIONS", "Payroll (employer contributions)", "5610", "2330", None, None,
     "Employer's own NSSF, housing levy and NITA: Dr employer contributions expense, Cr contributions payable."),
    ("expenses", "EXPENSE_FINANCE_APPROVED", "Employee expense claim", "5700", "2320", None, None,
     "Approved claim: Dr operating expense, Cr owed to the employee."),
    ("inventory", "STOCK_ADJUSTMENT", "Stock count difference", "5410", "1220", None, None,
     "Count shortage: Dr shrinkage, Cr stock (a surplus is the reverse)."),
    ("production", "RAW_MATERIAL_ISSUE", "Production - raw materials", "1210", "1200", None, None,
     "Raw materials consumed: Dr work in progress, Cr raw-material stock."),
    ("production", "PACKAGING_ISSUE", "Production - packaging", "1210", "1230", None, None,
     "Packaging consumed: Dr work in progress, Cr packaging stock."),
    ("production", "SEMI_FINISHED_ISSUE", "Production - semi-finished goods", "1210", "1215", None, None,
     "Semi-finished goods consumed: Dr work in progress, Cr semi-finished stock."),
    ("production", "CONVERSION_APPLIED", "Production - labour, machine, energy", "1210", "5310", None, None,
     "Conversion cost into the product: Dr work in progress, Cr production overhead absorbed."),
    ("production", "FINISHED_GOODS_RECEIPT", "Production - finished goods", "1220", "1210", None, None,
     "Finished goods received: Dr finished-goods stock, Cr work in progress."),
]


async def is_mandatory(db) -> bool:
    from app.models.utilities import SystemConfig

    v = (await db.execute(select(SystemConfig.value).where(SystemConfig.key == MANDATORY_KEY))).scalar_one_or_none()
    return (v or "").lower() == "true"


async def missing_rule(db, module: str, event: str, what: str) -> None:
    """A posting rule is missing: refuse once finance has approved the rule set; until then save and log."""
    if await is_mandatory(db):
        raise HTTPException(422, f"No active accounting rule {module}/{event}: {what} cannot be booked. "
                                 "Finance must set the rule (Finance → Posting Rules) before this can be saved.")
    log.warning("%s saved without a ledger entry: no %s/%s rule (rule set not approved yet)", what, module, event)


async def _accounts(db) -> dict:
    from app.models.finance import ChartOfAccount

    return {a.code: a for a in (await db.execute(select(ChartOfAccount))).scalars()}


async def overview(db) -> dict:
    """Catalog rows with the stored rule (active or proposed), for the Posting Rules screen."""
    from app.models.finance import AccountingPostingRule

    rules = {}
    for r in (await db.execute(select(AccountingPostingRule).order_by(AccountingPostingRule.priority))).scalars():
        rules.setdefault((r.source_module, r.source_event), r)
    accounts = await _accounts(db)
    by_id = {a.id: a for a in accounts.values()}

    def acc(account_id):
        a = by_id.get(account_id)
        return {"id": str(a.id), "code": a.code, "name": a.name} if a else None

    rows = []
    for module, event, name, *_ , purpose in CATALOG:
        r = rules.get((module, event))
        rows.append({"module": module, "event": event, "name": name, "purpose": purpose,
                     "rule_id": str(r.id) if r else None,
                     "status": "missing" if r is None else ("active" if r.is_active else
                                                            "proposed" if (r.notes or "").startswith(PROPOSED_NOTE) else "inactive"),
                     "debit": acc(r.debit_account_id) if r else None, "credit": acc(r.credit_account_id) if r else None,
                     "tax": acc(r.tax_account_id) if r else None, "clearing": acc(r.clearing_account_id) if r else None})
    return {"mandatory": await is_mandatory(db), "rules": rows,
            "accounts": [{"id": str(a.id), "code": a.code, "name": a.name, "type": a.account_type.value}
                         for a in sorted(accounts.values(), key=lambda a: a.code) if not a.is_control]}


async def propose(db) -> int:
    """Write the catalog as inactive draft rules where no rule exists yet. Returns how many were proposed."""
    from app.models.finance import AccountingPostingRule

    accounts = await _accounts(db)
    have = {(r.source_module, r.source_event) for r in (await db.execute(select(AccountingPostingRule))).scalars()}
    n = 0
    for module, event, name, debit, credit, tax, clearing, purpose in CATALOG:
        if (module, event) in have:
            continue
        ids = {}
        for field, code in (("debit", debit), ("credit", credit), ("tax", tax), ("clearing", clearing)):
            if code is not None and code not in accounts:
                raise HTTPException(422, f"Account {code} is missing from the chart of accounts")
            ids[field] = accounts[code].id if code else None
        db.add(AccountingPostingRule(source_module=module, source_event=event, rule_name=name, is_active=False, priority=10,
                                     debit_account_id=ids["debit"], credit_account_id=ids["credit"],
                                     tax_account_id=ids["tax"], clearing_account_id=ids["clearing"],
                                     notes=f"{PROPOSED_NOTE} {purpose}"))
        n += 1
    await db.flush()
    return n


async def update_rule(db, rule_id, data: dict) -> None:
    from app.models.finance import AccountingPostingRule, ChartOfAccount

    rule = await db.get(AccountingPostingRule, rule_id)
    if rule is None:
        raise HTTPException(404, "Rule not found")
    for field in ("debit", "credit", "tax", "clearing"):
        if field in data:
            value = data[field]
            if value:
                acct = await db.get(ChartOfAccount, value)
                if acct is None or acct.is_control:
                    raise HTTPException(422, f"{field}: choose a posting (non-control) account")
            setattr(rule, f"{field}_account_id", value or None)
    await db.flush()


async def approve(db, user_id) -> int:
    """Finance approves the set: proposed rules become active and posting becomes mandatory."""
    from app.models.finance import AccountingPostingRule
    from app.models.utilities import ConfigCategory, SystemConfig

    rows = (await db.execute(select(AccountingPostingRule).where(AccountingPostingRule.is_active.is_(False),
                                                                 AccountingPostingRule.notes.like(f"{PROPOSED_NOTE}%")))).scalars().all()
    needed = {(m, e): {f for f, code in (("debit", d), ("credit", c), ("tax", t), ("clearing", k)) if code}
              for m, e, _n, d, c, t, k, _p in CATALOG}
    gaps = [f"{r.source_module}/{r.source_event}: {f}" for r in rows for f in sorted(needed.get((r.source_module, r.source_event), ()))
            if getattr(r, f"{f}_account_id") is None]
    if gaps:
        raise HTTPException(422, "Choose an account before approving: " + "; ".join(gaps))
    for r in rows:
        r.is_active = True
        r.notes = r.notes.replace(PROPOSED_NOTE, "Approved by finance.")
    cfg = (await db.execute(select(SystemConfig).where(SystemConfig.key == MANDATORY_KEY))).scalar_one_or_none()
    if cfg is None:
        cfg = SystemConfig(key=MANDATORY_KEY, category=ConfigCategory.FINANCE, is_editable=False,
                           description="Accounting rules are mandatory: events without a rule are refused")
        db.add(cfg)
    cfg.value, cfg.updated_by_id = "true", user_id
    await db.flush()
    return len(rows)
