# Compliance & Labelling

**Route:** `/dashboard/compliance`  
**Permission required:** `gs1.view`  
**Workspace tabs:** GS1 & Labels, Regulatory Certs

---

## What It Does

The Compliance module manages product labelling and regulatory certification requirements. It covers GS1 barcode generation and label printing, and provides a consolidated view of all regulatory certificates linked to products and suppliers.

![Compliance workspace](../../../screenshots/captured/069_compliance.png)
*Compliance workspace showing GS1 & Labels and Regulatory Certs tabs.*

![Compliance — GS1 Labels tab](../../../screenshots/captured/070_compliance-gs1.png)
*GS1 Labels tab for generating and printing GS1-128 barcodes and label artwork.*

---

## GS1 & Labels Tab

**Tab key:** `gs1`  
**Route:** `/dashboard/gs1/page` (embedded)

### GS1 Overview

GS1 is the global standard for product identification codes. The ERP uses GS1 identifiers for:
- **GTIN** (Global Trade Item Number) — 14-digit product barcode
- **SSCC** (Serial Shipping Container Code) — pallet and logistics unit identification
- **GLN** (Global Location Number) — identifies company locations (factory, warehouse)
- **GS1-128** — variable-length barcode for batch/lot and expiry date encoding on labels

GS1 barcodes are mandatory for products distributed through modern trade (supermarkets, export) that use barcode scanning at point of sale and goods receipt.

### Label Types

| Label Type | Usage |
|------------|-------|
| Product Label | Consumer-facing label on individual units |
| Case Label | Outer carton label (case GTIN + batch + expiry) |
| Pallet Label | SSCC pallet label for logistics |
| Shelf Label | Price and PLU label for trade |
| QC Sample Label | Laboratory sample identification |

### GS1 Label Fields

Each label record includes:
- `product_id` — linked product
- `gtin` — 14-digit GS1 product code
- `batch_no` — production batch number
- `expiry_date` — product expiry date
- `net_weight` — declared net weight (g or mL)
- `country_of_origin` — ISO country code
- `label_version` — label design version number

### Label Printing Flow

1. Navigate to **GS1 & Labels** tab
2. Select product(s) and batch(es)
3. Choose label type and quantity
4. Click **Print** — sends to configured label printer (ZPL-compatible or PDF)

Labels can also be exported as PDFs for proofing before print.

### Allergen Declarations on Labels

Allergen information from the **Allergen** tab (Quality module) is pulled automatically into product labels. The ERP enforces that labels cannot be approved for printing until the allergen declaration has been reviewed for the current BOM version.

---

## Regulatory Certs Tab

**Tab key:** `regulatory-certs`  
**Route:** `/dashboard/quality/certificates/page` (embedded)

The Regulatory Certs tab is the same content as **Quality → Certificates**. It is surfaced here in the Compliance workspace for users whose primary focus is regulatory compliance rather than QC operations.

### Certificate Types

| Certificate Type | Description |
|-----------------|-------------|
| KEBS | Kenya Bureau of Standards product certification |
| KEPHIS | Kenya Plant Health Inspectorate Service (for plant-derived products) |
| KRA AEO | Kenya Revenue Authority Authorised Economic Operator |
| HALAL | Halal certification from an accredited body |
| KOSHER | Kosher certification |
| Organic | Organic certification from an accredited certifier |
| ISO 22000 | Food safety management system certification |
| FSSC 22000 | Food Safety System Certification 22000 |
| GMP | Good Manufacturing Practice certificate |
| Export Certificate | Certificate of conformity for export markets |

### Certificate Record Fields

| Field | Description |
|-------|-------------|
| `cert_type` | Type of certificate (from list above) |
| `cert_number` | Certificate reference number |
| `issuing_body` | Organisation that issued the certificate |
| `issued_date` | Date of issue |
| `expiry_date` | Certificate expiry date |
| `product_id` | Product(s) covered (or supplier-level) |
| `supplier_id` | Supplier (for incoming material certs) |
| `status` | ACTIVE / EXPIRED / SUSPENDED / PENDING |
| `document` | Attached PDF of the certificate |

### Certificate Expiry Alerts

The system flags certificates expiring within 60 days (configurable). Expired certificates are shown with an EXPIRED badge in red. Quality managers receive dashboard alerts for approaching expiries so renewal can be initiated in time.

### Certificate Linking

Certificates can be linked to:
- **Products** — for product-level certifications (e.g. KEBS mark)
- **Suppliers** — for supplier audit certificates (e.g. GMP, ISO 22000)
- **Materials** — for material-level compliance (e.g. Halal certificate for an ingredient)
- **QC Inspections** — attaching supplier COA (Certificate of Analysis) to an incoming inspection

---

## Compliance Workflow

### Label Approval Flow

```
1. R&D finalises BOM + Recipe (APPROVED status)
2. QA reviews allergen declaration
3. Regulatory submits KEBS / product registration if required
4. Marketing approves label artwork
5. Compliance officer approves label for print
6. Label is printed and barcode is verified at the scanner
```

### Certificate Renewal Flow

```
1. Alert generated (60 days before expiry)
2. Quality manager assigns renewal task
3. Renewal submitted to issuing body
4. New certificate received → uploaded to ERP
5. Old certificate archived
6. `expiry_date` updated on the new record
```
