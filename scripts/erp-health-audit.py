#!/usr/bin/env python3
"""
ERP Health Audit Script — repeatable automation.

Usage:
    python scripts/erp-health-audit.py [--root PATH] [--output PATH]

Scans the codebase for known anti-patterns and writes a Markdown report.
Exit code 0 = no findings; 1 = findings present.
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

ROOT_DEFAULT = Path(__file__).resolve().parent.parent
OUTPUT_DEFAULT = ROOT_DEFAULT / "docs" / "AUTOMATED_HEALTH_AUDIT.md"


@dataclass
class Finding:
    severity: str  # HIGH | MEDIUM | LOW | INFO
    category: str
    file: str
    line: Optional[int]
    message: str


findings: List[Finding] = []


def find(severity: str, category: str, file: str, line: Optional[int], msg: str) -> None:
    findings.append(Finding(severity, category, file, line, msg))


# ── helpers ───────────────────────────────────────────────────────────────────

_SKIP_DIRS = {".venv", "venv", "__pycache__", ".git", "node_modules", ".next", ".claude"}


def iter_py(root: Path):
    for p in root.rglob("*.py"):
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        yield p


def iter_ts(root: Path):
    for p in root.rglob("*.tsx"):
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        yield p
    for p in root.rglob("*.ts"):
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        yield p


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


# ── checks ────────────────────────────────────────────────────────────────────

_UNBOUNDED_SKIP_PATTERNS = [
    # Loading objects by a provided ID list — bounded by caller
    re.compile(r"\.in_\("),
    # for-loop consumption — bulk expire/delete, bounded by parent key
    re.compile(r"^\s*for\s+\w+\s+in\s+result\.scalars\(\)\.all\(\)"),
]

# Specific file-suffix + context patterns proven to be FK-bounded internal ops.
# Format: (relative_path_suffix, line_context_pattern)
# A finding is suppressed if the file path ends with the suffix AND the surrounding
# 10-line window matches the context pattern.
_KNOWN_FP_CONTEXTS = [
    # seed.py — startup initialization, not a user-facing query
    (os.path.join("app", "db", "seed.py"), None),
    # production_advanced.py schedule conflict check — bounded by time window condition
    (os.path.join("crud", "production_advanced.py"), re.compile(r"exclude_id|check_schedule|overlap")),
    # chemical_treatment.py KPI aggregation — internal, bounded by conditions
    (os.path.join("crud", "chemical_treatment.py"), re.compile(r"KPI|low_stock|kpi")),
    # FK-bounded lookup functions in logistics/logs
    (os.path.join("crud", "logistics.py"), re.compile(r"shipment_id\s*==|po_link|customs_doc|local_cost")),
    # logs.py: mpesa status history is FK-scoped to a single transaction
    (os.path.join("crud", "logs.py"), re.compile(r"transaction_id\s*==|MpesaStatus|status_history")),
    # Internal tax batch update
    (os.path.join("crud", "tax_regulatory.py"), re.compile(r"POSTED|mark_taxes|batch_update")),
    # procurement.py: internal payment recalc bounded by po.id FK
    (os.path.join("crud", "procurement.py"), re.compile(r"po\.id|payment_status|total_paid|Recalculate")),
    # two_factor: per-user ops bounded by user_id
    (os.path.join("crud", "two_factor.py"), re.compile(r"user_id\s*==|recovery_code|TwoFASession")),

    # ── C.2 Service-layer confirmed false positives (2026-06-01) ─────────────
    # Each entry is narrow: file suffix + discriminating context regex.
    # NOT suppressed: bank_reconciliation_service, invoice_match_service,
    #   report_builder_service (C.3 chunking), webhook_service, promotions_service
    #   (C.4 product decision), ess_service.list_accounts_raw (C.3 chunking).

    # Group A — FK-bounded inner queries
    # recall_service: contain_recall, list_actions, build_customer_impact — recall_id FK
    (os.path.join("services", "recall_service.py"),
     re.compile(r"recall_id\s*==")),
    # sales_service: allocate_so, _release_so_allocation, pick_line, create_invoice —
    #   so_id / shipment_id FK; Stock ops use with_for_update; flag_overdue_invoices —
    #   operational full-scan bounded by overdue status + date; get_customer_statement —
    #   customer_id FK
    (os.path.join("services", "sales_service.py"),
     re.compile(r"so_id\s*==|SOLine|with_for_update|shipment_id\s*==|customer_id\s*==|OVERDUE|flag_overdue")),
    # timesheets_service: add_line, update_line, delete_line, auto_fill_from_attendance —
    #   timesheet_id FK; get_payroll_input — bounded by period dates;
    #   get_dashboard, report_summary — analytics aggregation
    (os.path.join("services", "timesheets_service.py"),
     re.compile(r"timesheet_id\s*==|get_payroll_input|get_dashboard|report_summary")),
    # bom_costing_service: cost_bom inner line fetch, compare_bom_versions — bom_id FK
    (os.path.join("services", "bom_costing_service.py"),
     re.compile(r"bom_id\s*==|AdvancedBOMLine")),
    # wms_service: inner pick/put-away line queries — zone_id / warehouse_id / task_id FK;
    #   Stock hold/release ops use with_for_update
    (os.path.join("services", "wms_service.py"),
     re.compile(r"with_for_update|zone_id\s*==|warehouse_id\s*==|task_id\s*==")),
    # notifications_service: list_preferences — user_id FK, ~8 rows per user
    (os.path.join("services", "notifications_service.py"),
     re.compile(r"user_id\s*==|list_preferences")),
    # ess_service: get_leave_balances, list_documents, mark_all_read — employee_id FK;
    #   list_attendance — employee_id FK (window offset means attendance_date in window);
    #   list_leave_types — small config; run_hr_support_assistant — AI agent (ESSRequest);
    #   DELIBERATELY EXCLUDED: list_accounts_raw (C.3 chunking candidate)
    (os.path.join("services", "ess_service.py"),
     re.compile(r"employee_id\s*==|list_leave_types|ESSAttendanceRecord|ESSRequest")),

    # Group B — Computation engines (limiting would silently corrupt results)
    # procurement_suggestion_service: engine checks ALL active materials vs safety stock /
    #   reorder point; suggestion lines / groups / AI recs are FK-bounded by run_id
    (os.path.join("services", "procurement_suggestion_service.py"),
     re.compile(r"MRPSuggestion|SupplierItemPrice|material_id|reorder_point|safety_stock"
                r"|ProcurementSuggestion|run_id\s*==|is_active")),
    # payroll_ke_service: calculate_payroll_run — must process ALL active employees;
    #   paye/nhif/nssf/payroll_summary reports — run_id FK-bounded;
    #   _get_tax_bands / _get_nhif_tiers — small config filtered by tax_year + is_active;
    #   ai_compliance_monitor — scans all active payroll profiles
    (os.path.join("services", "payroll_ke_service.py"),
     re.compile(r"KeTaxBand|KeNhifTier|EmployeePayrollProfile|run_id\s*==|KePayrollLine")),
    # mps_service: get_mps_lines, release_to_production — mps_id FK;
    #   MRP result integration — mrp_run_id FK
    (os.path.join("services", "mps_service.py"),
     re.compile(r"mps_id\s*==|mrp_run_id\s*==")),
    # mrp_service: planning engine must load ALL active products to check reorder points
    (os.path.join("services", "mrp_service.py"),
     re.compile(r"_build_incoming|_build_material_stock|reorder_point")),
    # shop_floor_service: get_active_sessions, get_active_downtimes —
    #   scheduling engine needs full open set of active sessions / downtimes
    (os.path.join("services", "shop_floor_service.py"),
     re.compile(r"get_active_sessions|get_active_downtimes|SFSession|SFDowntimeLog")),

    # Group C — Regulatory / operational full-scan (must be complete by law or FEFO)
    # shelf_life_service: list_near_expiry, list_expired, rank_lots_fefo — FEFO must rank
    #   ALL lots; expiry scan must be complete; config tables (list_item_configs,
    #   list_picking_strategies, list_customer_rules) are small seeded reference data
    (os.path.join("services", "shelf_life_service.py"),
     re.compile(r"ShelfLife|near_expiry|list_expired|rank_lots_fefo|LotShelfLifeProfile|fefo|FEFO")),
    # bom_compliance_service: compute_compliance_summary — must check ALL BOM components
    #   for allergen roll-up and regulatory compliance; bom_id FK
    (os.path.join("services", "bom_compliance_service.py"),
     re.compile(r"bom_id\s*==|compute_compliance_summary|AdvancedBOMLine")),

    # Group D — Small config / static tables (bounded by design; seeded reference data)
    # appraisals_service: list_periods, list_templates — HR config tables;
    #   get_dashboard, report_* — analytics aggregation across appraisal records;
    #   run_* — AI insight agents (read-only, bounded by period/template scope)
    (os.path.join("services", "appraisals_service.py"),
     re.compile(r"list_periods|list_templates|get_dashboard|report_completion"
                r"|report_rating_distribution|report_promotions"
                r"|run_performance_insight|run_calibration_risk|run_development_plan_agent")),
    # training_service: list_skills, list_programs — training catalog config;
    #   get_program_effectiveness — training_id FK; get_dashboard, report_completion,
    #   report_certification_expiry, run_compliance_risk_monitor — analytics/compliance
    (os.path.join("services", "training_service.py"),
     re.compile(r"list_skills|list_programs|training_id\s*==|get_dashboard"
                r"|report_completion|report_certification_expiry|run_compliance_risk_monitor")),
    # recruitment_service: list_stages — 11 seeded pipeline stages (static config)
    (os.path.join("services", "recruitment_service.py"),
     re.compile(r"list_stages|RecruitmentStage")),
    # expenses_service: list_categories, list_policies — small config filtered by active_flag
    (os.path.join("services", "expenses_service.py"),
     re.compile(r"list_categories|list_policies|ExpenseCategory|ExpensePolicy")),

    # Group D+E — Config tables + analytics (dimensions module)
    # dimensions_service: list_dim_types, list_cost_centers, list_validation_rules,
    #   list_allocation_rules, list_default_rules — reference config tables;
    #   get_transaction_dimensions, derive_dimensions, validate_dimensions —
    #   FK-bounded by transaction_type / dim_type_id;
    #   run_ai_agents — analytics agents (4 findings)
    (os.path.join("services", "dimensions_service.py"),
     re.compile(r"list_dim_types|list_cost_centers|list_validation_rules"
                r"|list_allocation_rules|list_default_rules|run_ai_agents"
                r"|transaction_type\s*==|dim_type_id\s*==")),
]


def _is_known_fp(filepath: str, window_text: str) -> bool:
    for suffix, ctx_re in _KNOWN_FP_CONTEXTS:
        if filepath.replace("/", os.sep).endswith(suffix):
            if ctx_re is None or ctx_re.search(window_text):
                return True
    return False


def check_unbounded_queries(root: Path) -> None:
    pattern = re.compile(r"\.scalars\(\)\.all\(\)")
    limit_pattern = re.compile(r"\.limit\(")
    in_pattern = re.compile(r"\.in_\(")
    for_consume = re.compile(r"^\s*for\s+\w+\s+in\s+")
    crud_dir = root / "backend" / "app" / "crud"
    for p in iter_py(root / "backend"):
        text = read(p)
        lines = text.splitlines()
        is_crud = crud_dir in p.parents or p.parent == crud_dir
        for i, line in enumerate(lines, 1):
            if not pattern.search(line):
                continue
            window = lines[max(0, i - 8):i + 5]
            window_text = "\n".join(window)
            # Skip if .limit( already nearby
            if any(limit_pattern.search(w) for w in window):
                continue
            # Skip if bounded by .in_() — loading by provided IDs
            if any(in_pattern.search(w) for w in window):
                continue
            # Skip for-loop consumption (bulk update/delete)
            if for_consume.search(line) or for_consume.search(lines[max(0, i - 2)]):
                continue
            # Skip known false-positive contexts
            if _is_known_fp(str(p), window_text):
                continue
            sev = "HIGH" if is_crud else "MEDIUM"
            find(sev, "unbounded_query", str(p), i,
                 ".scalars().all() without .limit() nearby")


def check_for_update_locks(root: Path) -> None:
    pattern = re.compile(r"\.with_for_update\(\)")
    for p in iter_py(root / "backend"):
        text = read(p)
        for i, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                find("MEDIUM", "row_lock", str(p), i,
                     "with_for_update() — verify atomic SQL UPDATE is not feasible")


def check_pool_settings(root: Path) -> None:
    session_py = root / "backend" / "app" / "db" / "session.py"
    if session_py.exists():
        text = read(session_py)
        if "pool_size" not in text:
            find("HIGH", "db_pool", str(session_py), None,
                 "Missing pool_size in engine configuration")
        if "pool_pre_ping" not in text:
            find("MEDIUM", "db_pool", str(session_py), None,
                 "Missing pool_pre_ping in engine configuration")
    else:
        find("HIGH", "db_pool", str(session_py), None, "session.py not found")


def check_create_all(root: Path) -> None:
    # Only flag actual ORM create_all() calls, not permission code strings
    pattern = re.compile(r"\.create_all\s*\(")
    for p in iter_py(root / "backend"):
        # Skip test files — they legitimately use create_all for test DBs
        if "test" in p.name.lower() or "test" in str(p.parent).lower():
            continue
        text = read(p)
        if "development" in text or "ENVIRONMENT" in text:
            continue  # file has an environment guard somewhere
        for i, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                find("HIGH", "create_all", str(p), i,
                     ".create_all() call with no ENVIRONMENT guard in this file")


def check_dev_server_in_prod_dockerfile(root: Path) -> None:
    for name in ("Dockerfile.prod", "Dockerfile"):
        for dockerfile in root.rglob(name):
            if any(part in _SKIP_DIRS for part in dockerfile.parts):
                continue
            text = read(dockerfile)
            if "--reload" in text:
                find("HIGH", "prod_dockerfile", str(dockerfile), None,
                     "--reload flag found in production Dockerfile")
            if "npm run dev" in text:
                find("HIGH", "prod_dockerfile", str(dockerfile), None,
                     "npm run dev found in production Dockerfile")


def check_localstorage_token(root: Path) -> None:
    dangerous = re.compile(r"localStorage\.(setItem|getItem)\s*\(\s*['\"](?:access_token|refresh_token|jwt|token)['\"]")
    for p in iter_ts(root / "frontend"):
        text = read(p)
        for i, line in enumerate(text.splitlines(), 1):
            if dangerous.search(line):
                find("HIGH", "token_storage", str(p), i,
                     "Auth token stored in localStorage — use HttpOnly cookies instead")


def check_missing_resource_limits(root: Path) -> None:
    for name in ("docker-compose.yml", "docker-compose.prod.yml"):
        p = root / name
        if not p.exists():
            continue
        text = read(p)
        if "resources" not in text or "limits" not in text:
            find("MEDIUM", "docker_limits", str(p), None,
                 "No resource limits found in Docker Compose file")


def check_health_endpoint_caching(root: Path) -> None:
    main_py = root / "backend" / "app" / "main.py"
    if main_py.exists():
        text = read(main_py)
        if "/health" in text and "_db_health_cache" not in text:
            find("MEDIUM", "health_check", str(main_py), None,
                 "/health opens DB on every call — add caching (_db_health_cache pattern)")
        if "/live" not in text:
            find("LOW", "health_check", str(main_py), None,
                 "Missing /live liveness probe endpoint")


def check_env_file_mismatch(root: Path) -> None:
    examples = list(root.glob(".env.*.example"))
    for ex in examples:
        real = root / ex.name.replace(".example", "")
        if not real.exists():
            find("INFO", "env_files", str(ex), None,
                 f"Example env file has no corresponding {real.name} — copy and fill it")


def check_secret_key_default(root: Path) -> None:
    config_py = root / "backend" / "app" / "core" / "config.py"
    if config_py.exists():
        text = read(config_py)
        if '"changeme"' in text or "'changeme'" in text:
            # Only flag if there's no production guard
            if "_production_guards" not in text:
                find("HIGH", "security", str(config_py), None,
                     "Default SECRET_KEY 'changeme' with no production guard")


# ── run all checks ────────────────────────────────────────────────────────────

def run_audit(root: Path) -> None:
    check_pool_settings(root)
    check_unbounded_queries(root)
    check_for_update_locks(root)
    check_create_all(root)
    check_dev_server_in_prod_dockerfile(root)
    check_localstorage_token(root)
    check_missing_resource_limits(root)
    check_health_endpoint_caching(root)
    check_env_file_mismatch(root)
    check_secret_key_default(root)


# ── report ────────────────────────────────────────────────────────────────────

def write_report(output: Path) -> None:
    from datetime import datetime, timezone
    lines = [
        "# Automated ERP Health Audit",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]

    by_severity = {"HIGH": [], "MEDIUM": [], "LOW": [], "INFO": []}
    for f in findings:
        by_severity.get(f.severity, by_severity["INFO"]).append(f)

    totals = {k: len(v) for k, v in by_severity.items()}
    lines += [
        "## Summary",
        "",
        f"| Severity | Count |",
        f"|----------|-------|",
        f"| HIGH     | {totals['HIGH']} |",
        f"| MEDIUM   | {totals['MEDIUM']} |",
        f"| LOW      | {totals['LOW']} |",
        f"| INFO     | {totals['INFO']} |",
        f"| **Total**| **{sum(totals.values())}** |",
        "",
    ]

    for sev in ("HIGH", "MEDIUM", "LOW", "INFO"):
        items = by_severity[sev]
        if not items:
            continue
        lines.append(f"## {sev} ({len(items)})")
        lines.append("")
        for f in items:
            loc = f"{f.file}:{f.line}" if f.line else f.file
            lines.append(f"- **[{f.category}]** `{loc}` — {f.message}")
        lines.append("")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description="ERP Health Audit")
    parser.add_argument("--root", default=str(ROOT_DEFAULT))
    parser.add_argument("--output", default=str(OUTPUT_DEFAULT))
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output = Path(args.output).resolve()

    print(f"Auditing {root} ...")
    run_audit(root)
    write_report(output)

    highs = sum(1 for f in findings if f.severity == "HIGH")
    print(f"Found {len(findings)} findings ({highs} HIGH)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
