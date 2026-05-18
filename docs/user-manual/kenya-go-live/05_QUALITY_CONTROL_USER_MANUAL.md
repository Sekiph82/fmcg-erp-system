# Quality Control User Manual

**Audience:** QC Technicians, Lab Analysts, QA Manager  
**URL:** `/dashboard/quality`  
**Permission required:** `quality.view`, `quality.create`

---

## Your Role

You inspect incoming materials, in-process production, and finished goods. You manage HACCP documentation, handle consumer complaints, and maintain allergen records. Food safety compliance depends on your work.

---

## Pages You Use

| Page | URL | What you do there |
|---|---|---|
| Quality workspace | /dashboard/quality | All QC activities |
| Compliance workspace | /dashboard/compliance | GS1 labels, regulatory certs |
| Production (QC tab) | /dashboard/production?tab=quality-control | In-line QC during production |

---

## Screenshot

![Quality Workspace](../screenshots/captured/062_quality.png)

---

## Quality Inspection Workflow

```
Incoming materials:
1. Procurement delivers → QC receives inspection task
2. Inspect against parameters
3. Pass → materials released to warehouse
4. Fail → quarantine + corrective action

In-process (during production):
5. Operator logs in-line checks via Shop Floor terminal
6. QC technician does spot checks at defined intervals
7. Results recorded in Production → Quality Control tab

Finished goods:
8. Sample from each production batch
9. Lab tests against product specification
10. Pass → batch released for despatch
11. Fail → batch quarantined → root cause investigation
```

---

## Record an Inspection

1. Go to `/dashboard/quality?tab=inspections`
2. Click **+ New Inspection**
3. Select:
   - Inspection type: Incoming / In-process / Finished goods
   - Product or material
   - Batch/lot number
   - Linked PO or production order
4. For each parameter, enter the test result
5. System shows Pass/Fail per parameter based on spec limits
6. Overall: **PASS** or **FAIL**
7. If FAIL: mandatory **Corrective Action** field
8. Click **Submit**

![Quality — Inspections Tab](../screenshots/captured/063_quality-inspections.png)

---

## Quality Parameters

Define what gets tested and the acceptable limits:
1. Quality → Parameters tab
2. Click **+ Add Parameter**
3. Fields: parameter name, test method, unit, min, max, target
4. Assign to product or product group
5. Save

Examples:
- pH: 4.5 – 6.5
- Moisture %: < 12%
- Microbial count: < 100 CFU/g
- Temperature at receipt: 0–4°C

![Quality — Parameters Tab](../screenshots/captured/068_quality-parameters.png)

---

## Certificates of Analysis (CoA)

For each released batch:
1. Quality → Certificates tab
2. Click **Generate CoA** for the passed batch
3. System populates all test results from the inspection record
4. Review and sign off (digital signature)
5. Send to customer if requested

![Quality — Certificates Tab](../screenshots/captured/066_quality-certificates.png)

---

## QMS — HACCP and CAPA

1. Go to `/dashboard/quality?tab=qms`
2. HACCP plans: critical control points, monitoring procedures, limits
3. Non-conformance reports (NCR): log any deviation
4. CAPA: Corrective and Preventive Action records
5. Document control: SOPs, work instructions

![Quality — QMS Tab](../screenshots/captured/064_quality-qms.png)

---

## Allergen Matrix

Kenya food producers must declare allergens on labels:
1. Quality → Allergen tab
2. Each product shows allergen presence: Contains / May Contain / Free From
3. Cross-contamination risks from shared equipment are flagged
4. Update whenever a formula changes

![Quality — Allergen Tab](../screenshots/captured/065_quality-allergen.png)

**Critical for regulatory compliance:** Incorrect allergen declaration can trigger recalls and regulatory action.

---

## Consumer Complaints

1. Quality → Consumer Complaints tab
2. Click **+ Log Complaint**
3. Fill in: date, customer, product, batch number, complaint description
4. Assign to QA team member
5. Root cause investigation + CAPA
6. Close complaint when resolved
7. Batch link enables traceability checks

---

## Regulatory Certificates

1. Compliance → Regulatory Certs tab
2. Upload certificates (KEBS, KRA, import permits, halal, kosher)
3. Set expiry date
4. System alerts 60 days before expiry
5. Renew and upload new certificate

---

## GS1 Barcode Labels

1. Compliance → GS1 tab
2. Select product
3. System generates GS1-128 barcode with GTIN, lot, expiry date
4. Print via connected label printer
5. Barcode scannable at retail and for traceability

---

## Common Mistakes

| Mistake | How to Avoid |
|---|---|
| Releasing batch before all tests complete | All mandatory parameters must be entered before status can be set to PASS |
| Wrong batch number on inspection | Copy batch number directly from physical label |
| Not logging consumer complaint | Every complaint must be logged for regulatory audit trail |
| Expired certificate still in system | Set expiry dates on all certificates; review alert dashboard weekly |

---

## Troubleshooting

**Problem:** Cannot find the batch in inspection form  
**Solution:** Batch must be created in production first (Production → Batch & Lots tab)

**Problem:** Inspection shows FAIL but product looks fine  
**Solution:** Check parameter limits — they may need updating. Contact QA manager.

**Problem:** CoA not generating  
**Solution:** All test results must be entered and inspection status must be PASS

---

## Training Checklist

- [ ] Can create and submit an incoming goods inspection
- [ ] Can create in-process and finished goods inspections
- [ ] Can enter test results against parameters
- [ ] Can generate a Certificate of Analysis
- [ ] Can update the allergen matrix for a product
- [ ] Can log a consumer complaint
- [ ] Can generate a GS1 barcode label
- [ ] Can view HACCP CCPs and SOPs in QMS
- [ ] Knows how to raise a CAPA
