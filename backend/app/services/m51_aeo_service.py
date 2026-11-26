"""M51.S01.T005 AEO (answer-engine) measurement.

What this measures: how often a configured answer engine, asked a fixed set of localized prompts several times, names
the brand / its competitors and cites the brand's own domains. It is a SAMPLE of one model's answers, not a ranking in
Google AI Overviews, ChatGPT or any other product, and every figure carries its sample size and a 95 % Wilson interval.
It is kept apart from "readiness" (the CMS AEO audit, cms_service.aeo_audit, which checks page structure only).

Provider interface (documented, nothing scraped): ``ai_provider`` runs the prompts through app.services.ai_provider
(Anthropic Messages API / OpenAI API / Gemini, whichever key is configured; their terms permit API use); ``simulator``
is a deterministic local answer generator, allowed only while PROVIDER_EGRESS != live, labelled SIMULATED. Brave
Search's answer-summary API was NOT verified against its documentation (dashboard docs unreachable 2026-11-26) and is
not wired. With no provider, no consent or the mock AI provider the state is NOT_CONFIGURED and nothing is invented.

Cost caps: max_calls_per_run on the prompt set, AEO_MAX_CALLS_PER_RUN (int, 100) and AEO_MONTHLY_CALL_CAP (int, 500)
across all sets; the owner must tick consent_confirmed on the set. The monthly cap counts PROVIDER ATTEMPTS (retries included, failed
ones too) and is reserved atomically before the run: under a month-wide advisory lock the worst case n_calls x MAX_ATTEMPTS is
written as a committed RESERVED run row (so two concurrent runs cannot both pass the check), every attempt is counted as it is
made, and when the run ends the row's calls is set to the attempts really made (the unused reservation is released).
"""
from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlsplit

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_http import egress_mode
from app.models.m51_seo import M51AeoAnswer, M51AeoPromptSet, M51AeoRun
from app.services import ai_provider as ai

LOCALES = ("en", "sw", "tr")
URL_RE = re.compile(r"https?://[^\s)\]>\"']+")
SYSTEM = {"en": "Answer the shopper's question helpfully. Name specific brands and cite sources as full URLs.",
          "sw": "Jibu swali la mnunuzi kwa msaada. Taja chapa mahususi na tumia vyanzo kama URL kamili.",
          "tr": "Alıcının sorusunu yardımcı olacak şekilde yanıtla. Belirli markaları an ve kaynakları tam URL olarak ver."}

MAX_ATTEMPTS = 3                                  # provider attempts per sample (generate_with_retry)
_LOCK_KEY = 5105                                  # pg advisory lock serialising the monthly reservation
_override: Optional[ai.BaseAIProvider] = None     # tests inject a ScriptedProvider; never set in production code


class AeoError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


class SimulatedAnswers(ai.BaseAIProvider):
    """Deterministic local answers (no network, no cost). A prompt+counter hash decides whether the brand appears."""

    def __init__(self, brand: str = "POVU", rival: str = "RivalSoap"):
        self.n, self.brand, self.rival = 0, brand, rival

    async def generate_text(self, prompt: str, system: Optional[str] = None) -> ai.AIResponse:
        self.n += 1
        h = int(hashlib.sha256(f"{prompt}|{self.n}".encode()).hexdigest(), 16)
        parts = [f"For {prompt[:60]} many shoppers pick {self.rival} (https://rival.example.com/p)."]
        if h % 3 != 0:
            parts.append(f"{self.brand} AllClean is also well reviewed (https://povu-demo.test/allclean).")
        text = " ".join(parts)
        return ai.AIResponse(text=text, provider="simulator", model="aeo-sim", prompt_tokens=len(prompt) // 4 + 1,
                             completion_tokens=len(text) // 4 + 1, latency_ms=1)


def wilson(k: int, n: int, z: float = 1.96) -> dict:
    if n == 0:
        return {"rate": None, "low": None, "high": None, "n": 0}
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return {"rate": round(p, 4), "low": round(max(0, centre - half), 4), "high": round(min(1, centre + half), 4), "n": n}


def _term_re(term: str):
    return re.compile(r"(?<!\w)" + re.escape(term.strip()) + r"(?!\w)", re.I)


def analyse(answer: str, brand_terms: list, brand_domains: list, competitors: list) -> dict:
    cites = []
    for i, u in enumerate(URL_RE.findall(answer or "")):
        u = u.rstrip(".,;")
        cites.append({"url": u[:300], "host": (urlsplit(u).hostname or "")[:100], "position": i + 1})
    doms = [d.lower().lstrip(".") for d in brand_domains]
    return {"brand": any(_term_re(t).search(answer or "") for t in brand_terms if t.strip()),
            "brand_cited": any(c["host"] == d or c["host"].endswith("." + d) for c in cites for d in doms),
            "competitors": [t for t in competitors if t.strip() and _term_re(t).search(answer or "")],
            "citations": cites[:20]}


def _clean_list(v, n, m) -> list[str]:
    out = [str(x).strip()[:m] for x in (v or []) if str(x).strip()]
    if len(out) > n:
        raise AeoError(422, f"At most {n} entries.")
    return out


async def create_set(db: AsyncSession, user: str, b: dict) -> M51AeoPromptSet:
    if b["locale"] not in LOCALES:
        raise AeoError(422, "Locale must be en, sw or tr.")
    prompts, brand = _clean_list(b.get("prompts"), 20, 300), _clean_list(b.get("brand_terms"), 10, 80)
    if not prompts or not brand:
        raise AeoError(422, "At least one prompt and one brand term are needed.")
    if b.get("provider", "") not in ("", "ai_provider", "simulator"):
        raise AeoError(422, "Provider must be ai_provider or simulator.")
    row = M51AeoPromptSet(name=b["name"].strip()[:120], locale=b["locale"], prompts=prompts, brand_terms=brand,
                          brand_domains=_clean_list(b.get("brand_domains"), 10, 100),
                          competitor_terms=_clean_list(b.get("competitor_terms"), 20, 80), provider=b.get("provider", ""),
                          samples_per_prompt=max(1, min(int(b.get("samples_per_prompt", 3)), 10)),
                          max_calls_per_run=max(1, min(int(b.get("max_calls_per_run", 30)), 100)),
                          consent_confirmed=bool(b.get("consent_confirmed")), created_by=user)
    db.add(row)
    await db.flush()
    return row


def _provider(kind: str):
    """(provider object | None, reasons)."""
    if _override is not None:
        return _override, []
    if kind == "simulator":
        return (SimulatedAnswers(), []) if egress_mode() != "live" else (None, ["The simulator is not allowed with PROVIDER_EGRESS=live."])
    if kind == "ai_provider":
        p = ai.get_ai_provider()
        if isinstance(p, ai.MockProvider):
            return None, ["No AI API key is configured (ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY); the mock provider is not a measurement."]
        return p, []
    return None, ["No answer-engine provider is selected for this prompt set."]


async def state(db: AsyncSession, s: M51AeoPromptSet) -> dict:
    prov, reasons = _provider(s.provider)
    if not s.consent_confirmed:
        reasons = reasons + ["The owner has not confirmed provider terms and cost for this set."]
    used = await month_calls(db)
    cap = int(getattr(settings, "AEO_MONTHLY_CALL_CAP", 500))
    if used >= cap:
        reasons = reasons + [f"The monthly call cap ({cap}) is used up."]
    return {"state": "OK" if prov and not reasons else "NOT_CONFIGURED", "reasons": reasons, "provider": s.provider or None,
            "source": "SIMULATED" if s.provider == "simulator" or _override is not None else "LIVE",
            "calls_this_month": used, "monthly_cap": cap}


async def month_calls(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    first = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return int((await db.execute(select(func.coalesce(func.sum(M51AeoRun.calls), 0)).where(M51AeoRun.created_at >= first))).scalar_one())


async def run(db: AsyncSession, s: M51AeoPromptSet, user: str) -> M51AeoRun:
    st = await state(db, s)
    if st["state"] != "OK":
        raise AeoError(409, "NOT_CONFIGURED: " + " ".join(st["reasons"]))
    n_calls = len(s.prompts) * s.samples_per_prompt
    cap = min(s.max_calls_per_run, int(getattr(settings, "AEO_MAX_CALLS_PER_RUN", 100)))
    if n_calls > cap:
        raise AeoError(422, f"{n_calls} calls exceed the per-run cap of {cap}; reduce prompts or samples.")
    prov, _ = _provider(s.provider)
    reserve = n_calls * MAX_ATTEMPTS
    await db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _LOCK_KEY})      # released by the commit below
    if await month_calls(db) + reserve > st["monthly_cap"]:
        await db.rollback()
        raise AeoError(422, f"This run could use up to {reserve} provider attempts and would exceed the monthly call cap.")
    rec = M51AeoRun(set_id=s.id, provider=s.provider or "override", source=st["source"], status="RESERVED", calls=reserve, created_by=user)
    db.add(rec)
    await db.flush()
    await db.commit()                                    # the reservation is durable and visible to every other run from here on
    rec_id = rec.id
    attempts = 0

    async def before_attempt():
        nonlocal attempts
        attempts += 1                                     # every attempt counts, successful or not

    try:
        return await _sample(db, s, rec, prov, before_attempt, lambda: attempts)
    except BaseException:
        await db.rollback()
        await db.execute(update(M51AeoRun).where(M51AeoRun.id == rec_id).values(calls=attempts, status="FAILED", error="run aborted"))
        await db.commit()
        raise


async def _sample(db: AsyncSession, s: M51AeoPromptSet, rec: M51AeoRun, prov, before_attempt, attempts) -> M51AeoRun:
    brand_n = comp_n = cite_n = 0
    comp_counts = {c: 0 for c in s.competitor_terms}
    per_prompt = {p: {"n": 0, "brand": 0} for p in s.prompts}
    errors = ok = 0
    for p in s.prompts:
        for i in range(s.samples_per_prompt):
            try:
                r = await ai.generate_with_retry(prov, p, system=SYSTEM[s.locale], max_attempts=MAX_ATTEMPTS, before_attempt=before_attempt)
            except Exception as e:  # noqa: BLE001  provider failure: counted and reported, never turned into a result
                errors += 1
                rec.error = f"{type(e).__name__}"[:200]
                continue
            ok += 1
            rec.model, rec.model_version = r.model, r.model
            a = analyse(r.text, s.brand_terms, s.brand_domains, s.competitor_terms)
            db.add(M51AeoAnswer(run_id=rec.id, prompt=p, sample=i + 1, answer=r.text[:4000], brand=a["brand"],
                                brand_cited=a["brand_cited"], competitors=a["competitors"], citations=a["citations"]))
            brand_n += a["brand"]
            cite_n += a["brand_cited"]
            per_prompt[p]["n"] += 1
            per_prompt[p]["brand"] += a["brand"]
            for c in a["competitors"]:
                comp_counts[c] += 1
    n = ok
    rec.calls = attempts()                               # actual attempts; the rest of the reservation is released
    rec.status = "FAILED" if n == 0 else ("PARTIAL" if errors else "DONE")
    rec.summary = {"locale": s.locale, "samples": n, "errors": errors,
                   "brand_mention": wilson(brand_n, n), "brand_citation": wilson(cite_n, n),
                   "competitors": {c: wilson(k, n) for c, k in comp_counts.items()},
                   "per_prompt": {p: wilson(v["brand"], v["n"]) for p, v in per_prompt.items()},
                   "low_sample": n < 30,
                   "note": "Share of sampled answers from this one model that name/cite the brand; not a search ranking."}
    await db.flush()
    await db.refresh(rec)
    return rec


async def trend(db: AsyncSession, set_id) -> list[dict]:
    runs = (await db.execute(select(M51AeoRun).where(M51AeoRun.set_id == set_id, M51AeoRun.status.notin_(("FAILED", "RESERVED")))
                             .order_by(M51AeoRun.created_at))).scalars().all()
    return [{"run_id": str(r.id), "at": r.created_at.isoformat(), "source": r.source, "model": r.model,
             "model_version": r.model_version, **{k: (r.summary or {}).get(k) for k in ("samples", "brand_mention", "brand_citation", "low_sample")}}
            for r in runs]
