"""M36.S04.T004 ticket attachments on the shared document storage (opaque keys, type/size/content checks,
fail-closed ClamAV scan). A file is downloadable only when its scan is CLEAN; INFECTED uploads are deleted
and refused; NOT_SCANNED / ERROR stay quarantined (visible in the list, not downloadable)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.helpdesk import TicketAttachment

MAX_PER_TICKET = 10
MAX_BYTES = 10 * 1024 * 1024


async def add(db: AsyncSession, ticket_id: UUID, upload: UploadFile, *, from_customer: bool,
              portal_user_id: Optional[UUID] = None, uploaded_by_id: Optional[UUID] = None,
              customer_visible: bool = False) -> TicketAttachment:
    from app.services.document_storage_service import get_document_storage, scan_document

    from app.models.helpdesk import HelpdeskTicket

    await db.execute(select(HelpdeskTicket.id).where(HelpdeskTicket.id == ticket_id).with_for_update())  # serialise the limit
    count = (await db.execute(select(func.count()).select_from(TicketAttachment)
                              .where(TicketAttachment.ticket_id == ticket_id))).scalar_one()
    if count >= MAX_PER_TICKET:
        raise HTTPException(409, f"A ticket can hold at most {MAX_PER_TICKET} files.")
    storage = get_document_storage()
    stored = await storage.store_upload(upload, max_bytes=MAX_BYTES)
    scan = await scan_document(storage.path_for(stored.storage_key))
    if scan.status == "INFECTED":
        storage.delete(stored.storage_key)
        raise HTTPException(422, "The file was rejected by the malware scanner.")
    att = TicketAttachment(ticket_id=ticket_id, storage_key=stored.storage_key, file_name=stored.file_name,
                           file_size_bytes=stored.file_size_bytes, mime_type=stored.mime_type, sha256=stored.sha256,
                           scan_status=scan.status, from_customer=from_customer, portal_user_id=portal_user_id,
                           uploaded_by_id=uploaded_by_id, customer_visible=from_customer or customer_visible,
                           created_at=datetime.now(timezone.utc))
    db.add(att)
    try:
        await db.flush()
    except Exception:
        storage.delete(stored.storage_key)  # no orphan file when the record cannot be saved
        raise
    return att


def out(a: TicketAttachment) -> dict:
    return {"id": str(a.id), "file_name": a.file_name, "size": a.file_size_bytes, "type": a.mime_type,
            "from_customer": a.from_customer, "customer_visible": a.customer_visible, "scan_status": a.scan_status,
            "downloadable": a.scan_status == "CLEAN", "created_at": a.created_at.isoformat()}


def download(a: TicketAttachment) -> FileResponse:
    from app.services.document_storage_service import get_document_storage

    if a.scan_status != "CLEAN":
        raise HTTPException(409, f"File not released: malware scan status {a.scan_status}")
    path = get_document_storage().path_for(a.storage_key)
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(path, media_type=a.mime_type, filename=a.file_name,
                        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})
