"""
File upload security validator.

Call validate_upload() in any endpoint that accepts file uploads.
Checks:
  - MIME type allowlist
  - file size limit
  - filename sanitization (path traversal prevention)
  - basic magic-byte verification for images/PDFs
"""
from __future__ import annotations

import os
import re
import logging
from fastapi import HTTPException, UploadFile

log = logging.getLogger(__name__)

# Maximum file size: 10 MB for documents, 50 MB for imports
MAX_BYTES_DEFAULT = 10 * 1024 * 1024
MAX_BYTES_IMPORT  = 50 * 1024 * 1024

ALLOWED_DOC_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    "application/vnd.ms-excel",   # xls
    "text/csv",
    "text/plain",
}

ALLOWED_IMPORT_TYPES = {
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/plain",
}

# Magic byte signatures
_MAGIC = {
    b"%PDF": "application/pdf",
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
    b"RIFF": "image/webp",
    b"PK\x03\x04": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

_UNSAFE_FILENAME_RE = re.compile(r"[^\w.\-]")


def sanitize_filename(filename: str) -> str:
    """Strip path traversal and non-safe characters from filename."""
    # Strip null bytes before any further processing
    filename = filename.replace("\x00", "")
    # Normalize Windows backslash separators so os.path.basename works on Linux
    filename = filename.replace("\\", "/")
    # Remove path components
    filename = os.path.basename(filename)
    # Replace unsafe chars
    filename = _UNSAFE_FILENAME_RE.sub("_", filename)
    # Prevent leading dots (hidden files)
    filename = filename.lstrip(".")
    return filename[:255] or "upload"


def _detect_mime_from_magic(header: bytes) -> str | None:
    for magic, mime in _MAGIC.items():
        if header.startswith(magic):
            return mime
    return None


async def validate_upload(
    file: UploadFile,
    allowed_types: set[str] = ALLOWED_DOC_TYPES,
    max_bytes: int = MAX_BYTES_DEFAULT,
) -> bytes:
    """
    Read and validate an uploaded file.
    Returns file content bytes on success.
    Raises HTTPException on any policy violation.
    """
    # Filename safety
    if file.filename:
        file.filename = sanitize_filename(file.filename)

    # Read with size limit
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {max_bytes // (1024 * 1024)} MB.",
        )

    # MIME type check (declared)
    declared = file.content_type or ""
    if declared and declared not in allowed_types:
        log.warning("Upload rejected: declared MIME %s not in allowlist", declared)
        raise HTTPException(
            status_code=415,
            detail=f"File type '{declared}' is not allowed.",
        )

    # Magic byte verification
    if content:
        detected = _detect_mime_from_magic(content[:8])
        if detected and detected not in allowed_types:
            log.warning(
                "Upload rejected: magic-byte MIME %s mismatch with declared %s",
                detected, declared,
            )
            raise HTTPException(
                status_code=415,
                detail="File content does not match the declared file type.",
            )

    return content
