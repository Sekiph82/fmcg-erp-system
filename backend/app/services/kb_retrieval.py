"""Retrieval over approved (published, public) knowledge-base articles (M45.S01.T007/T008).

Lexical scoring: query terms (lower-case, stop words removed, simple English/Swahili stems) matched against title
(x3), summary (x2) and body. Only articles that pass kb_public._public() are ever returned, so drafts, internal and
company-restricted articles cannot leak into answers. Each hit carries its slug for the citation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

STOP = set("""a an and are as at be by can do does for from has have how i if in is it me my of on or our please the to
what when where which who why will with you your je ni na ya wa kwa la za cha vya katika nini gani lini""".split())


def terms(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-zA-Z0-9]{2,}", (text or "").lower()):
        if w in STOP:
            continue
        for suf in ("ing", "es", "ed", "s"):
            if len(w) > 4 and w.endswith(suf):
                w = w[: -len(suf)]
                break
        out.append(w)
    return out


@dataclass
class Hit:
    slug: str
    title: str
    summary: str
    body: str
    score: float


async def search(db: AsyncSession, query: str, limit: int = 3, min_score: float = 2.0) -> list[Hit]:
    from app.api.v1.endpoints.kb_public import _public
    from app.models.knowledge_base import KBArticle
    q = set(terms(query))
    if not q:
        return []
    rows = (await db.execute(select(KBArticle).where(and_(*_public())).limit(2000))).scalars()
    hits = []
    for a in rows:
        t, s, b = terms(a.title), terms(a.summary or ""), terms(a.content_md or "")
        score = 3 * len(q & set(t)) + 2 * len(q & set(s)) + min(3, sum(1 for w in b if w in q) / 3)
        if score >= min_score:
            hits.append(Hit(a.slug, a.title, a.summary or "", a.content_md or "", round(score, 2)))
    return sorted(hits, key=lambda h: -h.score)[:limit]
