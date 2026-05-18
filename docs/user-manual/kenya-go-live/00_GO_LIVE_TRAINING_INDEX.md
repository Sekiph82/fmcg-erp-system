# Kenya Go-Live Training Index

**Date:** 2026-05-18  
**Version:** 1.0  
**Project:** FMCG ERP — Kenya Production Launch

---

## How to Use This Manual Set

Each manual covers one role group. Staff should only need their own manual. The Admin manual covers system setup and applies to IT staff only.

All manuals reference screenshots from `../screenshots/captured/`. Screenshots are captured from the live ERP.

---

## Role Manuals

| # | Manual | Role Group | Status |
|---|---|---|---|
| 01 | [Admin User Manual](01_ADMIN_USER_MANUAL.md) | IT Admin, System Administrator | Ready |
| 02 | [Production User Manual](02_PRODUCTION_USER_MANUAL.md) | Production Supervisors, Operators | Ready |
| 03 | [Warehouse & Inventory Manual](03_WAREHOUSE_INVENTORY_USER_MANUAL.md) | Storekeepers, Receiving Clerks | Ready |
| 04 | [Procurement Manual](04_PROCUREMENT_USER_MANUAL.md) | Purchasing Officers | Ready |
| 05 | [Quality Control Manual](05_QUALITY_CONTROL_USER_MANUAL.md) | QC Technicians, QA Manager | Ready |
| 06 | [Sales & Logistics Manual](06_SALES_LOGISTICS_USER_MANUAL.md) | Sales Reps, Invoicing, Logistics | Ready |
| 07 | [HR Manual](07_HR_USER_MANUAL.md) | HR Officer, Payroll Clerk | Ready |
| 08 | [Manager Dashboard Manual](08_MANAGER_DASHBOARD_USER_MANUAL.md) | Department Heads, MD, Finance Director | Ready |
| 09 | [Common Problems & FAQ](09_COMMON_PROBLEMS_AND_FAQ.md) | All Staff | Ready |

---

## Go-Live Readiness Checklist

### Admin Tasks (Complete Before Go-Live)

- [ ] Company name, logo, timezone (Africa/Nairobi), currency (KES) configured
- [ ] All staff user accounts created
- [ ] Roles assigned (Production, Warehouse, Procurement, QC, Sales, HR, Finance)
- [ ] 2FA enabled for all admin accounts
- [ ] M-Pesa integration credentials configured
- [ ] SMTP configured for email notifications

### Master Data Setup (Complete Before Go-Live)

- [ ] All active products loaded in Products workspace
- [ ] All raw materials loaded in Materials workspace
- [ ] All suppliers loaded in Suppliers workspace
- [ ] Warehouses and bin locations configured in WMS
- [ ] BOM/recipes for all active products
- [ ] Chart of accounts set up in Finance
- [ ] All employees created with payroll profiles
- [ ] Customer master data loaded

### Opening Balances (Complete Before Go-Live)

- [ ] Opening stock counted and entered
- [ ] Opening bank balances entered in Finance
- [ ] Opening accounts receivable entered

---

## Training Schedule (Recommended)

| Day | Session | Audience | Duration |
|---|---|---|---|
| -14 | System setup and admin config | IT Admin | Full day |
| -7 | Production and BOM training | Production supervisors | Half day |
| -7 | Warehouse and WMS training | Storekeepers | Half day |
| -5 | Procurement and supplier training | Purchasing team | Half day |
| -5 | Quality inspection setup | QC team | Half day |
| -3 | HR and payroll setup | HR officer | Half day |
| -3 | Sales order and invoicing | Sales team | Half day |
| -1 | Dress rehearsal — full transaction run | All key users | Full day |
| Go-live | Live support at each workstation | IT + key users | Full day |
| +3 | Debrief, FAQ, corrections | All | 2 hours |

---

## Support During Go-Live

- First contact: System Administrator
- ERP vendor support: [add contact]
- Backup procedure: [add manual fallback process]

---

## ERP Login

URL: `http://[server-ip]:3000` (replace with actual server IP or domain)

Default admin: `admin` / [password set by administrator]  
Each staff member will have their own username provided by the admin.

**Never share passwords. Never log in as another user.**
