# Full ERP Reference Manual — Index

**Date:** 2026-05-18  
**Version:** 1.0  
**System:** FMCG ERP — Kenya

This is the complete reference manual covering every workspace and module in the ERP. Unlike the Kenya go-live role manuals, this manual covers all pages regardless of role.

---

## How to Use This Manual

- **Staff training**: use the Kenya go-live role manuals in `../kenya-go-live/` instead
- **Admin reference**: use this manual when setting up or investigating any module
- **Developer reference**: see API docs at `/docs` and backend source

---

## Chapter Index

| Chapter | Topic | Workspaces Covered |
|---|---|---|
| [01](01_DASHBOARD_AND_NAVIGATION.md) | Dashboard & Navigation | /dashboard, sidebar, search |
| [02](02_MASTER_DATA.md) | Master Data | products, materials, suppliers, recipes, BOM |
| [03](03_PROCUREMENT.md) | Procurement | procurement, suppliers |
| [04](04_INVENTORY_AND_WAREHOUSE.md) | Inventory & Warehouse | inventory, warehouses, wms |
| [05](05_PRODUCTION.md) | Production | production, shop-floor, planning |
| [06](06_QUALITY_AND_COMPLIANCE.md) | Quality & Compliance | quality, compliance |
| [07](07_SALES_AND_DISTRIBUTION.md) | Sales & Distribution | sales, logistics, crm, marketing, pos |
| [08](08_FINANCE.md) | Finance | finance, payroll |
| [09](09_HR_AND_PAYROLL.md) | HR & Payroll | hr, payroll |
| [10](10_ADMIN_AND_SECURITY.md) | Admin & Security | admin, integrations, logs, approvals |
| [11](11_AI_AND_AUTOMATION.md) | AI & Automation | ai, analytics |
| [12](12_REPORTS_AND_EXPORTS.md) | Reports & Exports | analytics, all workspace export functions |
| [13](13_STANDALONE_OPERATIONAL_PAGES.md) | Standalone Pages | npd, maintenance, utility-management, helpdesk, documents, communication |
| [14](14_OLD_ROUTE_COMPATIBILITY.md) | Old Route Compatibility | All /dashboard/* redirects |

---

## Workspace Quick Reference

| Workspace | URL | Role | Key Tabs |
|---|---|---|---|
| Dashboard | /dashboard | All | — |
| Products | /dashboard/products | Admin/Prod | products |
| Materials | /dashboard/materials | Warehouse | materials |
| Suppliers | /dashboard/suppliers | Procurement | suppliers |
| Inventory | /dashboard/inventory | Warehouse | stock, movements, shelf-life, cycle-count, traceability, serials, valuation |
| Warehouses | /dashboard/warehouses | Warehouse | warehouses, wms |
| WMS | /dashboard/wms | Warehouse | zones, locations, quarantine |
| Procurement | /dashboard/procurement | Procurement | purchase-requests, orders, rfq, deliveries, suppliers, suggestions, subcontracting, landed-cost |
| Production | /dashboard/production | Production | plans, orders, scheduling, execution, material-flow, batch-lots, quality-control, oee, downtime, waste-yield, costing |
| Shop Floor | /dashboard/shop-floor | Production | terminal, supervisor, queue, downtime, handover |
| BOM | /dashboard/bom | Production | list, substitutes, compare, conversion |
| Recipes | /dashboard/recipes | Production | recipes |
| Planning | /dashboard/planning | Production | mrp, mps, capacity, advanced, kanban |
| NPD | /dashboard/npd | Production | npd |
| Quality | /dashboard/quality | Quality | inspections, certificates, parameters, consumer-complaints, qms, allergen, brand-assets |
| Compliance | /dashboard/compliance | Quality | gs1, regulatory-certs |
| Sales | /dashboard/sales | Sales | orders, invoices, customers, quotes, shipments, van-sales, collections, returns, price-lists, field-sales |
| Logistics | /dashboard/logistics | Sales | shipments, containers, arrivals, fleet |
| CRM | /dashboard/crm | Sales | pipeline, leads, opportunities, loyalty, nps, surveys |
| Marketing | /dashboard/marketing | Sales | campaigns, promotions, tpm, market-intel |
| POS | /dashboard/pos | Sales | pos, sales, sessions |
| Finance | /dashboard/finance | Finance | accounting, bank-recon, fixed-assets, receivables, cashbook, budget, mpesa, tax, expenses |
| HR | /dashboard/hr | HR | employees, attendance, payroll, leave, recruitment, appraisals, training, expenses |
| Payroll | /dashboard/payroll | HR | overview, profiles, reports |
| Admin | /dashboard/admin | Admin | users, roles, permissions, companies, security, approvals, system-config, logs |
| Integrations | /dashboard/integrations | Admin | mpesa, sync, webhooks, developer |
| Analytics | /dashboard/analytics | Manager | overview, sales, production, inventory, finance, report-builder |
| AI | /dashboard/ai | All | chat, predictions, formulations |
| Documents | /dashboard/documents | All | documents, compliance, knowledge-base, esign |
| Communication | /dashboard/communication | All | messages, chatter, calendar, notifications |
| Helpdesk | /dashboard/helpdesk | All | all, open, escalated, sla |
| Maintenance | /dashboard/maintenance | Production | assets, breakdowns, plans, predictive |
| Utilities | /dashboard/utility-management | Production | electricity, water, steam, solar, esg |
| Logs | /dashboard/logs | Admin | operational, mpesa, security |
| Approvals | /dashboard/approvals | Manager | all, rules |
