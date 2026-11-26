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
what when where which who why will with you your je ni na ya wa kwa la za cha vya katika nini gani lini
bir bu ve ile için mi mı nasıl ne nedir povu""".split())   # povu: the brand is in every article, it grounds nothing

# M50.S01.T005: query-side Swahili/Turkish -> English glossary, so a SW/TR question reaches the English articles
GLOSSARY = {"uwasilishaji": "delivery", "usafirishaji": "delivery", "mzigo": "delivery", "teslimat": "delivery", "kargo": "delivery",
            "kurudisha": "return", "kurejesha": "return", "iade": "return", "bidhaa": "product", "ürün": "product", "urun": "product",
            "ukubwa": "size", "matumizi": "use", "kullanım": "use", "kullanim": "use", "kutu": "crate", "kreti": "crate",
            "iliyoharibika": "damaged", "hasarlı": "damaged", "hasarli": "damaged", "sabuni": "soap", "sabun": "soap",
            "malipo": "payment", "ödeme": "payment", "odeme": "payment", "bei": "price", "fiyat": "price",
            "hifadhi": "storage", "saklama": "storage", "mikono": "hand", "çamaşır": "laundry", "kufulia": "laundry"}

# retrieved text is data: an article whose body tries to instruct the model is quarantined, never quoted or sent to a model
INSTRUCTION_IN_DOC = re.compile(
    r"(ignore|disregard|forget)\s+(all\s+|any\s+)?(previous|prior|above|earlier)|system\s*prompt|you\s+are\s+now|"
    r"(reveal|print|show|send)\s+(your\s+)?(api|secret|system|password|prompt)|assistant\s*:|\[\s*(system|inst)\s*\]|"
    r"(approve|issue|process)\s+(a\s+|the\s+)?(refund|payment)|<\s*/?\s*(system|instruction)|"
    r"puuza\s+maagizo|önceki\s+talimat", re.I)


def terms(text: str, glossary: bool = False) -> list[str]:
    out = []
    for w in re.findall(r"[\w]{2,}", (text or "").lower()):
        if glossary and w in GLOSSARY:
            w = GLOSSARY[w]
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
    version: int = 1
    kind: str = "article"        # article | manual | pdf (from the article's tags)
    quarantined: bool = False    # body contains instruction-like text: never used as an answer source


def _kind(tags) -> str:
    t = {str(x).lower() for x in (tags or [])}
    return "manual" if "manual" in t else "pdf" if "pdf" in t else "article"


async def search(db: AsyncSession, query: str, limit: int = 3, min_score: float = 2.0, *, glossary: bool = False,
                 keep_quarantined: bool = False) -> list[Hit]:
    from app.api.v1.endpoints.kb_public import _public
    from app.models.knowledge_base import KBArticle
    q = set(terms(query, glossary))
    if not q:
        return []
    rows = (await db.execute(select(KBArticle).where(and_(*_public())).limit(2000))).scalars()
    hits = []
    for a in rows:
        t, s, b = terms(a.title), terms(a.summary or ""), terms(a.content_md or "")
        score = 3 * len(q & set(t)) + 2 * len(q & set(s)) + min(3, sum(1 for w in b if w in q) / 3)
        if score >= min_score:
            bad = bool(INSTRUCTION_IN_DOC.search(f"{a.title} {a.summary or ''} {a.content_md or ''}"))
            if bad and not keep_quarantined:
                continue
            hits.append(Hit(a.slug, a.title, a.summary or "", a.content_md or "", round(score, 2), a.version or 1,
                            _kind(a.tags), bad))
    return sorted(hits, key=lambda h: -h.score)[:limit]
