"""MCP server for ERP/CRM tools (M45.S01.T022). POST /api/v1/public/mcp — Model Context Protocol over Streamable HTTP
(JSON-RPC 2.0, JSON responses, no server-initiated streams).

Auth: Authorization: Bearer <personal access token> with scope mcp.read (reads) / mcp.write (proposals).
Every tool runs as the token's user: the same permissions and company/branch scope as in the app.
Write tools never change data: they create an approval request that a different person approves in the app.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import can_view_record, has_any_permission
from app.core.deps import get_db
from app.services import pat_service as pats

router = APIRouter()
PROTOCOL = "2025-06-18"


class ToolError(Exception):
    pass


def _need(user, perms: tuple[str, ...]) -> None:
    if not has_any_permission(user, perms):
        raise ToolError(f"Your account has no permission for this ({' or '.join(perms)}).")


async def t_search_customers(db, user, args) -> Any:
    from app.models.sales import Customer
    _need(user, ("sales.view", "crm.view"))
    q = str(args.get("query") or "").strip()
    if len(q) < 2:
        raise ToolError("query needs at least 2 characters.")
    rows = (await db.execute(select(Customer).where(or_(Customer.name.ilike(f"%{q}%"), Customer.code.ilike(f"%{q}%")))
                             .order_by(Customer.name).limit(25))).scalars()
    return [{"code": c.code, "name": c.name, "city": c.city, "channel": getattr(c.channel, "value", c.channel),
             "active": c.is_active} for c in rows if can_view_record(user, "sales", c)][:10]


async def t_order_status(db, user, args) -> Any:
    from app.models.sales import Customer, SalesOrder
    _need(user, ("sales.view",))
    so = (await db.execute(select(SalesOrder).where(SalesOrder.order_no == str(args.get("order_no") or "")))).scalar_one_or_none()
    if so is None or not can_view_record(user, "sales", so):
        raise ToolError("Order not found.")
    cust = await db.get(Customer, so.customer_id)
    return {"order_no": so.order_no, "customer": cust.name if cust else None, "status": so.status.value,
            "order_date": so.order_date.isoformat(), "requested_delivery_date": so.requested_delivery_date.isoformat(),
            "payment_status": so.payment_status.value}


async def t_stock_level(db, user, args) -> Any:
    from app.models.inventory import Stock
    from app.models.master import Product
    _need(user, ("inventory.view",))
    p = (await db.execute(select(Product).where(Product.sku == str(args.get("sku") or "")))).scalar_one_or_none()
    if p is None:
        raise ToolError("Product not found.")
    rows = list((await db.execute(select(Stock).where(Stock.product_id == p.id, Stock.is_blocked.is_(False)))).scalars())
    rows = [s for s in rows if can_view_record(user, "inventory", s)]
    return {"sku": p.sku, "name": p.name, "on_hand": float(sum(s.quantity_on_hand for s in rows)),
            "available": float(sum(s.quantity_available for s in rows)), "locations": len(rows)}


async def t_invoice_status(db, user, args) -> Any:
    from app.models.sales import Invoice
    _need(user, ("finance.view", "sales.view"))
    inv = (await db.execute(select(Invoice).where(Invoice.invoice_no == str(args.get("invoice_no") or "")))).scalar_one_or_none()
    if inv is None or not can_view_record(user, "sales", inv):
        raise ToolError("Invoice not found.")
    return {"invoice_no": inv.invoice_no, "status": inv.status.value, "due_date": inv.due_date.isoformat(),
            "total": str(inv.total_amount), "paid": str(inv.paid_amount), "currency": inv.currency}


async def t_propose_task(db, user, args, token) -> Any:
    from app.models.crm import CRMRecord
    _need(user, ("crm.edit", "crm.edit_all"))
    try:
        rid = uuid.UUID(str(args.get("crm_record_id")))
    except ValueError:
        raise ToolError("crm_record_id must be a UUID.")
    rec = await db.get(CRMRecord, rid)
    all_ = user.is_superuser or has_any_permission(user, ("crm.view_all", "crm.edit_all"))
    if rec is None or not (all_ or rec.assigned_rep_id == str(user.id)):   # same rule as the CRM screens
        raise ToolError("CRM record not found.")
    subject = str(args.get("subject") or "").strip()[:200]
    if not subject:
        raise ToolError("subject is required.")
    req = await pats.propose(db, source="MCP", source_ref=str(token.id), user=user, action="create_task",
                             arguments={"crm_record_id": str(rid), "subject": subject, "note": str(args.get("note") or "")[:2000],
                                        "due_date": args.get("due_date")},
                             summary=f"Task '{subject}' on {rec.company_name}")
    return {"approval_request_id": str(req.id), "status": "PENDING",
            "message": "Nothing was changed. A colleague must approve this in the ERP (AI requests)."}


TOOLS = {
    "search_customers": (t_search_customers, "mcp.read", "Find customers by name or code (max 10).",
                         {"query": {"type": "string", "minLength": 2}}, ["query"]),
    "order_status": (t_order_status, "mcp.read", "Status, dates and payment status of a sales order.",
                     {"order_no": {"type": "string"}}, ["order_no"]),
    "stock_level": (t_stock_level, "mcp.read", "On-hand and available stock for a product SKU.",
                    {"sku": {"type": "string"}}, ["sku"]),
    "invoice_status": (t_invoice_status, "mcp.read", "Status, due date and amounts of an invoice.",
                       {"invoice_no": {"type": "string"}}, ["invoice_no"]),
    "propose_follow_up_task": (t_propose_task, "mcp.write",
                               "Propose a follow-up task on a CRM record. Creates an approval request only.",
                               {"crm_record_id": {"type": "string"}, "subject": {"type": "string"},
                                "note": {"type": "string"}, "due_date": {"type": "string", "format": "date-time"}},
                               ["crm_record_id", "subject"]),
}


def _ok(rid, result) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def _err(rid, code: int, msg: str) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": msg}}


async def _handle(db: AsyncSession, msg: dict, user, token) -> dict | None:
    rid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if method is None or msg.get("jsonrpc") != "2.0":
        return _err(rid, -32600, "Invalid request")
    if rid is None:                       # notification (e.g. notifications/initialized): no response
        return None
    if method == "initialize":
        return _ok(rid, {"protocolVersion": PROTOCOL, "capabilities": {"tools": {"listChanged": False}},
                         "serverInfo": {"name": "fmcg-erp", "version": "1.0"},
                         "instructions": "Reads respect your ERP permissions. Writes only create approval requests."})
    if method == "ping":
        return _ok(rid, {})
    if method == "tools/list":
        return _ok(rid, {"tools": [{"name": n, "description": d, "inputSchema": {"type": "object", "properties": props,
                                                                                 "required": req}}
                                   for n, (_, scope, d, props, req) in TOOLS.items() if scope in token.scopes]})
    if method == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        if name not in TOOLS:
            return _err(rid, -32602, f"Unknown tool: {name}")
        fn, scope, *_ = TOOLS[name]
        if scope not in token.scopes:
            return _ok(rid, {"isError": True, "content": [{"type": "text", "text": f"This token lacks the {scope} scope."}]})
        try:
            data = await (fn(db, user, args, token) if scope == "mcp.write" else fn(db, user, args))
        except ToolError as e:
            pats.audit(db, user, "MCP_TOOL_REFUSED", "mcp_tool", name, {"token": str(token.id), "reason": str(e)})
            return _ok(rid, {"isError": True, "content": [{"type": "text", "text": str(e)}]})
        pats.audit(db, user, "MCP_TOOL_CALL", "mcp_tool", name, {"token": str(token.id), "args": {k: str(v)[:100] for k, v in args.items()}})
        import json
        return _ok(rid, {"content": [{"type": "text", "text": json.dumps(data, default=str)}], "structuredContent":
                         data if isinstance(data, dict) else {"items": data}, "isError": False})
    return _err(rid, -32601, f"Method not found: {method}")


@router.post("")
async def mcp(request: Request, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    user, token = await pats.authenticate(db, authorization, "mcp.read")
    try:
        body = await request.json()
    except ValueError:
        return JSONResponse(_err(None, -32700, "Parse error"), status_code=400)
    msgs = body if isinstance(body, list) else [body]
    out = [r for m in msgs if isinstance(m, dict) for r in [await _handle(db, m, user, token)] if r is not None]
    await db.commit()
    if not out:
        return Response(status_code=202)
    return JSONResponse(out if isinstance(body, list) else out[0])


@router.get("")
async def no_stream():
    return Response(status_code=405, headers={"Allow": "POST"})
