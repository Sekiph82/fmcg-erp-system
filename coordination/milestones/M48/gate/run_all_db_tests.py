"""M48.S01.T012 runner: every DB-gated backend test file on its own fresh disposable PostgreSQL database.

For each backend/tests/test_*.py that is gated on a database environment flag
(<TASK>_DISPOSABLE_TEST_DATABASE, M43_S01_DB, M43_S00_T004_DB, M44_DB, M45_DB, M46_DB, M48_DB, ...):

  1. CREATE DATABASE <name> TEMPLATE <template> on the disposable container (default m48-gate-pg, 127.0.0.1:25432).
  2. Set exactly the environment the file needs. Legacy files get <FLAG>=1 and <FLAG>_NAME=<name>, where <name> is
     generated from the DB-name regex / startswith prefix hard-coded in that file and checked against every one of them.
     Guards are never weakened: a file whose guard cannot be satisfied is reported UNPARSABLE and not run.
  3. Run pytest (sequential, with a timeout), record the last summary line and the -rs skip reasons.
  4. Drop the database(s).

Files that need a local service (SMTP/Mailpit, MQTT, ClamAV, Redis) run only when the service env var is already set
in the runner's environment (the gate starts those containers); otherwise they are reported SERVICE_REQUIRED.
Files that need legacy data prep (downgrade, seed old-schema rows, upgrade) get the prep from their original
coordination/sessions/*.ps1 runners, reproduced in PREP below.

Usage (from anywhere):
  python coordination/milestones/M48/gate/run_all_db_tests.py --list
  python coordination/milestones/M48/gate/run_all_db_tests.py --template m48_tmpl [--only substr ...] [--timeout 900]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path

try:  # Python 3.11+
    import re._parser as sre_parse  # type: ignore[import-not-found]
    import re._constants as sre_c  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    import sre_parse  # type: ignore[no-redef]
    import sre_constants as sre_c  # type: ignore[no-redef]

REPO = Path(__file__).resolve().parents[4]
BACKEND = REPO / "backend"
TESTS = BACKEND / "tests"
OUT_DIR = Path(__file__).resolve().parent / "db_results"

CONTAINER = "m48-gate-pg"
HOST, PORT, USER = "127.0.0.1", 25432, "postgres"

LEGACY_FLAG_RE = re.compile(r"[\"']([A-Z][A-Z0-9_]*_DISPOSABLE_TEST_DATABASE)(?:_NAME)?[\"']")
NEW_FLAG_RE = re.compile(r"[\"'](M\d+[A-Z0-9_]*_DB)[\"']")
REGEX_LIT_RE = re.compile(r"r?([\"'])(\^?fmcg_[^\"'\n]*?)\1")
STARTSWITH_RE = re.compile(r"startswith\(\s*[\"'](fmcg_[a-z0-9_]+)[\"']")
URL_GATE_RE = re.compile(r"[\"']postgresql[\"'] not in str\(settings\.DATABASE_URL\)")
HELPER_IMPORT_RE =re.compile(r"^\s*(?:from|import)\s+(?:tests\.)?(\w+)", re.M)
REGEX_META = set("[]{}()\\+*?|")

# env var -> service it needs. A gated file referencing one is SERVICE_REQUIRED unless the var is set here.
SERVICES = {
    "SMTP_TEST_SERVER": "SMTP sink (Mailpit), e.g. 127.0.0.1:51025",
    "MQTT_TEST_BROKER_URL": "MQTT broker (Mosquitto), e.g. mqtt://127.0.0.1:51883",
    "CLAMAV_TEST_HOST": "ClamAV clamd, e.g. 127.0.0.1:53310",
    "REDIS_URL": "Redis",
}
OPTIONAL_SERVICES = {"MAILPIT_TEST_API"}  # passed through when set, never required on its own

# Files whose tests read rows created by a legacy migration prep (from coordination/sessions/*/run_*.ps1).
_LC_LEGACY_ROWS = """
INSERT INTO lc_headers (id, lc_no, reference_type, currency_code, exchange_rate, total_lc_amount_fc, total_lc_amount_base, allocation_method, status)
VALUES ('25000000-0000-0000-0000-000000000038', 'LC-{tag}-LEGACY', 'MANUAL', 'USD', 1, 25.125, 25.125, 'BY_VALUE', 'DRAFT');
INSERT INTO lc_lines (id, header_id, cost_type, amount_fc, currency_code, exchange_rate, amount_base, is_included_in_valuation)
VALUES ('25000000-0000-0000-0000-000000000039', '25000000-0000-0000-0000-000000000038', 'FREIGHT_SEA', 25.125, 'USD', 1, 25.125, TRUE);
"""
_LC_FX_SNAPSHOT = """
ALTER TABLE lc_headers ADD COLUMN exchange_rate_id UUID NULL;
ALTER TABLE lc_headers ADD COLUMN exchange_rate_date DATE NULL;
ALTER TABLE lc_headers ADD COLUMN exchange_rate_source VARCHAR(20) NULL;
COMMENT ON COLUMN lc_headers.exchange_rate_id IS 'Added by Alembic revision 20261029_0040; exact finance rate row used for this snapshot';
COMMENT ON COLUMN lc_headers.exchange_rate_date IS 'Added by Alembic revision 20261029_0040; effective rate date, null for legacy unknowns';
COMMENT ON COLUMN lc_headers.exchange_rate_source IS 'Added by Alembic revision 20261029_0040; source copied with the rate snapshot';
ALTER TABLE lc_headers ADD CONSTRAINT fk_lc_headers_exchange_rate_id_exchange_rates FOREIGN KEY (exchange_rate_id) REFERENCES exchange_rates(id) ON DELETE SET NULL;
ALTER TABLE lc_lines ADD COLUMN exchange_rate_id UUID NULL;
ALTER TABLE lc_lines ADD COLUMN exchange_rate_date DATE NULL;
ALTER TABLE lc_lines ADD COLUMN exchange_rate_source VARCHAR(20) NULL;
COMMENT ON COLUMN lc_lines.exchange_rate_id IS 'Added by Alembic revision 20261029_0040; exact finance rate row used for this snapshot';
COMMENT ON COLUMN lc_lines.exchange_rate_date IS 'Added by Alembic revision 20261029_0040; effective rate date, null for legacy unknowns';
COMMENT ON COLUMN lc_lines.exchange_rate_source IS 'Added by Alembic revision 20261029_0040; source copied with the rate snapshot';
ALTER TABLE lc_lines ADD CONSTRAINT fk_lc_lines_exchange_rate_id_exchange_rates FOREIGN KEY (exchange_rate_id) REFERENCES exchange_rates(id) ON DELETE SET NULL;
"""


def _prep_m31_s02_t002(name: str) -> tuple[str, str, dict]:
    import uuid
    def_id, code = str(uuid.uuid4()), f"test.m31.s02.t002.migrated.{name[-20:]}"
    schema = '{"type":"object","properties":{"status":{"type":"string"}},"required":["status"],"additionalProperties":false}'
    sql = ("INSERT INTO webhook_event_definitions (id, event_code, event_name, module, payload_schema, active_flag) "
           f"VALUES ('{def_id}', '{code}', 'Synthetic migrated definition', 'testing', '{schema}'::jsonb, true);")
    return "20261029_0043", sql, {"M31_S02_T002_LEGACY_DEFINITION_ID": def_id, "M31_S02_T002_LEGACY_EVENT_CODE": code}


# file -> fn(db_name) -> (downgrade revision, SQL run at that revision, extra env); then `alembic upgrade head`.
PREP = {
    "test_m25_s02_t003_landed_cost_actuals.py": lambda n: (
        "20261029_0038",
        _LC_LEGACY_ROWS.format(tag="T003")
        + "DROP TABLE IF EXISTS lc_line_actuals;\nALTER TABLE lc_lines DROP COLUMN IF EXISTS estimated_amount_fc;\n",
        {}),
    "test_m25_s02_t004_currency_rates.py": lambda n: (
        "20261029_0038", _LC_FX_SNAPSHOT + _LC_LEGACY_ROWS.format(tag="T004"), {}),
    "test_m31_s02_t002_event_schema_governance_db.py": _prep_m31_s02_t002,
}


# ---------------------------------------------------------------- discovery
def _helper_flags() -> dict[str, set[str]]:
    """Flags declared in non-test helper modules under tests/ (e.g. m48_ads_support.DB)."""
    out = {}
    for p in TESTS.glob("*.py"):
        if not p.name.startswith("test_"):
            t = p.read_text(encoding="utf-8", errors="replace")
            flags = set(NEW_FLAG_RE.findall(t)) | set(LEGACY_FLAG_RE.findall(t))
            if flags:
                out[p.stem] = flags
    return out


def _regex_candidates(text: str) -> list[str]:
    return sorted({r for _, r in REGEX_LIT_RE.findall(text) if REGEX_META & set(r)})


def _gen(tree) -> str:
    out = []
    for op, av in tree:
        if op is sre_c.LITERAL:
            out.append(chr(av))
        elif op is sre_c.IN:
            chars = []
            for iop, iav in av:
                if iop is sre_c.LITERAL:
                    chars.append(chr(iav))
                elif iop is sre_c.RANGE:
                    chars.extend(chr(c) for c in range(iav[0], iav[1] + 1))
                elif iop is sre_c.CATEGORY:
                    chars.append("0" if "DIGIT" in str(iav) else "a")
                else:
                    raise ValueError(f"unsupported class item {iop}")
            out.append(random.choice(chars))
        elif op in (sre_c.MAX_REPEAT, sre_c.MIN_REPEAT):
            lo, hi, sub = av
            n = max(lo, 6) if hi is sre_c.MAXREPEAT else min(hi, max(lo, 24))
            out.append("".join(_gen(sub) for _ in range(n)))
        elif op is sre_c.SUBPATTERN:
            out.append(_gen(av[-1]))
        elif op is sre_c.BRANCH:
            out.append(_gen(av[1][0]))
        elif op is sre_c.AT:
            pass
        elif op is sre_c.ANY:
            out.append("a")
        elif op is sre_c.CATEGORY:
            out.append("0" if "DIGIT" in str(av) else "a")
        else:
            raise ValueError(f"unsupported regex op {op}")
    return "".join(out)


def make_name(regexes: list[str], prefixes: list[str]) -> str:
    """A DB name that fullmatches every regex and starts with every prefix the file hard-codes; raises otherwise."""
    seeds = ([_gen(sre_parse.parse(r)) for r in regexes] or [p + "%024x" % random.getrandbits(96) for p in prefixes]
             or ["m48r_" + "%020x" % random.getrandbits(80)])          # flag-only guard (no name rule in the file)
    for cand in seeds:
        if (all(re.fullmatch(r, cand) for r in regexes) and all(cand.startswith(p) for p in prefixes)
                and len(cand) <= 63 and re.fullmatch(r"[a-z0-9_]+", cand)):
            return cand
    raise ValueError(f"no name satisfies regexes={regexes} prefixes={prefixes}")


def discover() -> list[dict]:
    helpers = _helper_flags()
    plans = []
    for p in sorted(TESTS.glob("test_*.py")):
        text = p.read_text(encoding="utf-8", errors="replace")
        legacy = set(LEGACY_FLAG_RE.findall(text))
        new = set(NEW_FLAG_RE.findall(text))
        for mod in HELPER_IMPORT_RE.findall(text):
            for f in helpers.get(mod, ()):
                (legacy if f.endswith("_DISPOSABLE_TEST_DATABASE") else new).add(f)
        url_gated = bool(URL_GATE_RE.search(text))  # skips unless DATABASE_URL is PostgreSQL (M20 files)
        if not (legacy or new or url_gated):
            continue
        plan = {"file": p.name, "flags": sorted(legacy | new) or ["DATABASE_URL=postgresql"],"legacy_flags": sorted(legacy), "db_name": None,
                "needs_db2": "M45_DB2_URL" in text, "prep": p.name in PREP,
                "services": sorted(v for v in SERVICES if v in text), "class": "RUN", "note": ""}
        if legacy:
            regexes, prefixes = _regex_candidates(text), sorted(set(STARTSWITH_RE.findall(text)))
            try:
                plan["db_name"] = make_name(regexes, prefixes)
            except ValueError as exc:
                plan["class"], plan["note"] = "UNPARSABLE", str(exc)
            plan["name_rule"] = {"regexes": regexes, "startswith": prefixes}
        else:
            plan["db_name"] = "m48r_" + "%020x" % random.getrandbits(80)
        if plan["class"] == "RUN" and plan["services"]:
            plan["class"] = "SERVICE_REQUIRED"
            plan["note"] = "; ".join(f"{v}: {SERVICES[v]}" for v in plan["services"])
        if plan["prep"]:
            plan["note"] = (plan["note"] + "; " if plan["note"] else "") + "legacy prep: downgrade/seed/upgrade"
        plans.append(plan)
    return plans


# ---------------------------------------------------------------- execution
def psql(sql: str, db: str = "postgres") -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "exec", "-i", CONTAINER, "psql", "-U", USER, "-d", db, "-v", "ON_ERROR_STOP=1", "-q"],
                          input=sql, capture_output=True, text=True, timeout=300)


def url(db: str) -> str:
    return f"postgresql+asyncpg://{USER}@{HOST}:{PORT}/{db}"


def child_env(extra: dict) -> dict:
    env = {k: v for k, v in os.environ.items()
           if not (k == "DATABASE_URL" or "DISPOSABLE_TEST_DATABASE" in k or re.fullmatch(r"M\d+[A-Z0-9_]*_DB(2_URL)?", k)
                   or "_LEGACY_" in k)}
    env.update(extra)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _alembic(args: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "alembic", *args], cwd=BACKEND, env=env,
                          capture_output=True, text=True, timeout=900)


def summarize(out: str) -> tuple[str, dict]:
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    summary = next((ln for ln in reversed(lines)
                    if re.search(r"\b(passed|failed|skipped|error|errors|deselected|no tests ran)\b", ln)), lines[-1] if lines else "")
    counts = {k: int(n) for n, k in re.findall(r"(\d+) (passed|failed|skipped|errors?|xfailed|xpassed)", summary)}
    return summary.strip("= "), counts


def run_one(plan: dict, template: str, timeout: int) -> dict:
    res = dict(plan)
    svc_missing = [v for v in plan["services"] if not os.environ.get(v)]
    if plan["class"] == "UNPARSABLE" or svc_missing:
        res["status"] = plan["class"] if plan["class"] == "UNPARSABLE" else "SERVICE_REQUIRED"
        res["summary"] = ""
        return res
    name = plan["db_name"]
    dbs = [name] + ([name + "_dw"] if plan["needs_db2"] else [])
    env_extra = {"DATABASE_URL": url(name)}
    for f in plan["flags"]:
        if "=" not in f:
            env_extra[f] = "1"
    for f in plan["legacy_flags"]:
        env_extra[f + "_NAME"] = name
    if plan["needs_db2"]:
        env_extra["M45_DB2_URL"] = url(dbs[1])
    try:
        for db in dbs:
            r = psql(f'CREATE DATABASE "{db}" TEMPLATE "{template}";')
            if r.returncode:
                raise RuntimeError(f"create {db}: {r.stderr.strip()}")
        env = child_env(env_extra)
        if plan["prep"]:
            rev, sql, extra = PREP[plan["file"]](name)
            for step, ok in (("downgrade", _alembic(["downgrade", rev], env)),):
                if ok.returncode:
                    raise RuntimeError(f"prep {step} {rev} failed: {(ok.stderr or ok.stdout).strip()[-1500:]}")
            r = psql(sql, name)
            if r.returncode:
                raise RuntimeError(f"prep SQL failed: {r.stderr.strip()[-1500:]}")
            up = _alembic(["upgrade", "head"], env)
            if up.returncode:
                raise RuntimeError(f"prep upgrade head failed: {(up.stderr or up.stdout).strip()[-1500:]}")
            env.update(extra)
        try:
            p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rs", "--tb=short",
                                f"tests/{plan['file']}"], cwd=BACKEND, env=env, capture_output=True, text=True,
                               timeout=timeout, encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            res.update(status="TIMEOUT", summary=f"timeout after {timeout}s", rc=None)
            return res
        out = p.stdout + p.stderr
        res["summary"], res["counts"] = summarize(out)
        res["rc"] = p.returncode
        res["skip_reasons"] = [ln.strip() for ln in out.splitlines() if ln.startswith("SKIPPED")]
        c = res["counts"]
        if p.returncode == 0 and c.get("passed", 0) > 0:
            res["status"] = "PASS"
        elif p.returncode == 0:
            res["status"] = "SKIP"  # every test skipped: the guard was not satisfied, investigate
        else:
            res["status"] = "FAIL"
            res["tail"] = "\n".join(out.splitlines()[-60:])
    except Exception as exc:  # noqa: BLE001 - recorded per file, run continues
        res.update(status="ERROR", summary=str(exc)[:2000])
    finally:
        for db in dbs:
            psql(f'DROP DATABASE IF EXISTS "{db}" WITH (FORCE);')
    return res


def write_report(results: list[dict], template: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    totals: dict[str, int] = {}
    for r in results:
        totals[r["status"]] = totals.get(r["status"], 0) + 1
    tot_line = f"TOTAL files={len(results)} " + " ".join(f"{k}={v}" for k, v in sorted(totals.items()))
    (OUT_DIR / f"db_results_{stamp}.json").write_text(
        json.dumps({"sha": sha, "template": template, "totals": totals, "results": results}, indent=2), encoding="utf-8")
    md = [f"# DB-gated test run {stamp}", "", f"SHA `{sha}`, template `{template}`, container `{CONTAINER}`", "",
          "| file | flags | db name | status | summary / reason |", "|---|---|---|---|---|"]
    for r in results:
        why = r.get("summary") or r.get("note", "")
        md.append(f"| {r['file']} | {' '.join(r['flags'])} | {r.get('db_name') or ''} | {r['status']} | {why.replace('|', '/')} |")
    md += ["", tot_line, ""]
    path = OUT_DIR / f"db_results_{stamp}.md"
    path.write_text("\n".join(md), encoding="utf-8")
    print(tot_line)
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", default="m48_tmpl")
    ap.add_argument("--only", nargs="*", help="substring(s) of file names to run")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--list", action="store_true", help="print the discovered plan and exit")
    a = ap.parse_args()
    plans = discover()
    if a.only:
        plans = [p for p in plans if any(s in p["file"] for s in a.only)]
    if a.list:
        for p in plans:
            print(f"{p['class']:16} {p['file']:60} {' '.join(p['flags']):45} {p['db_name']} {p['note']}")
        print(f"{len(plans)} files")
        return 0
    results = []
    for i, p in enumerate(plans, 1):
        r = run_one(p, a.template, a.timeout)
        print(f"[{i}/{len(plans)}] {r['status']:16} {p['file']}: {r.get('summary') or r.get('note', '')}", flush=True)
        results.append(r)
    print("report:", write_report(results, a.template))
    return 0 if all(r["status"] == "PASS" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
