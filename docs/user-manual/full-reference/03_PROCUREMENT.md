# Procurement

**URL:** `/dashboard/procurement`  
**Module:** Procurement  
**Permission:** `procurement.view`

---

## Screenshot

> Screenshot pending: Procurement workspace overview

---

## Tabs

| Tab | URL | Purpose |
|---|---|---|
| Purchase Requests | ?tab=purchase-requests | Internal purchase requisitions |
| Orders | ?tab=orders | Purchase order management |
| RFQ | ?tab=rfq | Request for Quotation |
| Deliveries | ?tab=deliveries | Goods receipt notes |
| Suppliers | ?tab=suppliers | Supplier performance |
| Blanket Agreements | ?tab=blanket-agreements | Standing order contracts |
| Reorder Policies | ?tab=reorder-policies | Auto-reorder rules |
| AI Suggestions | ?tab=suggestions | AI-driven procurement suggestions |
| Subcontracting | ?tab=subcontracting | Outsourced production orders |
| Landed Cost | ?tab=landed-cost | Import cost allocation |
| Supplier Portal | ?tab=supplier-portal | Portal for supplier self-service |

---

## PO Status Flow

```
Draft → Submitted → Approved → Sent to Supplier → Partially Received → Fully Received → Invoiced → Paid
```

---

## Approval Thresholds

Configure in Admin → Approvals:
- POs below threshold: auto-approved
- POs above threshold: require manager approval

---

## Blanket Agreements

Standing arrangements with preferred suppliers for regular materials:
1. Set agreed price and quantity for a period
2. System creates POs against the agreement without re-quoting
3. Agreement expires when quantity or date limit reached

---

## Landed Cost Allocation

For imported materials:
- Freight, insurance, customs duty, port charges
- Allocate by: line value, weight, or quantity
- System adds landed cost to inventory unit cost

---

## Related Workspaces

- Suppliers (`/dashboard/suppliers`) — supplier master
- Inventory (`/dashboard/inventory`) — stock after receipt
- Finance (`/dashboard/finance`) — payables, invoice matching
