"""M50.S01.T012 AI accuracy, evaluation and safety framework.

Versioned benchmark corpora (corpora/*.json, synthetic POVU data) are run through a pluggable task adapter and judged by
deterministic scorers (citation correctness, unsupported claims, data leakage, prompt injection, approval/consent,
abstention, locale, latency, cost). Everything runs offline; nothing here calls a paid model unless the `llm` adapter is
chosen and a provider is configured. Results are stored with the model/config identity and are labelled SYNTHETIC:
they say how a component behaves on this synthetic corpus, never how accurate it is in production. Real-world
calibration would be a different data_kind with its own field (real_calibration), which nothing here fills in.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Optional

from app.services.ai_eval.adapters import ADAPTERS
from app.services.ai_eval.scorers import SCORER_VERSION, score_case

CORPUS_DIR = Path(__file__).parent / "corpora"
DATA_KIND = "SYNTHETIC"


class EvalError(Exception):
    pass


def load_corpus(corpus_id: str) -> dict:
    p = CORPUS_DIR / f"{corpus_id}.json"
    if not corpus_id.isidentifier() or not p.is_file():
        raise EvalError(f"Unknown corpus {corpus_id!r}.")
    raw = p.read_bytes()
    c = json.loads(raw)
    c["sha256"] = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    return c


def list_corpora() -> list[dict]:
    out = []
    for p in sorted(CORPUS_DIR.glob("*.json")):
        c = load_corpus(p.stem)
        out.append({"corpus_id": c["corpus_id"], "version": c["version"], "data_kind": c.get("data_kind", DATA_KIND),
                    "description": c.get("description", ""), "cases": len(c["cases"]), "sha256": c["sha256"],
                    "tasks": sorted({x.get("task", "qa") for x in c["cases"]})})
    return out


def config_for(corpus: dict, adapter: str, params: Optional[dict] = None) -> dict:
    a = ADAPTERS[adapter]
    return {"adapter": adapter, "model_id": a["model_id"], "provider": a["provider"], "corpus_id": corpus["corpus_id"],
            "corpus_version": corpus["version"], "corpus_sha256": corpus["sha256"], "scorer_version": SCORER_VERSION,
            "temperature": 0, "seed": 0, "params": params or {}}


def config_hash(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()


def digest(results: list[dict]) -> str:
    """Reproducibility fingerprint: case ids, verdicts and per-scorer pass/fail (never timings of a real model)."""
    core = [[r["case_id"], r["passed"], {k: v["passed"] for k, v in sorted(r["scores"].items())}] for r in results]
    return hashlib.sha256(json.dumps(core).encode()).hexdigest()


async def evaluate(corpus: dict, adapter: str, ctx: Optional[dict] = None) -> dict:
    """Run every applicable case. Returns {"status": DONE|UNAVAILABLE, "note", "results", "skipped", "summary"}."""
    ctx = ctx or {}
    a = ADAPTERS.get(adapter)
    if a is None:
        raise EvalError(f"Unknown adapter {adapter!r}.")
    ok, why = a["available"](ctx)
    if not ok:
        return {"status": "UNAVAILABLE", "note": why, "results": [], "skipped": len(corpus["cases"]), "summary": {}}
    results, skipped = [], 0
    for case in corpus["cases"]:
        if a["tasks"] is not None and case.get("task", "qa") not in a["tasks"]:
            skipped += 1
            continue
        err = None
        try:
            out = await a["run"](case, ctx)
            scores = score_case(case, out)
        except Exception as e:      # an adapter failure is a failed case with the reason, not a crash of the whole run
            out, scores, err = {"text": "", "latency_ms": 0, "tokens": 0, "cost": 0}, {}, f"{type(e).__name__}: {e}"[:300]
        results.append({"case_id": case["id"], "passed": bool(scores) and all(s["passed"] for s in scores.values()),
                        "scores": scores, "expected": case.get("expect"), "actual": out, "error": err,
                        "latency_ms": int(out.get("latency_ms", 0)), "tokens": int(out.get("tokens", 0)), "cost": Decimal(str(out.get("cost", 0) or 0))})
    per: dict[str, dict] = {}
    for r in results:
        for k, s in r["scores"].items():
            d = per.setdefault(k, {"passed": 0, "total": 0})
            d["total"] += 1
            d["passed"] += int(s["passed"])
    return {"status": "DONE" if results else "UNAVAILABLE", "note": None if results else f"adapter {adapter} has no applicable case in {corpus['corpus_id']}",
            "results": results, "skipped": skipped,
            "summary": {"scorers": per, "passed_cases": sum(r["passed"] for r in results), "digest": digest(results), "skipped": skipped}}


def verify_corpus(corpus: dict) -> list[str]:
    """Scorer calibration on the corpus itself: every golden answer must pass all its scorers, and every adversarial output
    must fail exactly the scorers named in must_fail. Returns the problems (empty = the corpus and scorers agree)."""
    problems = []
    for case in corpus["cases"]:
        if "golden" in case:
            for name, s in score_case(case, _golden_out(case)).items():
                if not s["passed"]:
                    problems.append(f"{case['id']}: golden answer fails {name}: {s['detail']}")
        for adv in case.get("adversarial", []):
            got = {n for n, s in score_case(case, adv["output"]).items() if not s["passed"]}
            missing = set(adv["must_fail"]) - got
            if missing:
                problems.append(f"{case['id']}/{adv['name']}: scorer(s) {sorted(missing)} did not catch the bad output")
    return problems


def _golden_out(case: dict) -> dict:
    g = case["golden"]
    text = g["text"]
    return {"text": text, "citations": g.get("citations", []), "actions": g.get("actions", []), "abstained": g.get("abstained", False),
            "meta": g.get("meta") or {}, "latency_ms": 20 + len(text) // 2, "latency_source": "SIMULATED", "tokens": len(text) // 4, "cost": 0}


async def run_and_store(db, corpus_id: str, adapter: str, user: str, ctx: Optional[dict] = None, params: Optional[dict] = None):
    """Evaluate and persist a run (always labelled SYNTHETIC) with its model/config identity."""
    from app.models.m50_ai_platform import AIEvalCaseResult, AIEvalRun
    corpus = load_corpus(corpus_id)
    cfg = config_for(corpus, adapter, params)
    res = await evaluate(corpus, adapter, {**(ctx or {}), "db": (ctx or {}).get("db", None)})
    run = AIEvalRun(corpus_id=corpus["corpus_id"], corpus_version=corpus["version"], corpus_sha256=corpus["sha256"], adapter=adapter,
                    model_id=cfg["model_id"], provider=cfg["provider"], config=cfg, config_hash=config_hash(cfg), data_kind=DATA_KIND,
                    status=res["status"], total=len(res["results"]), passed=sum(r["passed"] for r in res["results"]),
                    summary=res["summary"], note=res["note"], created_by=user)
    db.add(run)
    await db.flush()
    for r in res["results"]:
        db.add(AIEvalCaseResult(run_id=run.id, case_id=r["case_id"], passed=r["passed"], scores=r["scores"], expected=r["expected"],
                                actual=r["actual"], latency_ms=r["latency_ms"], tokens=r["tokens"], cost=r["cost"], error=r["error"]))
    await db.flush()
    return run
