"""
Integration API endpoints.
All external system interactions go through this router.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user, require_permission
from app.core.config import settings
from app.models.integrations import (
    IntegrationConfig, IntegrationLog, IntegrationMpesaTransaction,
    IntegrationProvider, IntegrationLogStatus, BarcodeLabel,
    CrmCustomerMapping, EcommerceOrderMapping, MachineEvent,
)
from app.schemas.integrations import (
    IntegrationConfigCreate, IntegrationConfigUpdate, IntegrationConfigRead,
    ProviderStatusRow,
    IntegrationLogRead,
    MpesaInitiateRequest, MpesaTransactionRead, MpesaCallbackPayload, MpesaStatusResponse,
    BarcodeGenerateRequest, BarcodeGenerateResponse, BarcodeScanRequest, BarcodeScanResult,
    BarcodeLabelRead, PrintRequest, PrintResponse,
    CrmSyncRequest, CrmSyncResult, CrmMappingRead,
    EcommerceImportRequest, EcommerceImportResult, EcommerceOrderMappingRead, InventorySyncResult,
    MachineEventCreate, MachineEventRead, MachineStatusRow,
)
from app.services import integration_service as svc
from app.services import mpesa_daraja_service as mpesa_svc
from app.services import barcode_service as barcode_svc
from app.services import crm_service as crm_svc
from app.services import ecommerce_service as ecomm_svc
from app.services import iot_service as iot_svc

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cfg_read(cfg: IntegrationConfig) -> IntegrationConfigRead:
    return IntegrationConfigRead(
        id=str(cfg.id),
        provider=cfg.provider,
        name=cfg.name,
        environment=cfg.environment,
        is_active=cfg.is_active,
        webhook_url=cfg.webhook_url,
        status=cfg.status,
        last_tested_at=cfg.last_tested_at,
        notes=cfg.notes,
        created_at=cfg.created_at,
    )


def _tx_read(tx: IntegrationMpesaTransaction) -> MpesaTransactionRead:
    return MpesaTransactionRead(
        id=str(tx.id),
        phone_number=tx.phone_number,
        amount=float(tx.amount),
        currency=tx.currency,
        merchant_reference=tx.merchant_reference,
        checkout_request_id=tx.checkout_request_id,
        mpesa_receipt_number=tx.mpesa_receipt_number,
        related_entity_type=tx.related_entity_type,
        related_entity_id=str(tx.related_entity_id) if tx.related_entity_id else None,
        status=tx.status,
        error_message=tx.error_message,
        result_code=tx.result_code,
        result_description=tx.result_description,
        retry_count=tx.retry_count,
        created_at=tx.created_at,
        updated_at=tx.updated_at,
    )


def _log_read(log: IntegrationLog, include_payloads: bool = False) -> IntegrationLogRead:
    return IntegrationLogRead(
        id=str(log.id),
        provider=log.provider,
        integration_type=log.integration_type,
        endpoint=log.endpoint,
        status=log.status,
        error_message=log.error_message,
        retry_count=log.retry_count,
        duration_ms=log.duration_ms,
        reference=log.reference,
        idempotency_key=log.idempotency_key,
        created_at=log.created_at,
        request_payload=log.request_payload if include_payloads else None,
        response_payload=log.response_payload if include_payloads else None,
    )


def _label_read(label: BarcodeLabel, svg: Optional[str] = None) -> BarcodeLabelRead:
    return BarcodeLabelRead(
        id=str(label.id),
        entity_type=label.entity_type,
        entity_id=str(label.entity_id),
        entity_name=label.entity_name,
        barcode_value=label.barcode_value,
        barcode_format=label.barcode_format,
        label_template=label.label_template,
        print_count=label.print_count,
        last_printed_at=label.last_printed_at,
        created_at=label.created_at,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/configs", response_model=List[IntegrationConfigRead],
            dependencies=[Depends(require_permission("integrations", "view"))])
async def list_configs(
    db: AsyncSession = Depends(get_db),
):
    configs = await svc.list_configs(db)
    return [_cfg_read(c) for c in configs]


@router.post("/configs", response_model=IntegrationConfigRead, status_code=201,
             dependencies=[Depends(require_permission("integrations", "edit"))])
async def create_config(
    body: IntegrationConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    cfg = await svc.create_config(db, body.model_dump())
    await db.commit()
    cfg = (await db.execute(select(IntegrationConfig).where(IntegrationConfig.id == cfg.id))).scalar_one()
    return _cfg_read(cfg)


@router.patch("/configs/{config_id}", response_model=IntegrationConfigRead,
              dependencies=[Depends(require_permission("integrations", "edit"))])
async def update_config(
    config_id: uuid.UUID,
    body: IntegrationConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    cfg = (await db.execute(select(IntegrationConfig).where(IntegrationConfig.id == config_id))).scalar_one_or_none()
    if not cfg:
        raise HTTPException(404, "Config not found")
    cfg = await svc.update_config(db, cfg, body.model_dump(exclude_none=True))
    await db.commit()
    return _cfg_read(cfg)


@router.get("/providers", response_model=List[ProviderStatusRow],
            dependencies=[Depends(require_permission("integrations", "view"))])
async def provider_summary(
    db: AsyncSession = Depends(get_db),
):
    """Dashboard overview — status + recent stats for all providers."""
    rows: List[ProviderStatusRow] = []
    configs = await svc.list_configs(db)
    cfg_by_provider = {c.provider: c for c in configs}

    for provider in IntegrationProvider:
        cfg = cfg_by_provider.get(provider)
        stats = await svc.get_provider_stats(db, provider, hours=24)
        rows.append(ProviderStatusRow(
            provider=provider,
            name=cfg.name if cfg else provider.value,
            status=cfg.status if cfg else "INACTIVE",
            environment=cfg.environment if cfg else "—",
            is_active=cfg.is_active if cfg else False,
            last_tested_at=cfg.last_tested_at if cfg else None,
            recent_success=stats["success"],
            recent_failures=stats["failed"],
        ))
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION LOGS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/logs", response_model=List[IntegrationLogRead],
            dependencies=[Depends(require_permission("integrations", "view"))])
async def list_logs(
    provider: Optional[IntegrationProvider] = None,
    status: Optional[IntegrationLogStatus] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    logs = await svc.list_logs(db, provider=provider, status=status, limit=limit, offset=offset)
    return [_log_read(log) for log in logs]


@router.get("/logs/{log_id}", response_model=IntegrationLogRead,
            dependencies=[Depends(require_permission("integrations", "view"))])
async def get_log(
    log_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    log = (await db.execute(select(IntegrationLog).where(IntegrationLog.id == log_id))).scalar_one_or_none()
    if not log:
        raise HTTPException(404, "Log not found")
    return _log_read(log, include_payloads=True)


# ═══════════════════════════════════════════════════════════════════════════════
# M-PESA
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/mpesa/initiate", response_model=MpesaTransactionRead, status_code=201)
async def initiate_mpesa_payment(
    body: MpesaInitiateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("mpesa", "initiate_payment")),
):
    """
    Initiate an M-Pesa STK Push payment.
    Uses real Daraja API when credentials are configured; sandbox simulation otherwise.
    """
    tx = await mpesa_svc.initiate_payment(
        db=db,
        phone_number=body.phone_number,
        amount=body.amount,
        merchant_reference=body.merchant_reference,
        related_entity_type=body.related_entity_type,
        related_entity_id=body.related_entity_id,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(tx)
    return _tx_read(tx)


@router.get("/mpesa/transactions", response_model=List[MpesaTransactionRead],
            dependencies=[Depends(require_permission("mpesa", "view_transactions"))])
async def list_mpesa_transactions(
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    from app.models.integrations import MpesaTxStatus
    q = select(IntegrationMpesaTransaction).order_by(IntegrationMpesaTransaction.created_at.desc())
    if status:
        q = q.where(IntegrationMpesaTransaction.status == MpesaTxStatus(status))
    result = await db.execute(q.limit(limit))
    return [_tx_read(tx) for tx in result.scalars().all()]


@router.get("/mpesa/transactions/{transaction_id}", response_model=MpesaTransactionRead,
            dependencies=[Depends(require_permission("mpesa", "view_transactions"))])
async def get_mpesa_transaction(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    tx = (await db.execute(
        select(IntegrationMpesaTransaction).where(IntegrationMpesaTransaction.id == transaction_id)
    )).scalar_one_or_none()
    if not tx:
        raise HTTPException(404, "Transaction not found")
    return _tx_read(tx)


@router.post("/mpesa/transactions/{transaction_id}/retry", response_model=MpesaTransactionRead)
async def retry_mpesa_transaction(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("mpesa", "retry_transaction")),
):
    tx = await mpesa_svc.retry_transaction(db, transaction_id, user_id=current_user.id)
    await db.commit()
    await db.refresh(tx)
    return _tx_read(tx)


@router.get("/mpesa/transactions/{transaction_id}/status", response_model=MpesaStatusResponse,
            dependencies=[Depends(require_permission("mpesa", "view_transactions"))])
async def check_mpesa_status(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    tx = await mpesa_svc.check_transaction_status(db, transaction_id)
    await db.commit()
    return MpesaStatusResponse(
        transaction_id=str(tx.id),
        checkout_request_id=tx.checkout_request_id,
        status=tx.status,
        mpesa_receipt_number=tx.mpesa_receipt_number,
        amount=float(tx.amount),
        message=tx.result_description or tx.status.value,
    )


@router.post("/mpesa/callback", status_code=200)
async def mpesa_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Daraja STK Push callback endpoint.
    This URL must be publicly reachable and configured in MPESA_CALLBACK_URL.
    No authentication — Safaricom calls this directly.
    Idempotent: duplicate callbacks are safely ignored.
    """
    payload = await request.json()
    await mpesa_svc.handle_callback(db, payload)
    await db.commit()
    # Daraja expects this exact response on success
    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@router.get("/mpesa/config",
            dependencies=[Depends(require_permission("integrations", "view"))])
async def mpesa_config_status():
    """Return M-Pesa configuration status (no secrets exposed)."""
    return {
        "configured": settings.MPESA_CONFIGURED,
        "environment": settings.MPESA_ENV,
        "shortcode": settings.MPESA_SHORTCODE or "— not set —",
        "callback_url": settings.MPESA_CALLBACK_URL,
        "transaction_type": settings.MPESA_TRANSACTION_TYPE,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# BARCODE
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/barcode/generate", response_model=BarcodeGenerateResponse, status_code=201,
             dependencies=[Depends(require_permission("integrations", "edit"))])
async def generate_barcode(
    body: BarcodeGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    label = await barcode_svc.generate_barcode(
        db,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        barcode_format=body.barcode_format,
        label_template=body.label_template,
    )
    await db.commit()
    await db.refresh(label)
    svg = barcode_svc._build_svg(label.barcode_value)
    return BarcodeGenerateResponse(
        barcode_value=label.barcode_value,
        barcode_format=label.barcode_format,
        entity_type=label.entity_type,
        entity_id=str(label.entity_id),
        entity_name=label.entity_name,
        svg_data=svg,
        label_id=str(label.id),
    )


@router.post("/barcode/scan", response_model=BarcodeScanResult,
             dependencies=[Depends(require_permission("integrations", "view"))])
async def scan_barcode(
    body: BarcodeScanRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await barcode_svc.scan_barcode(db, body.barcode_value)
    if not result:
        raise HTTPException(404, f"Barcode '{body.barcode_value}' not found")
    return BarcodeScanResult(**result)


@router.get("/barcode/labels", response_model=List[BarcodeLabelRead],
            dependencies=[Depends(require_permission("integrations", "view"))])
async def list_barcode_labels(
    entity_type: Optional[str] = None,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    labels = await barcode_svc.list_labels(db, entity_type=entity_type, limit=limit)
    return [_label_read(l) for l in labels]


@router.post("/barcode/print", response_model=PrintResponse,
             dependencies=[Depends(require_permission("integrations", "edit"))])
async def print_label(
    body: PrintRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Enqueue a label for printing.
    PLACEHOLDER: records the print request and increments print counter.
    Connect to a ZPL/EPL printer SDK or cloud print service in production.
    """
    label = await barcode_svc.get_label(db, uuid.UUID(body.label_id))
    if not label:
        raise HTTPException(404, "Label not found")
    await barcode_svc.record_print(db, label)
    await db.commit()
    return PrintResponse(
        job_id=f"PRINT-{str(label.id)[:8].upper()}",
        label_id=body.label_id,
        printer_name=body.printer_name or "default",
        copies=body.copies,
        status="queued",
        message="Print job queued (placeholder — connect to printer SDK for live printing)",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CRM
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/crm/sync/customers", response_model=CrmSyncResult,
             dependencies=[Depends(require_permission("integrations", "edit"))])
async def sync_crm_customers(
    body: CrmSyncRequest,
    db: AsyncSession = Depends(get_db),
):
    total, synced, errors = await crm_svc.sync_customers(
        db,
        direction=body.direction,
        customer_ids=body.customer_ids,
    )
    await db.commit()
    return CrmSyncResult(total=total, synced=synced, failed=len(errors), errors=errors[:10])


@router.get("/crm/mappings", response_model=List[CrmMappingRead],
            dependencies=[Depends(require_permission("integrations", "view"))])
async def list_crm_mappings(
    db: AsyncSession = Depends(get_db),
):
    mappings = await crm_svc.list_mappings(db)
    return [
        CrmMappingRead(
            id=str(m.id),
            customer_id=str(m.customer_id),
            crm_provider=m.crm_provider,
            external_crm_id=m.external_crm_id,
            sync_status=m.sync_status,
            sync_direction=m.sync_direction,
            last_sync_at=m.last_sync_at,
            created_at=m.created_at,
        )
        for m in mappings
    ]


@router.get("/crm/status",
            dependencies=[Depends(require_permission("integrations", "view"))])
async def crm_status(
    db: AsyncSession = Depends(get_db),
):
    cfg = await svc.get_config(db, IntegrationProvider.CRM)
    stats = await svc.get_provider_stats(db, IntegrationProvider.CRM, hours=24)
    return {
        "configured": cfg is not None,
        "active": cfg.is_active if cfg else False,
        "environment": cfg.environment if cfg else "—",
        "stats_24h": stats,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# E-COMMERCE
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/ecommerce/import-orders", response_model=EcommerceImportResult,
             dependencies=[Depends(require_permission("integrations", "edit"))])
async def import_ecommerce_orders(
    body: EcommerceImportRequest,
    db: AsyncSession = Depends(get_db),
):
    imported, mapped, errors = await ecomm_svc.import_orders(
        db, platform=body.platform, since_date=body.since_date, limit=body.limit
    )
    await db.commit()
    return EcommerceImportResult(
        platform=body.platform, imported=imported, mapped=mapped,
        failed=len(errors), errors=errors[:10]
    )


@router.post("/ecommerce/sync-inventory", response_model=InventorySyncResult,
             dependencies=[Depends(require_permission("integrations", "edit"))])
async def sync_ecommerce_inventory(
    platform: str = Query(..., description="SHOPIFY | WOOCOMMERCE"),
    db: AsyncSession = Depends(get_db),
):
    total, synced, errors = await ecomm_svc.sync_inventory(db, platform=platform)
    await db.commit()
    return InventorySyncResult(
        platform=platform, products_synced=synced,
        failed=len(errors), errors=errors[:10]
    )


@router.get("/ecommerce/orders", response_model=List[EcommerceOrderMappingRead],
            dependencies=[Depends(require_permission("integrations", "view"))])
async def list_ecommerce_orders(
    db: AsyncSession = Depends(get_db),
):
    mappings = await ecomm_svc.list_order_mappings(db)
    return [
        EcommerceOrderMappingRead(
            id=str(m.id),
            source_platform=m.source_platform,
            external_order_id=m.external_order_id,
            external_order_no=m.external_order_no,
            so_id=str(m.so_id) if m.so_id else None,
            sync_status=m.sync_status,
            error_message=m.error_message,
            last_sync_at=m.last_sync_at,
            created_at=m.created_at,
        )
        for m in mappings
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# IoT / MACHINE
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/iot/events", response_model=MachineEventRead, status_code=201)
async def ingest_machine_event(
    body: MachineEventCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Receive a single machine event.
    No auth required (machine tokens handled at network layer — placeholder).
    """
    event = await iot_svc.ingest_event(
        db,
        machine_id=body.machine_id,
        event_type=body.event_type,
        value_str=body.value_str,
        value_numeric=body.value_numeric,
        unit=body.unit,
        machine_name=body.machine_name,
        production_order_id=body.production_order_id,
        received_at=body.received_at,
        raw_payload=body.raw_payload,
    )
    await db.commit()
    return MachineEventRead(
        id=str(event.id),
        machine_id=event.machine_id,
        machine_name=event.machine_name,
        event_type=event.event_type,
        value_str=event.value_str,
        value_numeric=float(event.value_numeric) if event.value_numeric is not None else None,
        unit=event.unit,
        production_order_id=str(event.production_order_id) if event.production_order_id else None,
        received_at=event.received_at,
        created_at=event.created_at,
    )


@router.get("/iot/events", response_model=List[MachineEventRead],
            dependencies=[Depends(require_permission("integrations", "view"))])
async def list_machine_events(
    machine_id: Optional[str] = None,
    event_type: Optional[str] = None,
    hours: int = Query(24, le=168),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    events = await iot_svc.list_events(db, machine_id=machine_id, event_type=event_type, hours=hours, limit=limit)
    return [
        MachineEventRead(
            id=str(e.id),
            machine_id=e.machine_id,
            machine_name=e.machine_name,
            event_type=e.event_type,
            value_str=e.value_str,
            value_numeric=float(e.value_numeric) if e.value_numeric is not None else None,
            unit=e.unit,
            production_order_id=str(e.production_order_id) if e.production_order_id else None,
            received_at=e.received_at,
            created_at=e.created_at,
        )
        for e in events
    ]


@router.get("/iot/machines", response_model=List[MachineStatusRow],
            dependencies=[Depends(require_permission("integrations", "view"))])
async def machine_status(
    db: AsyncSession = Depends(get_db),
):
    rows = await iot_svc.get_machine_status_summary(db)
    return [MachineStatusRow(**r) for r in rows]


# ═══════════════════════════════════════════════════════════════════════════════
# MARKETING SYNC HOOKS (placeholders — swap body for real API calls in v2)
# ═══════════════════════════════════════════════════════════════════════════════

from app.models.integrations import IntegrationStatus
from pydantic import BaseModel as _BaseModel


class MarketingSyncStatus(_BaseModel):
    provider: str
    status: str
    message: str
    records_synced: int
    last_sync: Optional[str]


@router.post("/marketing/ads-sync",
             dependencies=[Depends(require_permission("integrations", "edit"))])
async def sync_ads_performance(
    provider: str = Query("META_ADS", description="META_ADS | GOOGLE_ADS | TIKTOK_ADS"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Placeholder: trigger an ads performance sync from the given ad platform.
    In v2: call provider API, upsert AdPerformance rows, log to IntegrationLog.
    """
    log = IntegrationLog(
        provider=provider,
        integration_type="ads_sync",
        endpoint=f"/integrations/marketing/ads-sync?provider={provider}",
        status=IntegrationLogStatus.PENDING,
        reference=f"ads_sync_{provider.lower()}",
    )
    db.add(log)
    await db.commit()
    return MarketingSyncStatus(
        provider=provider,
        status="PENDING",
        message="Ads sync queued. Connect ad platform credentials in Integration Config to activate.",
        records_synced=0,
        last_sync=None,
    )


@router.post("/marketing/social-sync",
             dependencies=[Depends(require_permission("integrations", "edit"))])
async def sync_social_analytics(
    provider: str = Query("SOCIAL_ANALYTICS", description="SOCIAL_ANALYTICS | ECOMMERCE_ANALYTICS"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Placeholder: trigger a social media analytics sync.
    In v2: call social API, upsert SocialMediaActivity rows.
    """
    log = IntegrationLog(
        provider=provider,
        integration_type="social_sync",
        endpoint=f"/integrations/marketing/social-sync?provider={provider}",
        status=IntegrationLogStatus.PENDING,
        reference=f"social_sync_{provider.lower()}",
    )
    db.add(log)
    await db.commit()
    return MarketingSyncStatus(
        provider=provider,
        status="PENDING",
        message="Social sync queued. Connect social analytics credentials to activate.",
        records_synced=0,
        last_sync=None,
    )


@router.post("/marketing/ecommerce-sync",
             dependencies=[Depends(require_permission("integrations", "edit"))])
async def sync_ecommerce_analytics(
    provider: str = Query("SHOPIFY", description="SHOPIFY | WOOCOMMERCE | ECOMMERCE_ANALYTICS"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Placeholder: trigger an e-commerce store performance sync.
    In v2: fetch orders and performance metrics, upsert StorePerformance rows.
    """
    log = IntegrationLog(
        provider=provider,
        integration_type="ecommerce_sync",
        endpoint=f"/integrations/marketing/ecommerce-sync?provider={provider}",
        status=IntegrationLogStatus.PENDING,
        reference=f"ecomm_sync_{provider.lower()}",
    )
    db.add(log)
    await db.commit()
    return MarketingSyncStatus(
        provider=provider,
        status="PENDING",
        message="E-commerce sync queued. Configure store credentials to activate.",
        records_synced=0,
        last_sync=None,
    )


@router.get("/marketing/sync-status",
            dependencies=[Depends(require_permission("integrations", "view"))])
async def marketing_sync_status(db: AsyncSession = Depends(get_db)):
    """
    Returns the last known sync status for all marketing integration providers.
    """
    marketing_providers = ["META_ADS", "GOOGLE_ADS", "TIKTOK_ADS", "SOCIAL_ANALYTICS",
                           "ECOMMERCE_ANALYTICS", "CRM", "SHOPIFY", "WOOCOMMERCE"]
    results = []
    for prov in marketing_providers:
        last_log = (await db.execute(
            select(IntegrationLog)
            .where(IntegrationLog.provider == prov)
            .order_by(IntegrationLog.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()
        results.append({
            "provider": prov,
            "status": last_log.status.value if last_log else "NOT_CONFIGURED",
            "last_sync": str(last_log.created_at) if last_log else None,
            "error": last_log.error_message if last_log else None,
        })
    return results
