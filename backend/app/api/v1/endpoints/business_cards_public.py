"""Public employee business cards (M42, no login): /public/cards/{slug}, {slug}.vcf, {slug}/photo. Allow-listed in
PUBLIC_ROUTES. A closed card (revoked, employee terminated or archived) and an unknown slug get the same answer with
no personal data. Responses are noindex and rate-limited per client."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.hr import Employee, EmployeeBusinessCard
from app.services import business_card_service as cards

router = APIRouter()
GONE = "This card is no longer valid."
NOINDEX = {"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-cache"}
_LIMIT, _MISS_LIMIT, _WINDOW = 120, 30, 60.0
# ponytail: per-process memory (one budget per worker); move to Redis when several API hosts serve cards
_hits: dict[str, deque] = defaultdict(deque)
_misses: dict[str, deque] = defaultdict(deque)


def _client(request: Request) -> str:
    # client.host is the real visitor only behind a proxy listed in FORWARDED_ALLOW_IPS (uvicorn rewrites it);
    # a client-supplied X-Forwarded-For is never trusted here
    return request.client.host if request.client else "?"


def _evict(store: dict[str, deque], now: float) -> None:
    if len(store) > 20_000:   # drop only stale clients, never live counters
        for k in [k for k, q in store.items() if not q or now - q[-1] > _WINDOW]:
            del store[k]


def _count(store: dict[str, deque], key: str, limit: int) -> None:
    now, q = time.monotonic(), store[key]
    while q and now - q[0] > _WINDOW:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(429, "Too many requests. Please try again in a minute.", headers={"Retry-After": "60", **NOINDEX})
    q.append(now)
    _evict(store, now)


def _rate_limit(request: Request) -> None:
    key = _client(request)
    _count(_hits, key, _LIMIT)
    request.state.card_client = key


async def _live(db: AsyncSession, slug: str, request: Request) -> tuple[EmployeeBusinessCard, Employee]:
    row = None
    if 1 <= len(slug) <= 120:
        row = (await db.execute(select(EmployeeBusinessCard, Employee).join(Employee, Employee.id == EmployeeBusinessCard.employee_id)
                                .where(EmployeeBusinessCard.slug == slug.lower()))).first()
    if row is None or not cards.is_live(row[0], row[1]):
        _count(_misses, getattr(request.state, "card_client", "?"), _MISS_LIMIT)   # guessing names costs more
        raise HTTPException(404, GONE, headers=NOINDEX)
    return row[0], row[1]


@router.get("/{slug}.vcf")
async def card_vcf(slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    """vCard 3.0 (UTF-8) with the photo when published with consent — 'Save contact' on iPhone and Android."""
    _rate_limit(request)
    card, emp = await _live(db, slug, request)
    return Response(cards.vcard(card, emp).encode("utf-8"), media_type="text/vcard; charset=utf-8",
                    headers={**NOINDEX, "Content-Disposition": f'attachment; filename="{card.slug}.vcf"'})


@router.get("/{slug}/photo")
async def card_photo(slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    _rate_limit(request)
    card, _emp = await _live(db, slug, request)
    img = cards.image_bytes(card.photo) if card.photo_consent_at else None
    if img is None:
        raise HTTPException(404, GONE, headers=NOINDEX)
    return Response(img[0], media_type=img[1], headers={**NOINDEX, "X-Content-Type-Options": "nosniff"})


@router.get("/{slug}")
async def card(slug: str, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    _rate_limit(request)
    card_row, emp = await _live(db, slug, request)
    response.headers.update(NOINDEX)
    return cards.public_view(card_row, emp)
