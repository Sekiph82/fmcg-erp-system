# Customs Documents

**Route:** `/dashboard/logistics?tab=documents`  
**Permission required:** `logistics.view`

## What It Does

Manages the set of trade and customs documents required for each shipment. Tracks document status from Draft to Approved and flags missing required documents.

![Documents Tab](../../../screenshots/captured/module-ui/logistics/documents/documents-tab.png)
*Documents tab — shipment selector and document checklist cards.*

## Document Types

| Type | Label | Required |
|------|-------|---------|
| COMMERCIAL_INVOICE | Commercial Invoice | ✅ |
| PACKING_LIST | Packing List | ✅ |
| BILL_OF_LADING | Bill of Lading | ✅ |
| AIRWAY_BILL | Airway Bill | — |
| CERTIFICATE_OF_ORIGIN | Certificate of Origin | ✅ |
| PHYTOSANITARY | Phytosanitary Certificate | — |
| IMPORT_DECLARATION | Import Declaration (IDF) | ✅ |
| DUTY_RECEIPT | Duty Payment Receipt | — |
| OTHER | Other | — |

Required documents (5): Commercial Invoice, Packing List, Bill of Lading, Certificate of Origin, Import Declaration. Missing required documents are highlighted in an orange alert banner.

## Document Statuses

| Status | Meaning |
|--------|---------|
| DRAFT | Document registered but not submitted |
| SUBMITTED | Submitted to customs / authority |
| APPROVED | Accepted and approved |
| REJECTED | Rejected — resubmission required |

## Document Checklist Cards

Each document type appears as a card. Cards with documents show: doc_no, doc_date, issuer, file reference, status badge. Cards without documents show "Not uploaded" with an Upload link.

## Add / Update Document Form

| Field | Description |
|-------|-------------|
| Document Type | Select from the 9 types |
| Document No | Reference number on the document |
| Date | Document issue date |
| Issuer | Company or authority that issued it |
| File Reference | Path or URL placeholder (e.g. docs/ISH-00001/invoice.pdf) |
| Status | DRAFT · SUBMITTED · APPROVED · REJECTED |
| Description / Notes | Free text |

API: `POST /api/v1/logistics/documents`, `PUT /api/v1/logistics/documents/{id}`

## All Documents Table

Below the checklist cards, a table lists all documents for the selected shipment with columns: Type, Doc No, Date, Issuer, File Ref, Status.
