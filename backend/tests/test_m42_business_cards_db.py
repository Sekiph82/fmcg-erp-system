"""M42 employee digital business cards on disposable PostgreSQL: a card for every employee (screen/API and Excel
import), permanent name slugs, only work contact data on the public card, live data (a changed phone shows at once
under the same QR), closed card for terminated employees with the same answer as an unknown slug, photo only with
consent, vCard 3.0, QR, the employee's own card, rate limit."""
from __future__ import annotations

import base64
import io
import os
import re
import zipfile
from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException, Response
from sqlalchemy import func, select
from starlette.datastructures import Headers, UploadFile
from starlette.requests import Request

from app.db.session import AsyncSessionLocal, engine

TASK_DB_ENV = "M42_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M42_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m42_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")

def _jpeg() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (22, 112, 184)).save(buf, "JPEG")
    return buf.getvalue()


JPEG = _jpeg()


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _req(ip: str = "41.90.3.3", fwd: str | None = None) -> Request:
    headers = [(b"user-agent", b"Safari")] + ([(b"x-forwarded-for", fwd.encode())] if fwd else [])
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers, "client": (ip, 5000)})


async def _user(db):
    from app.models.user import User

    u = User(email=f"m42-{uuid4().hex}@example.invalid", username=f"m42{uuid4().hex}", full_name="POVU HR",
             hashed_password="synthetic-test-only-not-a-credential", is_active=True, is_superuser=True)
    db.add(u)
    await db.flush()
    return u


@pytest.mark.asyncio
async def test_cards_created_live_closed_and_private():
    from app.api.v1.endpoints import business_cards as staff
    from app.api.v1.endpoints import business_cards_public as public
    from app.api.v1.endpoints import hr as hr_api
    from app.models.audit_log import AuditLog
    from app.models.hr import EmployeeBusinessCard
    from app.schemas.hr import EmployeeCreate, EmployeeUpdate

    tag = uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        hr = await _user(db)
        await db.commit()
        hr_id = hr.id

        async def fresh_hr():
            from app.models.user import User
            return await db.get(User, hr_id)

        def body(code, name, **kw):
            return EmployeeCreate(**{"employee_code": f"{code}-{tag}", "full_name": name, "department": "Sales", "role": "Sales Representative",
                                     "phone": "+254 712 345 678", "email": f"{code.lower()}-{tag}@povu.example", "hire_date": date(2026, 1, 5),
                                     "mpesa_number": "+254700999888", "bank_account": "0123456789", "salary_grade": "G5",
                                     "payment_method": "MPESA", **kw})

        name = f"Wanjiku Kamau {tag}"
        a = await hr_api.create_employee(body("A", name), db, hr)
        b = await hr_api.create_employee(body("B", name), db, hr)            # same name -> department added
        t = await hr_api.create_employee(body("T", f"Şekip Hayıt {tag}"), db, hr)
        c3 = await hr_api.create_employee(body("C", name), db, hr)           # same name and department -> -sales-2
        c4 = await hr_api.create_employee(body("D", name, department="Logistics"), db, hr)
        ca = (await db.execute(select(EmployeeBusinessCard).where(EmployeeBusinessCard.employee_id == a.id))).scalar_one()
        cb = (await db.execute(select(EmployeeBusinessCard).where(EmployeeBusinessCard.employee_id == b.id))).scalar_one()
        ct = (await db.execute(select(EmployeeBusinessCard).where(EmployeeBusinessCard.employee_id == t.id))).scalar_one()
        assert (ca.status, ca.slug) == ("PUBLISHED", f"wanjiku-kamau-{tag}") and cb.slug == f"wanjiku-kamau-{tag}-sales"
        more = {r.employee_id: r.slug for r in (await db.execute(select(EmployeeBusinessCard).where(
            EmployeeBusinessCard.employee_id.in_([c3.id, c4.id])))).scalars()}
        assert more == {c3.id: f"wanjiku-kamau-{tag}-sales-2", c4.id: f"wanjiku-kamau-{tag}-logistics"}
        extra_slugs = list(more.values())
        assert ct.slug == f"sekip-hayit-{tag}"
        slug_a, slug_b, slug_t = ca.slug, cb.slug, ct.slug
        a_id, b_id = a.id, b.id

        # public card: work contacts only
        out = await public.card(slug_a, _req(), Response(), db)
        assert out["name"] == name and out["title"] == "Sales Representative" and out["company"] == "POVU"
        assert out["phone"] == "+254 712 345 678" and out["whatsapp"] == "254712345678" and out["email"].startswith("a-")
        flat = str(out)
        for secret in ("700999888", "0123456789", "G5", f"A-{tag}", "MPESA"):
            assert secret not in flat
        assert out["url"].endswith(f"/kartvizit/{slug_a}")

        # live data: rename keeps the slug (printed QR), new phone shows at once; toggles hide fields
        await hr_api.update_employee(a_id, EmployeeUpdate(full_name=f"Wanjiku M. Kamau {tag}", phone="+254 733 000 111"), db, hr)
        out = await public.card(slug_a, _req(), Response(), db)
        assert out["phone"] == "+254 733 000 111" and out["name"].startswith("Wanjiku M.")
        assert (await db.execute(select(EmployeeBusinessCard.slug).where(EmployeeBusinessCard.employee_id == a_id))).scalar_one() == slug_a
        await staff.update_card(a_id, staff.CardUpdate(show_whatsapp=False, show_email=False, title_en="Key Account Manager"), db, hr)
        out = await public.card(slug_a, _req(), Response(), db)
        assert out["whatsapp"] is None and out["email"] is None and out["title"] == "Key Account Manager"

        # photo: consent required; then on the card, the vCard and the photo endpoint
        up = UploadFile(io.BytesIO(JPEG), filename="wanjiku.jpg", headers=Headers({"content-type": "image/jpeg"}))
        with pytest.raises(HTTPException) as e:
            await staff.upload_photo(a_id, up, False, db, hr)
        assert e.value.status_code == 422
        await db.rollback()
        hr = await fresh_hr()
        fake = UploadFile(io.BytesIO(b"<svg onload=alert(1)>"), filename="x.png", headers=Headers({"content-type": "image/png"}))
        with pytest.raises(HTTPException) as e:
            await staff.upload_photo(a_id, fake, True, db, hr)
        assert e.value.status_code == 415
        await db.rollback()
        hr = await fresh_hr()
        up = UploadFile(io.BytesIO(JPEG), filename="wanjiku.jpg", headers=Headers({"content-type": "image/jpeg"}))
        row = await staff.upload_photo(a_id, up, True, db, hr)
        assert row["has_photo"] and row["photo_consent_at"]
        photo = await public.card_photo(slug_a, _req(), db)
        assert photo.body == JPEG and photo.media_type == "image/jpeg" and photo.headers["x-content-type-options"] == "nosniff"
        vcf = (await public.card_vcf(slug_a, _req(), db)).body.decode()
        assert vcf.startswith("BEGIN:VCARD\r\nVERSION:3.0\r\n") and vcf.endswith("END:VCARD\r\n")
        assert f"FN:Wanjiku M. Kamau {tag}" in vcf and "TEL;TYPE=WORK,VOICE:+254 733 000 111" in vcf and "EMAIL" not in vcf
        assert "PHOTO;ENCODING=b;TYPE=JPEG:" in vcf and all(len(x.encode()) <= 75 for x in vcf.split("\r\n"))
        assert "700999888" not in vcf and "0123456789" not in vcf
        from app.models.hr import Employee
        emp_a = await db.get(Employee, a_id)
        emp_a.role = "Sales\rURL:http://evil.example/\rEND:VCARD"
        emp_a.email = f"a-{tag}@povu.example?bcc=spy@evil.example"
        await staff.update_card(a_id, staff.CardUpdate(title_en="", show_email=True), db, hr)
        vcf = (await public.card_vcf(slug_a, _req(), db)).body.decode()
        lines = vcf.split("\r\n")
        assert not any(x.startswith("URL:http://evil") for x in lines) and lines.count("END:VCARD") == 1 and "EMAIL" not in vcf
        assert "TITLE:Sales URL:http://evil.example/ END:VCARD" in lines   # stays inside the title value
        assert (await public.card(slug_a, _req(), Response(), db))["email"] is None

        # QR codes (login): SVG and PNG; ZIP of live cards
        svg = await staff.card_qr(a_id, "svg", db, hr)
        png = await staff.card_qr(a_id, "png", db, hr)
        assert b"<svg" in svg.body[:200] and png.body.startswith(b"\x89PNG")
        z = zipfile.ZipFile(io.BytesIO((await staff.qr_zip(None, None, None, tag, db)).body))
        assert set(z.namelist()) == {f"{x}.png" for x in (slug_a, slug_b, slug_t, *extra_slugs)}

        # terminated -> closed: same answer as an unknown slug, nothing personal; republish needs an active employee
        await hr_api.update_employee(b_id, EmployeeUpdate(status="TERMINATED"), db, hr)
        cb = (await db.execute(select(EmployeeBusinessCard).where(EmployeeBusinessCard.employee_id == b_id))).scalar_one()
        assert cb.status == "REVOKED" and cb.revoked_reason == "employee terminated"
        answers = []
        for slug in (slug_b, f"nobody-{tag}"):
            for call in (lambda s: public.card(s, _req(), Response(), db), lambda s: public.card_vcf(s, _req(), db),
                         lambda s: public.card_photo(s, _req(), db)):
                with pytest.raises(HTTPException) as e:
                    await call(slug)
                answers.append((e.value.status_code, e.value.detail))
        assert set(answers) == {(404, "This card is no longer valid.")}
        with pytest.raises(HTTPException) as e:
            await staff.republish_card(b_id, db, hr)
        assert e.value.status_code == 409
        await db.rollback()
        hr = await fresh_hr()
        await hr_api.update_employee(b_id, EmployeeUpdate(status="ACTIVE"), db, hr)   # rehire
        assert (await staff.republish_card(b_id, db, hr))["live"] is True
        assert (await public.card(slug_b, _req(), Response(), db))["slug"] == slug_b  # same QR works again

        events = set((await db.execute(select(AuditLog.event_type).where(AuditLog.target_type == "business_card",
                                                                         AuditLog.target_name.in_([slug_a, slug_b])))).scalars())
        assert {"BUSINESS_CARD_CREATED", "BUSINESS_CARD_UPDATED", "BUSINESS_CARD_PHOTO_SET", "BUSINESS_CARD_REVOKED",
                "BUSINESS_CARD_PUBLISHED"} <= events


@pytest.mark.asyncio
async def test_import_creates_cards_my_card_and_rate_limit():
    from app.api.v1.endpoints import business_cards as staff
    from app.api.v1.endpoints import business_cards_public as public
    from app.api.v1.endpoints.bulk_import import EmployeeAdapter
    from app.models.hr import Employee, EmployeeBusinessCard

    tag = uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        me = await _user(db)
        emp = await EmployeeAdapter().insert({"employee_code": f"IMP-{tag}", "full_name": f"Otieno Ouma {tag}", "department": "Production",
                                              "role": "Line Operator", "hire_date": date(2026, 2, 1), "status": "ACTIVE",
                                              "phone": "+254700111222", "user_id": me.id}, db)
        await db.commit()
        card = (await db.execute(select(EmployeeBusinessCard).where(EmployeeBusinessCard.employee_id == emp.id))).scalar_one()
        assert card.status == "PUBLISHED" and card.slug == f"otieno-ouma-{tag}"
        slug, emp_id = card.slug, emp.id

        # an older, terminated record linked to the same login does not hide the current one
        db.add(Employee(employee_code=f"OLD-{tag}", full_name=f"Otieno Ouma {tag}", department="Production", role="Helper",
                        hire_date=date(2020, 1, 1), status="TERMINATED", user_id=me.id))
        await db.commit()
        mine = await staff.my_card(db, me)
        assert mine["slug"] == slug and mine["employee_code"] is None
        assert (await staff.my_card_qr("png", db, me)).body.startswith(b"\x89PNG")
        stranger = SimpleNamespace(id=uuid4())
        with pytest.raises(HTTPException) as e:
            await staff.my_card(db, stranger)
        assert e.value.status_code == 404
        await db.rollback()

        public._hits.clear()
        public._misses.clear()
        ip = f"41.90.9.{int(tag[:2], 16) % 250}"
        for n in range(public._LIMIT):
            await public.card(slug, _req(ip, fwd=f"10.0.{n // 250}.{n % 250}"), Response(), db)
        with pytest.raises(HTTPException) as e:
            await public.card(slug, _req(ip, fwd="203.0.113.77"), Response(), db)
        assert e.value.status_code == 429
        other = "41.90.10.10"
        for n in range(public._MISS_LIMIT):
            with pytest.raises(HTTPException) as e:
                await public.card(f"no-such-person-{n}", _req(other), Response(), db)
            assert e.value.status_code == 404
        with pytest.raises(HTTPException) as e:
            await public.card(f"no-such-person-x", _req(other), Response(), db)
        assert e.value.status_code == 429
        assert (await db.get(Employee, emp_id)) is not None
