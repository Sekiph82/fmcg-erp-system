# Quality and Compliance

**URLs:** `/dashboard/quality`, `/dashboard/compliance`  
**Module:** Quality  
**Permission:** `quality.view`

---

## Screenshot

![Quality Workspace](../screenshots/captured/062_quality.png)

---

## Quality Workspace Tabs

| Tab | URL | Purpose |
|---|---|---|
| Inspections | ?tab=inspections | All QC inspections |
| Certificates | ?tab=certificates | Certificates of Analysis (CoA) |
| Parameters | ?tab=parameters | Test parameters and spec limits |
| Consumer Complaints | ?tab=consumer-complaints | Complaint register |
| Reports | ?tab=reports | QC summary reports |
| QMS | ?tab=qms | HACCP, CAPA, NCR, SOPs |
| Allergen | ?tab=allergen | Allergen matrix |
| Brand Assets | ?tab=brand-assets | Approved artwork and labels |

---

## Compliance Workspace Tabs

| Tab | URL | Purpose |
|---|---|---|
| GS1 | ?tab=gs1 | GS1 barcode generation |
| Regulatory Certs | ?tab=regulatory-certs | KEBS, import, halal certs |

---

## Inspection Types

| Type | When | Who |
|---|---|---|
| Incoming | On receipt of raw materials | QC technician |
| In-process | During production at CCPs | Operator + QC |
| Finished goods | After production, before dispatch | QC technician + lab |

---

## QMS Modules

**HACCP:** Hazard Analysis and Critical Control Points  
**CAPA:** Corrective and Preventive Action  
**NCR:** Non-Conformance Report  
**SOP:** Standard Operating Procedure (document library)

---

## Allergen Declarations

Kenya food regulations require accurate allergen labelling. The allergen matrix cross-references all products against the 14 major allergens (EU standards). The system flags cross-contamination risks.

---

## GS1 Barcode Generation

The system generates:
- GS1-128 barcodes: GTIN + batch + expiry
- QR codes for product traceability
- Labels printed via connected thermal printer (Zebra, Honeywell)

---

## Related Workspaces

- Production (Quality Control tab) — in-process checks
- Inventory (Traceability tab) — batch trace
- Compliance — GS1 and regulatory
