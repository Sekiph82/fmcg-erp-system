# PLANS.md

## Project Goal

Build a full-scale FMCG factory ERP/MES system that supports:

- Production operations (factory-level control)
- Inventory and warehousing
- Procurement and suppliers
- Sales and customer operations
- Finance and costing
- Quality control
- Utilities and infrastructure systems
- Machine-level traceability
- KPI dashboards and reporting
- Future AI-assisted optimization

This system should evolve into a real enterprise-grade manufacturing platform.

---

## Global Development Strategy

Development must follow:

1. Build strong foundations first
2. Implement modules incrementally
3. Maintain strict modularity
4. Avoid jumping to dashboards before data layers exist
5. Always prefer data integrity over UI completeness
6. Ensure each phase is usable and testable
7. Integrate modules progressively (not at the end)

---

## Phase Structure (High-Level)

### Phase Group 1 — Core Foundations
- data models
- CRUD systems
- relationships
- validation
- import/export

### Phase Group 2 — Operational Modules
- Production
- Utilities
- Inventory
- Procurement

### Phase Group 3 — Costing & Finance
- tariffs
- cost allocation
- product costing
- financial tracking

### Phase Group 4 — Intelligence Layer
- KPIs
- dashboards
- anomaly detection
- reporting

### Phase Group 5 — Integration & Hardening
- cross-module integration
- QA
- optimization
- scalability

---

# 🏭 UTILITIES MODULE PLAN (PRIMARY FOCUS)

## Phase U1 — Module Foundation
- menu and routes
- base pages
- navigation integration

## Phase U2 — Core Data Models
- UtilityAssetCategory
- UtilityAsset
- UtilityDevice (meters/sensors)

## Phase U3 — Master Data CRUD
- asset categories CRUD
- assets CRUD
- devices CRUD
- filters and validation

## Phase U4 — Readings Infrastructure
- meter readings
- validation
- anomaly flags
- CSV import

## Phase U5 — Utility Transaction Layer
- unified transaction schema
- reusable consumption tracking

## Phase U6 — Water Management
- water consumption
- water KPIs

## Phase U7 — Soft Water System
- regeneration cycles
- salt usage
- hardness tracking

## Phase U8 — Electricity Management
- consumption tracking
- department/line breakdown

## Phase U9 — Boiler & Steam
- steam generation
- gas usage
- efficiency tracking

## Phase U10 — Compressed Air
- compressor tracking
- idle time
- leak estimation

## Phase U11 — Solar Energy
- generation tracking
- expected vs actual

## Phase U12 — Chemical Treatment
- dosing
- supplier + cost tracking

## Phase U13 — Wastewater / Biological Treatment
- pH, COD, BOD tracking
- compliance

## Phase U14 — Machine Utility Mapping
- machine-level consumption

## Phase U15 — Tariffs & Bills
- utility pricing
- billing structure

## Phase U16 — Cost Allocation
- distribute utility cost:
  - per machine
  - per line
  - per batch
  - per product

## Phase U17 — KPI Engine
- calculation layer
- reusable formulas

## Phase U18 — Dashboards
- main utilities dashboard
- sub dashboards

## Phase U19 — Alarms & Anomalies
- rule-based alerts
- anomaly detection

## Phase U20 — Reports
- filtered reports
- export support

## Phase U21 — Integration
- Production linkage
- Inventory linkage
- Finance linkage

## Phase U22 — Seed Data
- realistic factory data

## Phase U23 — QA & Hardening
- fix inconsistencies
- optimize queries
- ensure stability

---

# 🏭 PRODUCTION MODULE PLAN

## Phase P1 — Foundation
- production module structure

## Phase P2 — Production Orders
- basic order lifecycle

## Phase P3 — Work Orders
- operational tasks

## Phase P4 — Work Centers
- machines and lines

## Phase P5 — Routing
- step-by-step production

## Phase P6 — Time Tracking
- planned vs actual

## Phase P7 — Downtime
- downtime logging

## Phase P8 — Batch Tracking
- traceability

## Phase P9 — Quality Control
- inline + final QC

## Phase P10 — Waste & Yield
- loss tracking

## Phase P11 — Integration with Utilities
- utility consumption per batch

---

# 📦 INVENTORY MODULE PLAN

## Phase I1 — Warehouses
## Phase I2 — Products
## Phase I3 — Raw Materials
## Phase I4 — Stock Tracking
## Phase I5 — Movements
## Phase I6 — Production Integration
## Phase I7 — Utility Chemical Integration

---

# 💰 FINANCE / COSTING PLAN

## Phase F1 — Basic Invoices
## Phase F2 — Payments
## Phase F3 — Tariffs
## Phase F4 — Cost Allocation Engine
## Phase F5 — Product Costing
## Phase F6 — Profitability Analysis

---

# 🧠 AI / INTELLIGENCE PLAN

(To be implemented AFTER strong data foundation)

## Phase AI1 — Data Readiness
## Phase AI2 — Anomaly Detection
## Phase AI3 — Cost Optimization Suggestions
## Phase AI4 — Predictive Maintenance
## Phase AI5 — Demand Forecasting
## Phase AI6 — Recipe Optimization

---

# 🚀 Execution Rules for Claude

When continuing work:

1. Inspect repository state
2. Identify completed phases
3. Identify partially completed phases
4. Select next logical phase
5. Implement ONLY that phase
6. Keep changes small and coherent

If unsure:
- prioritize earlier unfinished phases
- prioritize data layer over UI
- prioritize correctness over completeness

---

# ❗ Critical Rules

- Do NOT jump to dashboards before data exists
- Do NOT build reports without real data
- Do NOT create fake AI features
- Do NOT rewrite working modules
- Do NOT skip cost allocation layer
- Do NOT break integration points

---

# 🎯 Success Definition

The system is successful when:

- each module works independently
- modules integrate cleanly
- data flows correctly between modules
- costs can be calculated per product
- factory operations can be tracked end-to-end
- dashboards reflect real operational data
