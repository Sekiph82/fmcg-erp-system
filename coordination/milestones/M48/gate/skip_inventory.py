"""M48.S01.T012 static skip inventory of backend/tests: skipif conditions, pytest.skip calls, importorskip, mark.skip, xfail.

Prints a markdown section (grouped by class and reason) to stdout. Used to (re)generate SKIP_INVENTORY.md at the gate SHA:
  python coordination/milestones/M48/gate/skip_inventory.py > coordination/milestones/M48/gate/skip_inventory_static.md
"""
from __future__ import annotations

import ast
import collections
import re
from pathlib import Path

TESTS = Path(__file__).resolve().parents[4] / "backend" / "tests"

SERVICE_RE = re.compile(r"SMTP_TEST_SERVER|SMTP\b|MQTT|BROKER|CLAMAV|REDIS_URL|MAILPIT")
DB_RE = re.compile(r"DISPOSABLE|M\d+[A-Z0-9_]*_DB\b|TASK_DB_ENV|DATABASE_URL|postgres|PostgreSQL|_LEGACY_|migration runner", re.I)
PLATFORM_RE = re.compile(r"sys\.platform|os\.name|platform\.|ffmpeg|shutil\.which|not installed", re.I)
PROVIDER_RE = re.compile(r"live|sandbox account|real account|credential|API_KEY|TOKEN", re.I)


def classify(text: str) -> str:
    if SERVICE_RE.search(text):
        return "SERVICE"
    if DB_RE.search(text):
        return "DB_FLAG"
    if PLATFORM_RE.search(text):
        return "PLATFORM"
    if PROVIDER_RE.search(text):
        return "PROVIDER_LIVE"
    return "UNEXPLAINED"


def _name(f: ast.AST) -> str:
    return ast.unparse(f) if isinstance(f, ast.AST) else ""


def scan(path: Path):
    src = path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(src)
    parents = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = _name(node.func)
        kind = None
        if fn.endswith("mark.skipif"):
            kind = "skipif"
        elif fn in ("pytest.skip", "skip"):
            kind = "skip"
        elif fn.endswith("importorskip"):
            kind = "importorskip"
        elif fn.endswith("mark.skip"):
            kind = "mark.skip"
        elif fn.endswith("mark.xfail") or fn == "pytest.xfail":
            kind = "xfail"
        if not kind:
            continue
        reason = next((ast.unparse(k.value) for k in node.keywords if k.arg == "reason"), "")
        cond = ""
        if kind in ("skipif", "xfail") and node.args:
            cond = ast.unparse(node.args[0])
        elif kind in ("skip", "mark.skip") and node.args:
            reason = reason or ast.unparse(node.args[0])
        elif kind == "importorskip" and node.args:
            reason = "module " + ast.unparse(node.args[0])
        if kind == "skip":  # condition = enclosing if-tests
            p, conds = parents.get(node), []
            while p is not None and not isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
                if isinstance(p, ast.If):
                    conds.append(ast.unparse(p.test))
                p = parents.get(p)
            cond = " and ".join(reversed(conds))
        yield {"file": path.name, "line": node.lineno, "kind": kind, "cond": cond, "reason": reason.strip("'\"")}


def main() -> None:
    rows = [r for p in sorted(TESTS.glob("*.py")) for r in scan(p)]
    groups: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for r in rows:
        cls = classify(r["cond"] + " " + r["reason"])
        key_reason = re.sub(r"M\d+(_S\d+)?(_T\d+[A-Z]?)?|M\d+\.S\d+\.T\d+", "<TASK>", r["reason"] or r["cond"])[:160]
        groups[(cls, key_reason)].append(r)
    by_cls = collections.Counter()
    for (cls, _), rs in groups.items():
        by_cls[cls] += len(rs)
    print(f"Static skip sites: {len(rows)} in {len({r['file'] for r in rows})} files. "
          + ", ".join(f"{k}={v}" for k, v in sorted(by_cls.items())))
    print()
    for cls in ("UNEXPLAINED", "PROVIDER_LIVE", "PLATFORM", "SERVICE", "DB_FLAG"):
        items = sorted(((k[1], v) for k, v in groups.items() if k[0] == cls), key=lambda kv: -len(kv[1]))
        if not items:
            continue
        print(f"### {cls} ({sum(len(v) for _, v in items)} sites)\n")
        print("| sites | files | reason (task ids normalised) | kinds | example |\n|---|---|---|---|---|")
        for reason, rs in items:
            files = sorted({r["file"] for r in rs})
            kinds = ",".join(sorted({r["kind"] for r in rs}))
            ex = f"{rs[0]['file']}:{rs[0]['line']} `{(rs[0]['cond'] or '-')[:90]}`".replace("|", "/")
            print(f"| {len(rs)} | {len(files)} | {reason.replace('|', '/')} | {kinds} | {ex} |")
        print()


if __name__ == "__main__":
    main()
