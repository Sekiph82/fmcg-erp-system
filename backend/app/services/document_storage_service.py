"""Local document binary storage and fail-closed ClamAV scanning."""
from __future__ import annotations

import asyncio
import hashlib
import os
import re
import struct
import tempfile
import unicodedata
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import settings


ALLOWED_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
_STORAGE_KEY = re.compile(r"^[a-f0-9]{32}$")
_CHUNK_SIZE = 64 * 1024


@dataclass(frozen=True)
class StoredDocumentFile:
    storage_key: str
    file_name: str
    file_size_bytes: int
    mime_type: str
    sha256: str


@dataclass(frozen=True)
class ScanResult:
    status: str
    result: str


def _safe_file_name(file_name: str | None) -> tuple[str, str, str]:
    raw = (file_name or "").replace("\\", "/").split("/")[-1]
    normalized = unicodedata.normalize("NFKC", raw).strip()
    if (
        not normalized
        or len(normalized) > 255
        or any(ord(char) < 32 or ord(char) == 127 for char in normalized)
        or normalized in {".", ".."}
    ):
        raise HTTPException(status_code=422, detail="A safe file name is required")
    extension = Path(normalized).suffix.lower()
    mime_type = ALLOWED_MIME_TYPES.get(extension)
    if not mime_type:
        raise HTTPException(status_code=415, detail="This document file type is not allowed")
    return normalized, extension, mime_type


def _validate_file_content(path: Path, extension: str, prefix: bytes) -> None:
    if extension == ".pdf" and prefix.startswith(b"%PDF-"):
        return
    if extension == ".png" and prefix.startswith(b"\x89PNG\r\n\x1a\n"):
        return
    if extension in {".jpg", ".jpeg"} and prefix.startswith(b"\xff\xd8\xff"):
        return
    if extension in {".txt", ".csv"}:
        try:
            with path.open("r", encoding="utf-8-sig", errors="strict") as stream:
                for chunk in iter(lambda: stream.read(_CHUNK_SIZE), ""):
                    if "\x00" in chunk:
                        raise HTTPException(status_code=415, detail="Binary content is not allowed for this file type")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=415, detail="Text files must use UTF-8 encoding") from exc
        return
    if extension in {".docx", ".xlsx"} and prefix.startswith(b"PK\x03\x04"):
        expected_part = "word/document.xml" if extension == ".docx" else "xl/workbook.xml"
        try:
            with zipfile.ZipFile(path) as archive:
                names = set(archive.namelist())
                if "[Content_Types].xml" not in names or expected_part not in names:
                    raise HTTPException(status_code=415, detail="The file content does not match its extension")
                if archive.getinfo("[Content_Types].xml").file_size > 1024 * 1024:
                    raise HTTPException(status_code=415, detail="Office document metadata is too large")
                archive.read("[Content_Types].xml")
        except (OSError, zipfile.BadZipFile, KeyError, RuntimeError) as exc:
            raise HTTPException(status_code=415, detail="The Office document is invalid") from exc
        return
    raise HTTPException(status_code=415, detail="The file content does not match its extension")


class LocalDocumentStorage:
    """Stores files under generated opaque keys; client paths are never used."""

    def __init__(self, root: Path | str | None = None):
        configured = Path(root or settings.DOCUMENT_STORAGE_PATH)
        if not configured.is_absolute():
            configured = Path(__file__).resolve().parents[2] / configured
        self.root = configured.resolve()

    def path_for(self, storage_key: str) -> Path:
        if not _STORAGE_KEY.fullmatch(storage_key):
            raise HTTPException(status_code=404, detail="Stored document file not found")
        unresolved = self.root / storage_key
        if unresolved.is_symlink():
            raise HTTPException(status_code=404, detail="Stored document file not found")
        candidate = unresolved.resolve()
        if candidate.parent != self.root:
            raise HTTPException(status_code=404, detail="Stored document file not found")
        return candidate

    async def store_upload(
        self,
        upload: UploadFile,
        *,
        max_bytes: int | None = None,
    ) -> StoredDocumentFile:
        file_name, extension, mime_type = _safe_file_name(upload.filename)
        declared_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
        if declared_type not in {"", "application/octet-stream", mime_type}:
            raise HTTPException(status_code=415, detail="The declared MIME type does not match the file extension")

        limit = max_bytes if max_bytes is not None else settings.DOCUMENT_MAX_UPLOAD_BYTES
        if limit < 1:
            raise HTTPException(status_code=503, detail="Document upload size limit is not configured")

        storage_key = uuid.uuid4().hex
        self.root.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{storage_key}.", suffix=".upload", dir=self.root)
        temp_path = Path(temp_name)
        digest = hashlib.sha256()
        prefix = bytearray()
        size = 0
        try:
            with os.fdopen(fd, "wb") as target:
                while True:
                    chunk = await upload.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > limit:
                        raise HTTPException(status_code=413, detail="The document exceeds the configured upload limit")
                    if len(prefix) < 4096:
                        prefix.extend(chunk[: 4096 - len(prefix)])
                    digest.update(chunk)
                    target.write(chunk)
                target.flush()
                os.fsync(target.fileno())
            if size == 0:
                raise HTTPException(status_code=422, detail="Empty document files are not allowed")
            _validate_file_content(temp_path, extension, bytes(prefix))
            final_path = self.path_for(storage_key)
            if final_path.exists():
                raise HTTPException(status_code=409, detail="A storage-key collision occurred")
            os.replace(temp_path, final_path)
            try:
                os.chmod(final_path, 0o600)
            except OSError:
                # Windows does not expose POSIX mode semantics; the generated
                # opaque key and authorization checks remain the access control.
                pass
            return StoredDocumentFile(storage_key, file_name, size, mime_type, digest.hexdigest())
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

    def delete(self, storage_key: str) -> None:
        self.path_for(storage_key).unlink(missing_ok=True)


def get_document_storage() -> LocalDocumentStorage:
    if settings.DOCUMENT_STORAGE_PROVIDER.strip().lower() != "local":
        raise HTTPException(status_code=503, detail="The configured document storage provider is not available")
    return LocalDocumentStorage()


async def scan_document(path: Path) -> ScanResult:
    host = settings.DOCUMENT_CLAMAV_HOST.strip()
    if not host:
        return ScanResult("NOT_SCANNED", "No malware scanner is configured; file remains quarantined.")

    writer = None
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, settings.DOCUMENT_CLAMAV_PORT),
            timeout=settings.DOCUMENT_CLAMAV_TIMEOUT_SECONDS,
        )
        writer.write(b"zINSTREAM\0")
        with path.open("rb") as stream:
            while chunk := stream.read(_CHUNK_SIZE):
                writer.write(struct.pack("!I", len(chunk)))
                writer.write(chunk)
                await asyncio.wait_for(writer.drain(), timeout=settings.DOCUMENT_CLAMAV_TIMEOUT_SECONDS)
        writer.write(struct.pack("!I", 0))
        await asyncio.wait_for(writer.drain(), timeout=settings.DOCUMENT_CLAMAV_TIMEOUT_SECONDS)
        response = await asyncio.wait_for(reader.readline(), timeout=settings.DOCUMENT_CLAMAV_TIMEOUT_SECONDS)
        decoded = response.decode("utf-8", errors="replace").strip()
        if decoded.endswith(": OK"):
            return ScanResult("CLEAN", "ClamAV scan completed successfully.")
        if decoded.endswith(" FOUND"):
            return ScanResult("INFECTED", "ClamAV detected malicious content; file remains quarantined.")
        return ScanResult("SCAN_ERROR", "ClamAV returned an invalid scan response; file remains quarantined.")
    except (OSError, asyncio.TimeoutError, ValueError, struct.error):
        return ScanResult("SCAN_ERROR", "ClamAV scan could not be completed; file remains quarantined.")
    finally:
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass
