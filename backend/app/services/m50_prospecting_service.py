"""M50.S01.T001 AI Prospecting Agent orchestration (extends the M45 prospecting in customer_data_service).

Steps of one run, each logged with counts and unknowns:
 1 ICP -> discovery from CRM open leads and licensed imported sources (customer_data_service.prospect: existing
   customers are excluded, every score point carries a citation);
 2 CRM association/dedup (an imported prospect that matches an open CRM lead is linked to it, not duplicated);
 3 authorised web research (T002 adapter; only when SEARCH is configured, enabled and licensed): matching result
   titles/snippets become citations with retrieval time; discovery queries may add low-confidence "web" candidates
   that always say what is unverified;
 4 territory/channel assessment from our own customers, competitor mentions from cited text only;
 5 ranking: the configured LLM (ai_provider) may adjust each score by at most +/-0.15 and write a rationale that must
   cite evidence ids [E1]..; any failure, unknown id or ungrounded rationale falls back to the deterministic rationale.
   With the mock provider (no key) the run is labelled DETERMINISTIC.
Outreach is only ever a proposal: an AI action request that a DIFFERENT person approves; suppressed or unsubscribed
addresses are refused at proposal time and again by the outbox. Nothing is sent, scraped or invented.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.m50_prospecting import M50AgentRun, M50Candidate, M50Icp
from app.services import customer_data_service as cds
from app.services import m50_research_service as rs

MAX_ADJUST = 0.15
WEB_CANDIDATE_SCORE = 0.2


class AgentError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _tokens(name: str) -> set[str]:
    return {t for t in cds.norm_name(name).split() if len(t) > 2}


def _mentions(name: str, text: str) -> bool:
    t = _tokens(name)
    return bool(t) and t <= _tokens(text)


async def territory(db: AsyncSession, city: Optional[str], region: Optional[str]) -> dict:
    from app.models.sales import Customer
    if not city and not region:
        return {"assessment": "UNKNOWN", "note": "No city or region known for this company."}
    q = select(func.count()).select_from(Customer).where(Customer.is_active.is_(True))
    n_city = (await db.execute(q.where(func.lower(Customer.city) == (city or "").lower()))).scalar_one() if city else None
    n_region = (await db.execute(q.where(func.lower(Customer.region) == (region or "").lower()))).scalar_one() if region else None
    n = n_city if n_city is not None else n_region
    return {"assessment": "WHITE_SPACE" if n == 0 else "SERVED", "customers_in_city": n_city, "customers_in_region": n_region,
            "note": ("No active customer there yet: new territory." if n == 0 else f"{n} active customers already served nearby: delivery route likely exists.")}


def competitor_mentions(text: str, competitors: list[str], citation: str) -> dict:
    hits = [c for c in competitors if c and re.search(rf"\b{re.escape(c)}\b", text, re.I)]
    if not competitors:
        return {"assessment": "UNKNOWN", "mentions": [], "note": "No competitor list defined in the ICP."}
    return {"assessment": "MENTIONED" if hits else "NONE_FOUND", "mentions": [{"competitor": h, "citation": citation} for h in hits],
            "note": "Only cited text was searched; absence is not proof of no competitor."}


async def _llm_rank(cands: list[dict], brand_note: str) -> tuple[str, Optional[str], dict[str, dict], Optional[str]]:
    """(mode, model, {id: {adjust, rationale}}, error)."""
    from app.services.ai_provider import MockProvider, get_ai_provider
    prov = get_ai_provider()
    if isinstance(prov, MockProvider):
        return "DETERMINISTIC", None, {}, None
    payload = [{"id": c["key"], "company": c["company_name"], "score": c["score"],
                "evidence": [{"e": f"E{i + 1}", "criterion": e["criterion"], "value": e["value"]} for i, e in enumerate(c["evidence"])],
                "unknown": c["unknowns"]} for c in cands[:30]]
    prompt = ("Rank sales prospects for a home/personal care distributor. Use ONLY the evidence given; never add facts. "
              f"Reply with a JSON list [{{\"id\", \"adjust\" (number between -{MAX_ADJUST} and {MAX_ADJUST}), "
              "\"rationale\" (max 300 chars, must cite evidence ids like [E1], and name unknowns)}}].\n" + json.dumps(payload))
    try:
        res = await prov.generate_text(prompt, system="You are a careful B2B sales analyst. Do not invent facts.")
        data = res.parse_json()
    except Exception as e:                                   # provider down, bad JSON: the run still completes
        return "DETERMINISTIC", None, {}, f"LLM unavailable: {type(e).__name__}"
    out = {}
    by_id = {c["key"]: c for c in cands}
    for item in data if isinstance(data, list) else []:
        c = by_id.get(str(item.get("id")))
        if c is None:
            continue
        try:
            adj = max(-MAX_ADJUST, min(MAX_ADJUST, float(item.get("adjust", 0))))
        except (TypeError, ValueError):
            adj = 0.0
        cites = {int(n) for n in re.findall(r"\[E(\d+)\]", str(item.get("rationale", "")))}
        ok = bool(cites) and all(1 <= n <= len(c["evidence"]) for n in cites)
        out[c["key"]] = {"adjust": adj, "rationale": str(item["rationale"])[:300] if ok else None}
    return "LLM", getattr(res, "model", None), out, None


def _det_rationale(c: dict) -> str:
    ev = "; ".join(f'{e["criterion"]} {e["value"]} [{e["citation"]}]' for e in c["evidence"]) or "no matching evidence"
    return f"Matches: {ev}. Unknown: {', '.join(c['unknowns']) or 'none'}."


async def run(db: AsyncSession, user: str, *, criteria: dict, competitors: list[str], use_search: bool,
              discovery_queries: list[str], icp_id: Optional[uuid.UUID] = None) -> M50AgentRun:
    from app.models.crm import CRMRecord, CRMRecordType, CRMStatus
    steps: list[dict] = []
    base = await cds.prospect(db, criteria, user, limit=100)
    cands = [{**r, "key": f'{r["kind"]}:{r["id"]}', "citations": [], "unknowns": list(r["unknown"]), "web": False} for r in base.results]
    found = len(cands)
    merged: dict[str, dict] = {}
    for c in sorted(cands, key=lambda x: x["kind"] != "lead"):          # an existing CRM lead absorbs a matching imported row
        k = cds.norm_name(c["company_name"])
        keep = merged.setdefault(k, c)
        if keep is not c:
            keep["evidence"] += [e for e in c["evidence"] if e["criterion"] not in {x["criterion"] for x in keep["evidence"]}]
            keep["unknowns"] = [u for u in keep["unknowns"] if u in c["unknown"]]
            keep["score"], keep["email"] = max(keep["score"], c["score"]), keep.get("email") or c.get("email")
            keep["can_email"] = keep["can_email"] or c["can_email"]
    cands = list(merged.values())
    steps.append({"step": "discovery", "found": found, "candidates": len(cands), "duplicates_merged": found - len(cands),
                  "sources": sorted({c["kind"] for c in cands})})

    leads = {cds.norm_name(n): i for i, n in (await db.execute(select(CRMRecord.id, CRMRecord.company_name).where(
        CRMRecord.record_type == CRMRecordType.LEAD, CRMRecord.status == CRMStatus.OPEN))).all()}
    linked = 0
    for c in cands:
        lid = c["id"] if c["kind"] == "lead" else leads.get(cds.norm_name(c["company_name"]))
        c["crm_record_id"], c["crm_association"] = (uuid.UUID(str(lid)), "EXISTING_LEAD") if lid else (None, "NONE")
        linked += bool(lid)
    steps.append({"step": "crm_association", "linked_to_existing_leads": linked})

    state = await rs.search_state(db) if use_search else {"state": "OFF", "reasons": []}
    search_state = state["state"]
    if use_search and search_state == "OK":
        errs, searched = [], 0
        for c in cands[:10]:
            q = f'{c["company_name"]} {c.get("city") or ""}'.strip()
            try:
                rec = await rs.search(db, q, user)
            except rs.ResearchError as e:
                errs.append(str(e))
                search_state = "ERROR"
                break
            searched += 1
            for hit in rec.results:
                if _mentions(c["company_name"], f'{hit["title"]} {hit["description"]}'):
                    c["citations"].append({"url": hit["url"], "title": hit["title"], "snippet": hit["description"],
                                           "retrieved_at": _now().isoformat(), "age_days": 0})
            if c["citations"]:
                c["evidence"].append({"criterion": "web_presence", "value": f'{len(c["citations"])} web result(s)', "citation": c["citations"][0]["url"]})
                c["score"] = min(1.0, round(c["score"] + 0.1, 3))
            else:
                c["unknowns"].append("web_presence")
        existing = {cds.norm_name(c["company_name"]) for c in cands}
        for q in discovery_queries[:3] if search_state == "OK" else []:
            try:
                rec = await rs.search(db, q, user)
            except rs.ResearchError as e:
                errs.append(str(e))
                search_state = "ERROR"
                break
            searched += 1
            for hit in rec.results[:5]:
                name = re.split(r"\s[-|:]\s", hit["title"])[0].strip()
                if not name or cds.norm_name(name) in existing:
                    continue
                existing.add(cds.norm_name(name))
                cands.append({"kind": "web", "id": hit["url"], "key": f'web:{hit["url"]}', "company_name": name[:255], "city": None,
                              "channel": None, "segment": None, "email": None, "can_email": False, "score": WEB_CANDIDATE_SCORE,
                              "confidence": 0.2, "web": True, "source_age_days": 0, "crm_record_id": None, "crm_association": "NONE",
                              "citations": [{"url": hit["url"], "title": hit["title"], "snippet": hit["description"],
                                             "retrieved_at": _now().isoformat(), "age_days": 0}],
                              "evidence": [{"criterion": "web_result", "value": query_safe(q), "citation": hit["url"]}],
                              "unknowns": ["city", "channel", "segment", "email", "identity not verified: a person must confirm this is a real prospect"]})
        steps.append({"step": "web_research", "state": search_state, "searches": searched, "errors": errs[:3]})
    else:
        steps.append({"step": "web_research", "state": search_state, "searches": 0,
                      "note": "; ".join(state["reasons"]) or "Not requested."})

    for c in cands:
        text = " ".join([c.get("notes") or ""] + [x["snippet"] for x in c["citations"]])
        c["territory"] = await territory(db, c.get("city"), None)
        c["competitor"] = competitor_mentions(text, competitors, c["citations"][0]["url"] if c["citations"] else c["evidence"][0]["citation"] if c["evidence"] else "")
    steps.append({"step": "assessment", "white_space": sum(c["territory"]["assessment"] == "WHITE_SPACE" for c in cands),
                  "competitor_mentions": sum(bool(c["competitor"]["mentions"]) for c in cands)})

    mode, model, adj, err = await _llm_rank(cands, "")
    for c in cands:
        a = adj.get(c["key"], {})
        c["final"] = max(0.0, min(1.0, round(c["score"] + a.get("adjust", 0.0), 3)))
        c["rationale"] = a.get("rationale") or _det_rationale(c)
    cands.sort(key=lambda c: (-c["final"], -c["confidence"], c["company_name"]))
    steps.append({"step": "ranking", "mode": mode, "error": err, "ungrounded_rationales_dropped": sum(1 for v in adj.values() if not v["rationale"])})

    r = M50AgentRun(icp_id=icp_id, criteria={**criteria, "competitors": competitors}, llm_mode=mode, llm_model=model,
                    search_state=search_state, steps=steps, created_by=user)
    db.add(r)
    await db.flush()
    for c in cands:
        ages = [x for x in [c.get("source_age_days")] if x is not None]
        db.add(M50Candidate(run_id=r.id, kind=c["kind"], ref_id=str(c["id"])[:60], company_name=c["company_name"],
                            norm_name=cds.norm_name(c["company_name"]), email=c.get("email"), score=c["final"],
                            confidence=c["confidence"], evidence=c["evidence"], citations=c["citations"], unknowns=c["unknowns"],
                            territory=c["territory"], competitor=c["competitor"], rationale=c["rationale"],
                            crm_record_id=c["crm_record_id"], crm_association=c["crm_association"],
                            evidence_age_days=min(ages) if ages else None))
    await db.flush()
    return r


def query_safe(q: str) -> str:
    return f"search: {q[:80]}"


def cand_view(c: M50Candidate) -> dict:
    return {"id": str(c.id), "kind": c.kind, "company_name": c.company_name, "email": c.email, "score": c.score,
            "confidence": c.confidence, "evidence": c.evidence, "citations": c.citations, "unknowns": c.unknowns,
            "territory": c.territory, "competitor": c.competitor, "rationale": c.rationale,
            "crm_record_id": str(c.crm_record_id) if c.crm_record_id else None, "crm_association": c.crm_association,
            "evidence_age_days": c.evidence_age_days, "status": c.status,
            "approval_request_id": str(c.approval_request_id) if c.approval_request_id else None,
            "can_propose_outreach": bool(cds.norm_email(c.email)) and c.status == "RANKED",
            "outreach_blocked_reason": None if cds.norm_email(c.email) else "No verified e-mail address: call or visit instead."}


async def propose_outreach(db: AsyncSession, cand_id: uuid.UUID, user, subject: Optional[str], body: Optional[str]) -> dict:
    from app.services import crm_outbound_service as outbound
    from app.services import pat_service as pats
    c = await db.get(M50Candidate, cand_id, with_for_update=True)
    if c is None:
        raise AgentError(404, "Candidate not found")
    if c.status != "RANKED":
        raise AgentError(409, f"Candidate is already {c.status}.")
    email = cds.norm_email(c.email)
    if not email:
        raise AgentError(409, "No valid e-mail for this prospect; call or visit instead.")
    consent = await outbound.consent_for(db, email)
    if consent is not None and consent.status in outbound.SUPPRESSING:
        raise AgentError(409, f"This address is {consent.status.lower()}; no outreach is allowed.")
    result = {"kind": c.kind if c.kind != "web" else None, "id": c.ref_id, "company_name": c.company_name, "evidence": c.evidence}
    d = await cds.draft(db, result, user.full_name or user.username)
    req = await pats.propose(db, source="PROSPECT", source_ref=f"m50:{c.id}", user=user, action="send_email",
                             arguments={"to_email": email, "subject": subject or d["subject"], "body": body or d["body"]},
                             summary=f"First contact (AI prospecting): {c.company_name}")
    c.status, c.approval_request_id = "OUTREACH_PROPOSED", req.id
    pats.audit(db, user, "M50_OUTREACH_PROPOSED", "m50_candidate", str(c.id), {"request": str(req.id), "sources": d["sources"][:10]})
    return {"approval_request_id": str(req.id), "status": "PENDING", "sources": d["sources"]}


async def draft_for(db: AsyncSession, cand_id: uuid.UUID, user) -> dict:
    c = await db.get(M50Candidate, cand_id)
    if c is None:
        raise AgentError(404, "Candidate not found")
    return await cds.draft(db, {"kind": c.kind if c.kind != "web" else None, "id": c.ref_id, "company_name": c.company_name,
                                "evidence": c.evidence}, user.full_name or user.username)
