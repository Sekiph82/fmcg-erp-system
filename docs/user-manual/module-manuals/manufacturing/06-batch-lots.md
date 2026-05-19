# Batch & Lots

**Route:** `/dashboard/production?tab=batch-lots`  
**Tab key:** `batch-lots`  
**Permission required:** `production.view`

---

![Production — Batch / Lots tab](../../../screenshots/captured/module-ui/manufacturing/production/batch-lots-tab.png)
*Batch / Lots tab showing batch and lot numbers assigned during production runs.*

## What It Does

The Batch & Lots tab tracks the batch numbers and lot numbers assigned during production. Batch/lot traceability is required for:
- Food safety recalls (trace finished goods back to raw material lots)
- Shelf-life management (FIFO/FEFO rotation)
- Quality holds (quarantine a specific batch without affecting stock of other batches)
- Customer complaints (identify which production run a product came from)

---

## Key Concepts

### Batch vs. Lot

| Term | Meaning in this ERP |
|------|---------------------|
| **Batch** | A single production run — all output from one work order or a portion of it |
| **Lot** | A traceability unit used for materials received from suppliers |

These terms are sometimes used interchangeably in the UI. In reports, `batch_no` refers to production output; `lot_number` refers to incoming material.

### Batch Number Format

Batch numbers are either:
- System-generated (auto-assigned when a work order is released)
- User-assigned (manually entered during work order creation)

Typical format: `BTH-{YYYYMMDD}-{sequence}` (e.g. `BTH-20260519-001`).

### Lot Number Format

Lot numbers come from the supplier delivery. They are recorded during Goods Receipt in the Procurement/Inventory module and carried through to production when materials are issued.

---

## Batch Record Fields

A batch record captures:

| Field | Description |
|-------|-------------|
| Batch No | Unique identifier for this production batch |
| Work Order | The work order that produced this batch |
| Product | Finished good produced |
| Quantity Produced | Actual good quantity |
| Quantity Scrapped | Quantity rejected / written off |
| Yield % | `quantity_produced / (quantity_produced + quantity_scrapped) × 100` |
| Production Date | Date the batch was manufactured |
| Expiry Date | Calculated from production date + product shelf life |
| Status | PENDING / RELEASED / QUARANTINED / REJECTED / CONSUMED |
| QC Result | Link to the QC inspection for this batch |
| Warehouse Location | Where the finished batch was stored |

---

## Traceability

### Forward Trace (Batch → Customer)

Starting from a batch number, trace:
1. Which work order produced it
2. Which materials (with lot numbers) were consumed
3. Which delivery notes / invoices it appeared on
4. Which customers received it

### Backward Trace (Material Lot → Batch)

Starting from a supplier lot number, trace:
1. Which purchase orders received this lot
2. Which production work orders consumed it
3. Which product batches it contributed to
4. Which customers may have received those batches

---

## QC Integration

When a production batch is created, it appears in the **QC Inspections** queue for a **Finished Goods** inspection. The QC result (PASSED / FAILED / CONDITIONAL_RELEASE) is linked back to the batch record and determines whether the batch can be released to the warehouse.

- `PASSED` → batch status moves to RELEASED, stock credited to finished goods
- `FAILED` → batch status moves to QUARANTINED or REJECTED
- `CONDITIONAL_RELEASE` → batch released with restrictions; notes recorded

---

## Shelf Life & Expiry

Each product has a configured shelf life (in days). When a batch is created:
- `expiry_date = production_date + shelf_life_days`

Batches approaching expiry are flagged in inventory reports. FEFO (First Expiry First Out) picking enforces expiry order during sales order fulfilment.

---

## Batch Quarantine

A batch can be quarantined at any point by a Quality officer. While quarantined:
- The batch cannot be picked for sales orders
- The stock is moved to a quarantine location in the WMS
- All movements require QC manager authorisation

To release from quarantine: navigate to the QC inspection for this batch, record the decision, and change batch status to RELEASED.
