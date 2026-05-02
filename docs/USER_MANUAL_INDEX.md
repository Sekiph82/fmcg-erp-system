# FMCG ERP SYSTEM — COMPLETE USER MANUAL

**Version:** 1.0  
**System:** FMCG ERP (Kenya / East Africa)  
**Audience:** All ERP Users — Operators, Managers, Administrators  
**Format:** Enterprise Training Manual — SAP/Oracle Style

---

## TABLE OF CONTENTS

### PHASE 1 — PLANNING & PRODUCTION
1. [MRP & Demand Forecasting](USER_MANUAL_PHASE1_PLANNING.md#mrp)
2. [Master Production Scheduling (MPS)](USER_MANUAL_PHASE1_PLANNING.md#mps)
3. [Advanced Planning Suite](USER_MANUAL_PHASE1_PLANNING.md#planning)
4. [BOM & Formula Management](USER_MANUAL_PHASE1_PLANNING.md#bom)
5. [Production Orders / MES](USER_MANUAL_PHASE1_PLANNING.md#production)
6. [Shop Floor Execution](USER_MANUAL_PHASE1_PLANNING.md#shopfloor)
7. [Material Flow Engine](USER_MANUAL_PHASE1_PLANNING.md#materialflow)
8. [Machine & Operator Intelligence](USER_MANUAL_PHASE1_PLANNING.md#machineops)

### PHASE 2 — INVENTORY, QUALITY & COMPLIANCE
9. [Inventory & FEFO Control](USER_MANUAL_PHASE2_QUALITY.md#inventory)
10. [Lot Traceability & Batch Recall](USER_MANUAL_PHASE2_QUALITY.md#traceability)
11. [Quality Control & QMS / HACCP](USER_MANUAL_PHASE2_QUALITY.md#qms)
12. [GS1 Barcode & Label Printing](USER_MANUAL_PHASE2_QUALITY.md#gs1)
13. [Allergen & Nutrition Management](USER_MANUAL_PHASE2_QUALITY.md#allergen)

### PHASE 3 — PROCUREMENT & FINANCE
14. [Procurement Suggestion Engine](USER_MANUAL_PHASE3_FINANCE.md#procurement-suggestion)
15. [Subcontracting](USER_MANUAL_PHASE3_FINANCE.md#subcontracting)
16. [Landed Cost Allocation](USER_MANUAL_PHASE3_FINANCE.md#landed-cost)
17. [3-Way Invoice Matching](USER_MANUAL_PHASE3_FINANCE.md#invoice-match)
18. [Bank Reconciliation](USER_MANUAL_PHASE3_FINANCE.md#bank-recon)
19. [Fixed Assets & Depreciation](USER_MANUAL_PHASE3_FINANCE.md#fixed-assets)
20. [Accounting Dimensions & Cost Centers](USER_MANUAL_PHASE3_FINANCE.md#dimensions)

### PHASE 4 — SALES & COMMERCIAL
21. [Sales Orders](USER_MANUAL_PHASE4_SALES.md#sales-orders)
22. [Pricing Engine & Promotions](USER_MANUAL_PHASE4_SALES.md#pricing)
23. [CRM Pipeline](USER_MANUAL_PHASE4_SALES.md#crm)
24. [Customer / Distributor Portal](USER_MANUAL_PHASE4_SALES.md#portal)
25. [Supplier Portal](USER_MANUAL_PHASE4_SALES.md#supplier-portal)
26. [Dunning & Collections](USER_MANUAL_PHASE4_SALES.md#dunning)
27. [Subscription / Recurring Orders](USER_MANUAL_PHASE4_SALES.md#subscription)
28. [Van Sales / Mobile POS](USER_MANUAL_PHASE4_SALES.md#van-sales)
29. [Contract Management](USER_MANUAL_PHASE4_SALES.md#contracts)
30. [Sales Commissions](USER_MANUAL_PHASE4_SALES.md#commissions)

### PHASE 5 — HR & PAYROLL
31. [Expense Claims](USER_MANUAL_PHASE5_HR.md#expenses)
32. [Recruitment / ATS](USER_MANUAL_PHASE5_HR.md#recruitment)
33. [Employee Self-Service (ESS)](USER_MANUAL_PHASE5_HR.md#ess)
34. [Performance Appraisals](USER_MANUAL_PHASE5_HR.md#appraisals)
35. [Training & Skills Management](USER_MANUAL_PHASE5_HR.md#training)
36. [Timesheet Management](USER_MANUAL_PHASE5_HR.md#timesheets)
37. [Kenya Payroll](USER_MANUAL_PHASE5_HR.md#payroll)

### PHASE 6 — PLATFORM & INTELLIGENCE
38. [Notification Center](USER_MANUAL_PHASE6_PLATFORM.md#notifications)
39. [Kanban Boards](USER_MANUAL_PHASE6_PLATFORM.md#kanban)
40. [Custom Report Builder](USER_MANUAL_PHASE6_PLATFORM.md#report-builder)
41. [Calendar & Resource Scheduling](USER_MANUAL_PHASE6_PLATFORM.md#calendar)
42. [Activity Timeline / Chatter](USER_MANUAL_PHASE6_PLATFORM.md#chatter)
43. [Custom Fields](USER_MANUAL_PHASE6_PLATFORM.md#custom-fields)
44. [2FA & Security](USER_MANUAL_PHASE6_PLATFORM.md#2fa)
45. [Webhook / Event Engine](USER_MANUAL_PHASE6_PLATFORM.md#webhooks)
46. [AI & Intelligence Layer](USER_MANUAL_PHASE6_PLATFORM.md#ai)

### PHASE 7 — EXTENDED FMCG MODULES
47. [Fleet Management](USER_MANUAL_PHASE7_EXTENDED.md#fleet)
48. [Cycle Counting](USER_MANUAL_PHASE7_EXTENDED.md#cycle-count)
49. [Putaway Rules](USER_MANUAL_PHASE7_EXTENDED.md#putaway)
50. [Secondary Sales / Distributor Sell-Through](USER_MANUAL_PHASE7_EXTENDED.md#secondary-sales)
51. [ESG & Sustainability Reporting](USER_MANUAL_PHASE7_EXTENDED.md#esg)

---

## HOW TO USE THIS MANUAL

### For New Users
Start with **Phase 1** if you work in production/planning.  
Start with **Phase 4** if you work in sales/commercial.  
Start with **Phase 5** if you work in HR/payroll.

### For System Administrators
Read **Phase 6** (Platform) fully before configuring the system.

### For Trainers
Each module ends with a **QUICK TRAINING SUMMARY** — use these for 15-minute onboarding sessions.

### Navigation
- Use Ctrl+F / Cmd+F to search within any document.
- Each section uses consistent headers: Overview → Roles → Concepts → Screens → Workflows → Scenarios → Do's/Don'ts → Errors → Integrations.

---

## SYSTEM OVERVIEW

The FMCG ERP is a full enterprise resource planning system built for Fast-Moving Consumer Goods manufacturers in Kenya and East Africa. It covers the complete business cycle:

```
Raw Materials → Production → Finished Goods → Sales → Collection → Finance
     ↑                                                                  ↓
Procurement ←──────────────── Planning ────────────────────────── Reporting
```

### Core Principles
1. **No action without audit** — every financial and stock movement is logged.
2. **Approval before execution** — critical actions require authorization.
3. **AI assists, humans decide** — AI recommendations require user confirmation.
4. **Data integrity first** — the system enforces business rules automatically.

---

*This manual was generated for the FMCG ERP System v1.0, May 2026.*
