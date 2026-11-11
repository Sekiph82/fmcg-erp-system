"""Read-only GraphQL API (POST /api/v1/graphql).

Queries mirror the REST read endpoints for master data, orders and stock. Mutations are not
offered: writes stay on REST so every business rule has one implementation. REST applies
company/branch scope filters per record; GraphQL does not re-implement them, so transactional
data needs the company-wide ``*.view_all`` grant (or superuser) — scoped users use REST.
"""
from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from graphql import (
    GraphQLArgument, GraphQLBoolean, GraphQLError, GraphQLField, GraphQLFloat, GraphQLID, GraphQLInt,
    GraphQLList, GraphQLNonNull, GraphQLObjectType, GraphQLSchema, GraphQLString, graphql, parse, validate,
)
from graphql.language import FieldNode, FragmentSpreadNode, InlineFragmentNode, OperationDefinitionNode
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission
from app.core.deps import get_current_user, get_db
from app.models.inventory import Stock
from app.models.master import Material, Product, Supplier
from app.models.procurement import PurchaseOrder
from app.models.production import ProductionOrder
from app.models.sales import Customer, SalesOrder

router = APIRouter()

MAX_LIMIT = 200
MAX_DEPTH = 6
MAX_QUERY_CHARS = 10_000

# ── helpers ──────────────────────────────────────────────────────────────────


def _require(info, *codes: str) -> None:
    user = info.context["user"]
    if codes and not has_any_permission(user, codes):
        raise GraphQLError(f"Permission required: one of {', '.join(codes)}")


def _limit(value: Optional[int]) -> int:
    return max(1, min(int(value or 50), MAX_LIMIT))


def _val(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    if value is not None and type(value).__name__ == "UUID":
        return str(value)
    return value


def _field(attr: str, kind=GraphQLString) -> GraphQLField:
    return GraphQLField(kind, resolve=lambda obj, _info: _val(getattr(obj, attr)))


def _object(name: str, fields: dict[str, tuple[str, Any]]) -> GraphQLObjectType:
    return GraphQLObjectType(name, lambda: {k: _field(attr, kind) for k, (attr, kind) in fields.items()})


ProductType = _object("Product", {
    "id": ("id", GraphQLID), "sku": ("sku", GraphQLString), "name": ("name", GraphQLString),
    "category": ("category", GraphQLString), "uom": ("uom", GraphQLString), "barcode": ("barcode", GraphQLString),
    "sellingPrice": ("selling_price", GraphQLFloat), "isActive": ("is_active", GraphQLBoolean),
})
MaterialType = _object("Material", {
    "id": ("id", GraphQLID), "code": ("code", GraphQLString), "name": ("name", GraphQLString),
    "materialType": ("material_type", GraphQLString), "uom": ("uom", GraphQLString),
    "leadTimeDays": ("lead_time_days", GraphQLInt), "isActive": ("is_active", GraphQLBoolean),
})
CustomerType = _object("Customer", {
    "id": ("id", GraphQLID), "code": ("code", GraphQLString), "name": ("name", GraphQLString),
    "channel": ("channel", GraphQLString), "city": ("city", GraphQLString), "currency": ("currency", GraphQLString),
    "isActive": ("is_active", GraphQLBoolean),
})
SupplierType = _object("Supplier", {
    "id": ("id", GraphQLID), "code": ("code", GraphQLString), "name": ("name", GraphQLString),
    "qualificationStatus": ("qualification_status", GraphQLString), "riskLevel": ("risk_level", GraphQLString),
    "isActive": ("is_active", GraphQLBoolean),
})
SalesOrderType = _object("SalesOrder", {
    "id": ("id", GraphQLID), "orderNo": ("order_no", GraphQLString), "customerId": ("customer_id", GraphQLID),
    "orderDate": ("order_date", GraphQLString), "status": ("status", GraphQLString),
    "currency": ("currency", GraphQLString), "warehouseId": ("warehouse_id", GraphQLID),
})
PurchaseOrderType = _object("PurchaseOrder", {
    "id": ("id", GraphQLID), "poNo": ("po_no", GraphQLString), "supplierId": ("supplier_id", GraphQLID),
    "orderDate": ("order_date", GraphQLString), "expectedDeliveryDate": ("expected_delivery_date", GraphQLString),
    "status": ("status", GraphQLString), "currency": ("currency", GraphQLString),
})
ProductionOrderType = _object("ProductionOrder", {
    "id": ("id", GraphQLID), "orderNo": ("order_no", GraphQLString), "productId": ("product_id", GraphQLID),
    "status": ("status", GraphQLString), "plannedQuantity": ("planned_quantity", GraphQLFloat),
    "actualQuantity": ("actual_quantity", GraphQLFloat), "uom": ("uom", GraphQLString),
    "batchNo": ("batch_no", GraphQLString),
})
InventoryLevelType = _object("InventoryLevel", {
    "id": ("id", GraphQLID), "warehouseId": ("warehouse_id", GraphQLID), "productId": ("product_id", GraphQLID),
    "materialId": ("material_id", GraphQLID), "lotId": ("lot_id", GraphQLID),
    "quantityOnHand": ("quantity_on_hand", GraphQLFloat), "quantityAvailable": ("quantity_available", GraphQLFloat),
    "isBlocked": ("is_blocked", GraphQLBoolean),
})

PAGE = {"limit": GraphQLArgument(GraphQLInt), "offset": GraphQLArgument(GraphQLInt)}


async def _rows(info, query, limit=None, offset=None):
    # graphql-core resolves root fields concurrently; one AsyncSession allows one operation at a time.
    db: AsyncSession = info.context["db"]
    async with info.context["db_lock"]:
        result = await db.execute(query.limit(_limit(limit)).offset(max(0, int(offset or 0))))
        return list(result.scalars().all())


def _search(query, model, search: Optional[str], *columns):
    if search:
        pattern = f"%{search.strip()[:100]}%"
        from sqlalchemy import or_
        query = query.where(or_(*[getattr(model, c).ilike(pattern) for c in columns]))
    return query


async def resolve_products(_root, info, search=None, limit=None, offset=None):
    return await _rows(info, _search(select(Product).order_by(Product.sku), Product, search, "sku", "name"), limit, offset)


async def resolve_materials(_root, info, search=None, limit=None, offset=None):
    return await _rows(info, _search(select(Material).order_by(Material.code), Material, search, "code", "name"), limit, offset)


async def resolve_suppliers(_root, info, search=None, limit=None, offset=None):
    _require(info, "suppliers.view", "suppliers.view_all")
    return await _rows(info, _search(select(Supplier).order_by(Supplier.code), Supplier, search, "code", "name"), limit, offset)


async def resolve_customers(_root, info, search=None, limit=None, offset=None):
    _require(info, "sales.view_all", "crm.view_all")
    return await _rows(info, _search(select(Customer).order_by(Customer.code), Customer, search, "code", "name"), limit, offset)


async def resolve_customer(_root, info, id):
    _require(info, "sales.view_all", "crm.view_all")
    rows = await _rows(info, select(Customer).where(Customer.id == id), 1)
    return rows[0] if rows else None


async def resolve_sales_orders(_root, info, status=None, customerId=None, dateFrom=None, dateTo=None, limit=None, offset=None):
    _require(info, "sales.view_all")
    q = select(SalesOrder).order_by(SalesOrder.order_date.desc(), SalesOrder.order_no)
    if status:
        q = q.where(SalesOrder.status == status)
    if customerId:
        q = q.where(SalesOrder.customer_id == customerId)
    if dateFrom:
        q = q.where(SalesOrder.order_date >= date.fromisoformat(dateFrom))
    if dateTo:
        q = q.where(SalesOrder.order_date <= date.fromisoformat(dateTo))
    return await _rows(info, q, limit, offset)


async def resolve_purchase_orders(_root, info, status=None, supplierId=None, limit=None, offset=None):
    _require(info, "procurement.view_all")
    q = select(PurchaseOrder).order_by(PurchaseOrder.order_date.desc(), PurchaseOrder.po_no)
    if status:
        q = q.where(PurchaseOrder.status == status)
    if supplierId:
        q = q.where(PurchaseOrder.supplier_id == supplierId)
    return await _rows(info, q, limit, offset)


async def resolve_production_orders(_root, info, status=None, productId=None, limit=None, offset=None):
    _require(info, "production.view_all")
    q = select(ProductionOrder).order_by(ProductionOrder.scheduled_start.desc(), ProductionOrder.order_no)
    if status:
        q = q.where(ProductionOrder.status == status)
    if productId:
        q = q.where(ProductionOrder.product_id == productId)
    return await _rows(info, q, limit, offset)


async def resolve_inventory_levels(_root, info, warehouseId=None, sku=None, limit=None, offset=None):
    _require(info, "inventory.view_all")
    q = select(Stock).order_by(Stock.warehouse_id, Stock.id)
    if warehouseId:
        q = q.where(Stock.warehouse_id == warehouseId)
    if sku:
        q = q.join(Product, Product.id == Stock.product_id).where(Product.sku == sku)
    return await _rows(info, q, limit, offset)


def _list(kind):
    return GraphQLNonNull(GraphQLList(GraphQLNonNull(kind)))


QueryType = GraphQLObjectType("Query", lambda: {
    "products": GraphQLField(_list(ProductType), args={"search": GraphQLArgument(GraphQLString), **PAGE}, resolve=resolve_products),
    "materials": GraphQLField(_list(MaterialType), args={"search": GraphQLArgument(GraphQLString), **PAGE}, resolve=resolve_materials),
    "suppliers": GraphQLField(_list(SupplierType), args={"search": GraphQLArgument(GraphQLString), **PAGE}, resolve=resolve_suppliers),
    "customers": GraphQLField(_list(CustomerType), args={"search": GraphQLArgument(GraphQLString), **PAGE}, resolve=resolve_customers),
    "customer": GraphQLField(CustomerType, args={"id": GraphQLArgument(GraphQLNonNull(GraphQLID))}, resolve=resolve_customer),
    "salesOrders": GraphQLField(_list(SalesOrderType), args={
        "status": GraphQLArgument(GraphQLString), "customerId": GraphQLArgument(GraphQLID),
        "dateFrom": GraphQLArgument(GraphQLString), "dateTo": GraphQLArgument(GraphQLString), **PAGE},
        resolve=resolve_sales_orders),
    "purchaseOrders": GraphQLField(_list(PurchaseOrderType), args={
        "status": GraphQLArgument(GraphQLString), "supplierId": GraphQLArgument(GraphQLID), **PAGE},
        resolve=resolve_purchase_orders),
    "productionOrders": GraphQLField(_list(ProductionOrderType), args={
        "status": GraphQLArgument(GraphQLString), "productId": GraphQLArgument(GraphQLID), **PAGE},
        resolve=resolve_production_orders),
    "inventoryLevels": GraphQLField(_list(InventoryLevelType), args={
        "warehouseId": GraphQLArgument(GraphQLID), "sku": GraphQLArgument(GraphQLString), **PAGE},
        resolve=resolve_inventory_levels),
})

SCHEMA = GraphQLSchema(query=QueryType)


def _depth(node, fragments, seen=frozenset()) -> int:
    selection_set = getattr(node, "selection_set", None)
    if selection_set is None:
        return 0
    depths = []
    for sel in selection_set.selections:
        if isinstance(sel, FieldNode):
            depths.append(1 + _depth(sel, fragments, seen))
        elif isinstance(sel, InlineFragmentNode):
            depths.append(_depth(sel, fragments, seen))
        elif isinstance(sel, FragmentSpreadNode) and sel.name.value not in seen and sel.name.value in fragments:
            depths.append(_depth(fragments[sel.name.value], fragments, seen | {sel.name.value}))
    return max(depths, default=0)


def graphql_context(db: AsyncSession, user) -> dict[str, Any]:
    return {"db": db, "user": user, "db_lock": asyncio.Lock()}


class GraphQLRequest(BaseModel):
    query: str = Field(max_length=MAX_QUERY_CHARS)
    variables: Optional[dict[str, Any]] = None
    operationName: Optional[str] = None


@router.post("")
async def execute_graphql(
    body: GraphQLRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        document = parse(body.query)
    except GraphQLError as exc:
        return {"errors": [{"message": exc.message}]}
    if any(isinstance(d, OperationDefinitionNode) and d.operation.value != "query" for d in document.definitions):
        raise HTTPException(400, "Only queries are supported; use the REST API for changes.")
    errors = validate(SCHEMA, document)
    if errors:
        return {"errors": [{"message": e.message} for e in errors]}
    fragments = {d.name.value: d for d in document.definitions if d.kind == "fragment_definition"}
    if max((_depth(d, fragments) for d in document.definitions if isinstance(d, OperationDefinitionNode)), default=0) > MAX_DEPTH:
        raise HTTPException(400, f"Query depth exceeds {MAX_DEPTH}.")
    result = await graphql(SCHEMA, body.query, variable_values=body.variables, operation_name=body.operationName,
                           context_value=graphql_context(db, user))
    payload: dict[str, Any] = {"data": result.data}
    if result.errors:
        payload["errors"] = [{"message": e.message, "path": e.path} for e in result.errors]
    return payload
