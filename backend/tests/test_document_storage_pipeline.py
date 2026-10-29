from __future__ import annotations

import asyncio
import hashlib
import struct
from io import BytesIO
from pathlib import Path
import uuid
import zipfile
import os
import re

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select

from app.api.v1.endpoints import documents as document_endpoints
from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.models.documents import Document, DocumentCategory, DocumentStatus
from app.models.user import User
from app.schemas.documents import DocumentCreate, DocumentUpdate
from app.services.document_storage_service import (
    LocalDocumentStorage,
    ScanResult,
    scan_document,
)


def _upload(name: str, content: bytes, content_type: str | None = None) -> UploadFile:
    headers = {"content-type": content_type} if content_type else None
    return UploadFile(filename=name, file=BytesIO(content), headers=headers)


@pytest.mark.asyncio
async def test_pdf_upload_has_opaque_key_checksum_and_restrictive_file_mode(tmp_path: Path):
    content = b"%PDF-1.7\nsynthetic document\n%%EOF\n"
    storage = LocalDocumentStorage(tmp_path)

    stored = await storage.store_upload(_upload("work-instruction.pdf", content, "application/pdf"))

    assert len(stored.storage_key) == 32
    assert stored.storage_key == stored.storage_key.lower()
    assert "/" not in stored.storage_key and "\\" not in stored.storage_key
    assert stored.file_name == "work-instruction.pdf"
    assert stored.mime_type == "application/pdf"
    assert stored.file_size_bytes == len(content)
    assert stored.sha256 == hashlib.sha256(content).hexdigest()
    assert storage.path_for(stored.storage_key).read_bytes() == content
    assert not list(tmp_path.glob("*.upload"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("filename", "content", "content_type", "status"),
    [
        ("../../secret.pdf", b"%PDF-1.7\nx", "application/pdf", None),
        ("payload.exe", b"MZ\x00\x00", "application/octet-stream", 415),
        ("fake.pdf", b"<html>not a pdf</html>", "application/pdf", 415),
        ("image.png", b"%PDF-1.7\nwrong extension", "image/png", 415),
        ("file.pdf", b"%PDF-1.7\n", "image/png", 415),
        ("empty.pdf", b"", "application/pdf", 422),
    ],
)
async def test_upload_rejects_unsafe_or_mismatched_content(tmp_path, filename, content, content_type, status):
    storage = LocalDocumentStorage(tmp_path)
    upload = _upload(filename, content, content_type)

    if status is None:
        stored = await storage.store_upload(upload)
        assert stored.file_name == "secret.pdf"
    else:
        with pytest.raises(HTTPException) as error:
            await storage.store_upload(upload)
        assert error.value.status_code == status
    assert not list(tmp_path.glob("*.upload"))


@pytest.mark.asyncio
async def test_upload_limit_is_enforced_and_temporary_data_is_removed(tmp_path):
    storage = LocalDocumentStorage(tmp_path)
    with pytest.raises(HTTPException) as error:
        await storage.store_upload(_upload("large.pdf", b"%PDF-1.7\n12345", "application/pdf"), max_bytes=8)
    assert error.value.status_code == 413
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_text_files_must_be_valid_utf8_and_not_binary(tmp_path):
    storage = LocalDocumentStorage(tmp_path)
    with pytest.raises(HTTPException) as error:
        await storage.store_upload(_upload("bad.csv", b"a,b\n\xff", "text/csv"))
    assert error.value.status_code == 415
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_office_file_must_be_a_matching_zip_package(tmp_path):
    storage = LocalDocumentStorage(tmp_path)
    with pytest.raises(HTTPException) as error:
        await storage.store_upload(
            _upload("report.docx", b"PK\x03\x04not-a-zip", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        )
    assert error.value.status_code == 415

    office_path = tmp_path / "valid.docx"
    with zipfile.ZipFile(office_path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
    content = office_path.read_bytes()
    stored = await storage.store_upload(
        _upload("report.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    )
    assert storage.path_for(stored.storage_key).read_bytes() == content


@pytest.mark.asyncio
async def test_unconfigured_scanner_keeps_file_quarantined(tmp_path, monkeypatch):
    path = tmp_path / "stored"
    path.write_bytes(b"%PDF-1.7\n")
    monkeypatch.setattr(settings, "DOCUMENT_CLAMAV_HOST", "")

    result = await scan_document(path)

    assert result.status == "NOT_SCANNED"
    assert "remains quarantined" in result.result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "expected"),
    [(b"stream: OK\n", "CLEAN"), (b"stream: Test-Signature FOUND\n", "INFECTED")],
)
async def test_clamav_instream_protocol_sets_only_scanner_confirmed_status(tmp_path, monkeypatch, response, expected):
    payload = b"%PDF-1.7\nsynthetic file"
    path = tmp_path / "stored"
    path.write_bytes(payload)
    observed = bytearray()

    async def handle(reader, writer):
        assert await reader.readexactly(len(b"zINSTREAM\0")) == b"zINSTREAM\0"
        while True:
            (size,) = struct.unpack("!I", await reader.readexactly(4))
            if size == 0:
                break
            observed.extend(await reader.readexactly(size))
        writer.write(response)
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    monkeypatch.setattr(settings, "DOCUMENT_CLAMAV_HOST", "127.0.0.1")
    monkeypatch.setattr(settings, "DOCUMENT_CLAMAV_PORT", port)
    monkeypatch.setattr(settings, "DOCUMENT_CLAMAV_TIMEOUT_SECONDS", 2)
    try:
        result = await scan_document(path)
    finally:
        server.close()
        await server.wait_closed()

    assert result.status == expected
    assert bytes(observed) == payload


def test_document_api_cannot_accept_client_authored_storage_metadata():
    with pytest.raises(Exception):
        DocumentCreate(title="Synthetic", category=DocumentCategory.SOP, storage_key="outside-root")
    with pytest.raises(Exception):
        DocumentUpdate(file_scan_status="CLEAN")
    with pytest.raises(Exception):
        DocumentCreate(title="Synthetic", category=DocumentCategory.SOP, status=DocumentStatus.APPROVED)


def _route_permissions(route) -> set[str]:
    codes: set[str] = set()
    for dependency in route.dependencies:
        closure = getattr(dependency.dependency, "__closure__", None) or []
        for cell in closure:
            try:
                value = cell.cell_contents
            except ValueError:
                continue
            if isinstance(value, str) and value in {"documents.view", "documents.edit"}:
                codes.add(value)
    return codes


def test_binary_routes_require_document_permissions():
    routes = {
        (route.path, method): route
        for route in document_endpoints.router.routes
        for method in route.methods
    }
    assert "documents.edit" in _route_permissions(routes[("/{doc_id}/file", "POST")])
    assert "documents.edit" in _route_permissions(routes[("/{doc_id}/scan", "POST")])
    download = routes[("/{doc_id}/file", "GET")]
    assert "documents.view" in _route_permissions(download)


def _task_database_name() -> str:
    expected = os.environ.get("M01_S02_T005_DISPOSABLE_TEST_DATABASE_NAME")
    url = engine.url
    if not (
        os.environ.get("M01_S02_T005_DISPOSABLE_TEST_DATABASE") == "1"
        and url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and expected
        and re.fullmatch(r"fmcg_m01_s02_t005_[a-f0-9]{20,32}", expected)
        and url.database == expected
    ):
        pytest.fail("Refusing writes: DATABASE_URL must match the exact passwordless task-owned loopback database.")
    return expected


@pytest.mark.asyncio
async def test_upload_scan_quarantine_and_secure_download_postgresql(tmp_path, monkeypatch):
    expected_database = _task_database_name()
    suffix = uuid.uuid4().hex[:12]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.current_database()))).scalar_one() == expected_database
        user = User(
            email=f"m01-t005-{suffix}@example.invalid",
            username=f"m01t005{suffix}",
            full_name=f"Synthetic document owner {suffix}",
            hashed_password="synthetic-test-only-not-a-credential",
            is_superuser=True,
        )
        db.add(user)
        await db.flush()
        doc = Document(
            title=f"Synthetic SOP {suffix}",
            category=DocumentCategory.SOP,
            status=DocumentStatus.DRAFT,
            owner_user_id=user.id,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        doc_id, user_id = doc.id, user.id

        storage = LocalDocumentStorage(tmp_path)
        monkeypatch.setattr(document_endpoints, "get_document_storage", lambda: storage)
        monkeypatch.setattr(document_endpoints, "scan_document", _not_scanned)
        response = await document_endpoints.upload_document_file(
            doc_id, _upload("synthetic-sop.pdf", b"%PDF-1.7\nsynthetic\n", "application/pdf"), db, user
        )
        primary_storage_key = doc.storage_key
        assert response.file_storage_ready is True
        assert response.file_scan_status == "NOT_SCANNED"
        assert response.file_checksum_sha256 == hashlib.sha256(b"%PDF-1.7\nsynthetic\n").hexdigest()
        assert doc.storage_key
        assert doc.storage_key not in document_endpoints.DocumentRead.model_validate(doc).model_dump_json()

        with pytest.raises(HTTPException) as blocked_download:
            await document_endpoints.download_document_file(doc_id, db, user)
        assert blocked_download.value.status_code == 423
        with pytest.raises(HTTPException) as blocked_approval:
            await document_endpoints.approve_document(doc_id, document_endpoints.DocumentApprove(), db, user)
        assert blocked_approval.value.status_code == 409

        monkeypatch.setattr(document_endpoints, "scan_document", _clean)
        scanned = await document_endpoints.scan_document_file(doc_id, db, user)
        assert scanned.file_scan_status == "CLEAN"
        download = await document_endpoints.download_document_file(doc_id, db, user)
        assert download.path.read_bytes() == b"%PDF-1.7\nsynthetic\n"
        assert download.headers["cache-control"] == "no-store"
        assert download.headers["x-content-type-options"] == "nosniff"

        scan_started = asyncio.Event()
        allow_rescan_to_finish = asyncio.Event()

        async def _delayed_infected(_path):
            scan_started.set()
            await allow_rescan_to_finish.wait()
            return ScanResult("INFECTED", "Synthetic delayed malware result")

        scan_db = AsyncSessionLocal()
        approval_during_scan_db = AsyncSessionLocal()
        try:
            monkeypatch.setattr(document_endpoints, "scan_document", _delayed_infected)
            rescan_task = asyncio.create_task(document_endpoints.scan_document_file(doc_id, scan_db, user))
            await asyncio.wait_for(scan_started.wait(), timeout=5)
            with pytest.raises(HTTPException) as approval_during_scan:
                await document_endpoints.approve_document(
                    doc_id, document_endpoints.DocumentApprove(), approval_during_scan_db, user
                )
            assert approval_during_scan.value.status_code == 409
            await approval_during_scan_db.rollback()
            allow_rescan_to_finish.set()
            infected = await rescan_task
        finally:
            allow_rescan_to_finish.set()
            await scan_db.close()
            await approval_during_scan_db.close()

        assert infected.file_scan_status == "INFECTED"
        assert infected.status == DocumentStatus.DRAFT
        infected_download_db = AsyncSessionLocal()
        try:
            with pytest.raises(HTTPException) as blocked_again:
                await document_endpoints.download_document_file(doc_id, infected_download_db, user)
            assert blocked_again.value.status_code == 423
        finally:
            await infected_download_db.close()

        race_doc = Document(
            title=f"Synthetic upload race {suffix}",
            category=DocumentCategory.SOP,
            status=DocumentStatus.DRAFT,
            owner_user_id=user.id,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        db.add(race_doc)
        await db.commit()
        await db.refresh(race_doc)
        race_doc_id = race_doc.id

        scan_started = asyncio.Event()
        allow_scan_to_finish = asyncio.Event()

        async def _delayed_scan(_path):
            scan_started.set()
            await allow_scan_to_finish.wait()
            return ScanResult("NOT_SCANNED", "Synthetic delayed scanner result")

        upload_db = AsyncSessionLocal()
        approval_db = AsyncSessionLocal()
        try:
            monkeypatch.setattr(document_endpoints, "scan_document", _delayed_scan)
            upload_task = asyncio.create_task(document_endpoints.upload_document_file(
                race_doc_id,
                _upload("racing-upload.pdf", b"%PDF-1.7\nrace\n", "application/pdf"),
                upload_db,
                user,
            ))
            await asyncio.wait_for(scan_started.wait(), timeout=5)
            approved_race = await document_endpoints.approve_document(
                race_doc_id, document_endpoints.DocumentApprove(), approval_db, user
            )
            assert approved_race.status == DocumentStatus.APPROVED
            allow_scan_to_finish.set()
            with pytest.raises(HTTPException) as upload_after_approval:
                await upload_task
            assert upload_after_approval.value.status_code in {403, 409}

            race_after = (await db.execute(
                select(Document)
                .where(Document.id == race_doc_id)
                .execution_options(populate_existing=True)
            )).scalar_one()
            assert race_after.status == DocumentStatus.APPROVED
            assert race_after.storage_key is None
            assert {path.name for path in tmp_path.iterdir()} == {primary_storage_key}
        finally:
            allow_scan_to_finish.set()
            await upload_db.close()
            await approval_db.close()

        duplicate_doc = Document(
            title=f"Synthetic duplicate upload race {suffix}",
            category=DocumentCategory.SOP,
            status=DocumentStatus.DRAFT,
            owner_user_id=user.id,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        db.add(duplicate_doc)
        await db.commit()
        await db.refresh(duplicate_doc)
        duplicate_doc_id = duplicate_doc.id
        both_scans_started = asyncio.Event()
        allow_both_scans_to_finish = asyncio.Event()
        scan_count = 0

        async def _duplicate_scan_barrier(_path):
            nonlocal scan_count
            scan_count += 1
            if scan_count == 2:
                both_scans_started.set()
            await allow_both_scans_to_finish.wait()
            return ScanResult("NOT_SCANNED", "Synthetic concurrent scanner result")

        upload_db_one = AsyncSessionLocal()
        upload_db_two = AsyncSessionLocal()
        try:
            monkeypatch.setattr(document_endpoints, "scan_document", _duplicate_scan_barrier)
            duplicate_uploads = [
                asyncio.create_task(document_endpoints.upload_document_file(
                    duplicate_doc_id,
                    _upload("first-upload.pdf", b"%PDF-1.7\nfirst\n", "application/pdf"),
                    upload_db_one,
                    user,
                )),
                asyncio.create_task(document_endpoints.upload_document_file(
                    duplicate_doc_id,
                    _upload("second-upload.pdf", b"%PDF-1.7\nsecond\n", "application/pdf"),
                    upload_db_two,
                    user,
                )),
            ]
            await asyncio.wait_for(both_scans_started.wait(), timeout=5)
            allow_both_scans_to_finish.set()
            outcomes = await asyncio.gather(*duplicate_uploads, return_exceptions=True)
            successes = [outcome for outcome in outcomes if not isinstance(outcome, Exception)]
            failures = [outcome for outcome in outcomes if isinstance(outcome, HTTPException)]
            assert len(successes) == 1
            assert len(failures) == 1 and failures[0].status_code == 409

            duplicate_after = (await db.execute(
                select(Document)
                .where(Document.id == duplicate_doc_id)
                .execution_options(populate_existing=True)
            )).scalar_one()
            assert duplicate_after.storage_key
            assert storage.path_for(duplicate_after.storage_key).is_file()
            assert {path.name for path in tmp_path.iterdir()} == {
                primary_storage_key,
                duplicate_after.storage_key,
            }
        finally:
            allow_both_scans_to_finish.set()
            await upload_db_one.close()
            await upload_db_two.close()

        storage.delete(duplicate_after.storage_key)
        storage.delete(primary_storage_key)
        await db.delete(duplicate_doc)
        await db.delete(race_doc)
        await db.delete(doc)
        await db.delete(user)
        await db.commit()


async def _not_scanned(_path):
    return ScanResult("NOT_SCANNED", "No scanner configured; quarantined")


async def _clean(_path):
    return ScanResult("CLEAN", "Synthetic scanner clean result")
