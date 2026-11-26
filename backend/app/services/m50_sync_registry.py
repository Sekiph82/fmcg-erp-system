"""M50.S01.T009 data-sync registry: every ERP object a no-code sync may touch, with typed fields, natural keys,
dependencies and, above all, what a sync may do to it.

mode "write"      master data upserted directly (RBAC per target, controlled fields admin-only);
mode "propose"    sales/purchase orders: an inbound row is only STAGED; a second person with the domain create right
                  approves it and the document is created as a DRAFT through the domain's own create function;
mode "read_only"  stock and posted finance: outbound only. An inbound sync is refused when it is defined and again when
                  it runs. Stock moves only through inventory documents, finance only through posting/reversal.

Field kinds: text, email, phone, integer, number, bool, date, enum:<ClassName>, ref (a natural key that is resolved to the
related record's id; the related target must be synced first).
Pure data: no imports of the sync service (it imports this module).
"""
from __future__ import annotations

# virtual (non-column) inbound fields resolved to ids: field -> (column, referenced target)
REFS_CUSTOMER = {"customer_code": ("customer_id", "customers")}

EXTRA_TARGETS: dict[str, dict] = {
    "suppliers": {"model": ("app.models.master", "Supplier"), "key": "code", "perm": ("procurement.edit", "procurement.create"),
                  "view_perm": ("procurement.view_all", "procurement.view"),
                  "fields": {"code": "text", "name": "text", "contact_person": "text", "email": "email", "phone": "phone",
                             "address": "text", "city": "text", "country": "text", "tax_id": "text",
                             "payment_terms_days": "integer", "lead_time_days": "integer", "is_active": "bool"},
                  "required": ["code", "name"], "defaults": {}},
    "products": {"model": ("app.models.master", "Product"), "key": "sku", "perm": ("products.edit", "products.create"),
                 "view_perm": ("products.view", "inventory.view"),
                 "fields": {"sku": "text", "barcode": "text", "name": "text", "description": "text",
                            "category": "enum:ProductCategory", "uom": "enum:UnitOfMeasure", "units_per_carton": "integer",
                            "weight_kg": "number", "shelf_life_days": "integer", "reorder_point": "number",
                            "standard_cost": "number", "standard_cost_currency": "text", "selling_price": "number",
                            "is_active": "bool"},
                 "required": ["sku", "name", "category"], "defaults": {}},
    "materials": {"model": ("app.models.master", "Material"), "key": "code", "perm": ("inventory.edit", "inventory.create"),
                  "view_perm": ("inventory.view", "materials.view"),
                  "fields": {"code": "text", "name": "text", "description": "text", "material_type": "enum:MaterialType",
                             "uom": "enum:UnitOfMeasure", "weight_kg": "number", "reorder_point": "number",
                             "minimum_order_qty": "number", "standard_cost": "number", "lead_time_days": "integer",
                             "is_active": "bool", "supplier_code": "ref"},
                  "refs": {"supplier_code": ("supplier_id", "suppliers")},
                  "required": ["code", "name", "material_type"], "defaults": {}},
    "deals": {"model": ("app.models.crm", "CRMRecord"), "key": "opportunity_code", "perm": ("crm.edit_all",),
              "view_perm": ("crm.view_all", "crm.edit_all"),
              "fields": {"opportunity_code": "text", "company_name": "text", "contact_person_name": "text",
                         "contact_email": "email", "contact_phone": "phone", "expected_revenue": "number",
                         "expected_close_date": "date", "currency": "text", "industry_segment": "text"},
              "required": ["opportunity_code", "company_name"], "defaults": {"record_type": "OPPORTUNITY"}},   # str → enum member on write
    "tickets": {"model": ("app.models.helpdesk", "HelpdeskTicket"), "key": "ticket_no", "perm": ("crm.edit_all", "helpdesk.edit_all"),
                "view_perm": ("crm.view_all", "helpdesk.view_all"),
                "fields": {"ticket_no": "text", "subject": "text", "description": "text", "priority": "enum:TicketPriority",
                           "category": "enum:TicketCategory", "customer_code": "ref"},
                "refs": REFS_CUSTOMER, "required": ["ticket_no", "subject"], "defaults": {}},
    # a custom object type's fields come from its definition (adapter "co"); the sync's options name the type
    "custom_objects": {"adapter": "co", "key": "(display field)", "perm": ("crm.edit", "crm.edit_all", "sales.edit"),
                       "view_perm": ("crm.view", "crm.view_all", "sales.view"), "fields": {}, "required": [], "defaults": {}},
    # links between records, e.g. a contact to a customer or a custom-object record to a deal (adapter "assoc")
    "associations": {"adapter": "assoc", "key": "link", "perm": ("crm.edit", "crm.edit_all"), "view_perm": ("crm.view", "crm.view_all"),
                     "fields": {"from_key": "text", "to_type": "text", "to_key": "text", "label": "text"},
                     "required": ["from_key", "to_type", "to_key"], "defaults": {}},
    # transactional: inbound = proposals needing a second person; outbound = read of the documents with their lines
    "sales_orders": {"mode": "propose", "model": ("app.models.sales", "SalesOrder"), "key": "order_no",
                     "perm": ("sales.create",), "view_perm": ("sales.view_all", "crm.view_all"),
                     "fields": {"order_no": "text", "customer_code": "ref", "order_date": "date", "requested_delivery_date": "date",
                                "currency": "text", "notes": "text", "sku": "text", "quantity": "number", "unit_price": "number",
                                "discount_pct": "number", "tax_rate": "number", "unit": "text", "status": "text"},
                     "refs": REFS_CUSTOMER, "required": ["order_no", "customer_code", "order_date", "requested_delivery_date",
                                                         "sku", "quantity"],
                     "defaults": {}, "line_fields": ["sku", "quantity", "unit_price", "discount_pct", "tax_rate", "unit"],
                     "export": "sales_orders"},
    "purchase_orders": {"mode": "propose", "model": ("app.models.procurement", "PurchaseOrder"), "key": "po_no",
                        "perm": ("procurement.create",), "view_perm": ("procurement.view_all",),
                        "fields": {"po_no": "text", "supplier_code": "ref", "order_date": "date", "expected_delivery_date": "date",
                                   "currency": "text", "payment_terms": "text", "notes": "text", "material_code": "text", "sku": "text",
                                   "quantity": "number", "unit_price": "number", "tax_rate": "number", "unit": "text", "status": "text"},
                        "refs": {"supplier_code": ("supplier_id", "suppliers")},
                        "required": ["po_no", "supplier_code", "order_date", "expected_delivery_date", "quantity"],
                        "defaults": {}, "line_fields": ["material_code", "sku", "quantity", "unit_price", "tax_rate", "unit"],
                        "export": "purchase_orders"},
    # read-only: posted finance and stock are never written by a sync
    "invoices": {"mode": "read_only", "model": ("app.models.sales", "Invoice"), "key": "invoice_no", "perm": (),
                 "view_perm": ("finance.view", "sales.view_all"),
                 "fields": {"invoice_no": "text", "order_no": "text", "customer_code": "text", "invoice_date": "date",
                            "due_date": "date", "status": "text", "currency": "text", "subtotal": "number", "tax_amount": "number",
                            "total_amount": "number", "paid_amount": "number"},
                 "required": [], "defaults": {}, "export": "invoices",
                 "why": "Invoices are posted finance documents: change them only through the invoicing, credit-note and reversal flows."},
    "stock": {"mode": "read_only", "model": ("app.models.inventory", "Stock"), "key": "stock_key", "perm": (),
              "view_perm": ("inventory.view", "inventory.view_all"),
              "fields": {"stock_key": "text", "sku": "text", "material_code": "text", "warehouse_code": "text",
                         "quantity_on_hand": "number", "quantity_reserved": "number", "quantity_available": "number",
                         "is_blocked": "bool"},
              "required": [], "defaults": {}, "export": "stock",
              "why": "Stock changes only through goods receipts, issues, transfers and counted adjustments."},
}

# what a target needs to exist first (dependency ordering of a full synchronisation)
DEPENDS: dict[str, list[str]] = {
    "customers": [], "suppliers": [], "products": [], "crm_contacts": [],
    "materials": ["suppliers"],
    "deals": ["customers"], "tickets": ["customers"],
    "custom_objects": [],
    "sales_orders": ["customers", "products"], "purchase_orders": ["suppliers", "materials", "products"],
    "invoices": ["sales_orders", "customers"], "stock": ["products", "materials"],
    "associations": ["customers", "crm_contacts", "deals", "products", "sales_orders", "custom_objects"],
}
EXTRA_CONTROLLED = {"standard_cost", "selling_price", "expected_revenue"}   # prices/costs/revenue: admin-run syncs only


def order(targets: list[str]) -> list[str]:
    """Dependency order of the given targets (dependencies first; a target whose dependency is not in the list is fine)."""
    chosen, out, seen = set(targets), [], set()

    def visit(t: str, stack: tuple = ()):
        if t in seen or t in stack:
            return
        for d in DEPENDS.get(t, []):
            visit(d, stack + (t,))
        seen.add(t)
        if t in chosen:
            out.append(t)

    for t in sorted(chosen):
        visit(t)
    return out
