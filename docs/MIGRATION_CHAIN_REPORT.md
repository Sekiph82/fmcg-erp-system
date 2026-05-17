# Migration Chain Report

Generated: 2026-05-17

## Summary

The migration chain is **fundamentally designed for a pre-bootstrapped database**. It cannot run successfully on a fresh database via `alembic upgrade head` alone. This is a known design constraint: Alembic was introduced after the initial schema was already deployed via SQLAlchemy `create_all()`.

## Migration Chain (revision order)

```
3c45d9071c98  ← BASE (down_revision = None)  ← misnamed "initial_schema"
  └─ a1b2c3d4e5f6  finance_accounting_module
       └─ b2c3d4e5f6a7  ai_intelligence_module
            └─ d4e5f6a7b8c9  advanced_production_module
                 ├─ a2b3c4d5e6f7  boiler_steam_extended
                 │    └─ b7c8d9e0f1a2  compressor_air_extended
                 │         └─ c8d9e0f1a2b3  production_costing
                 │              └─ d9e0f1a2b3c4  production_ai
                 │                   └─ e0f1a2b3c4d5  chemical_water_treatment
                 │                        └─ f1a2b3c4d5e6  qms_haccp_system
                 │                             └─ a3b4c5d6e7f8  gs1_label_printing
                 │                                  └─ b4c5d6e7f8a9  allergen_nutrition_system ─┐
                 └─ e5f6a7b8c9d0  utilities_module                                              │
                      └─ f6a7b8c9d0e1  utility_management_module                               │
                           ├─ a0b1c2d3e4f5  extend_utility_assets ───────────────────────────┐ │
                           └─ b1c2d3e4f5a0  extend_utility_devices_readings                  │ │
                                └─ c2d3e4f5a0b1  utility_transactions_backbone               │ │
                                     └─ d4e5f6a7b8cc  soft_water_extended ─────────────────┐ │ │
                                                                                             ↓ ↓ ↓
                                                          87ad3195d2c5  merge_all_heads (3 parents)
                                                               └─ 4cddbd375e74  procurement_suggestion_engine
                                                                    └─ 4a1b1eba5eed  subcontracting_system
                                                                         └─ c5d6e7f8a9b0  landed_cost
                                                                              └─ d6e7f8a9b0c1  invoice_matching
                                                                                   └─ e7f8a9b0c1d2  bank_reconciliation
                                                                                        └─ f9a0b1c2d3e4  crm_pipeline
                                                                                             └─ a9b0c1d2e3f4  portal
                                                                                                  └─ b1c2d3e4f5a6  supplier_portal
                                                                                                       └─ c2d3e4f5a6b7  dunning
                                                                                                            └─ d3e4f5a6b7c8  price_list
                                                                                                                 └─ e4f5a6b7c8d9  recurring_orders
                                                                                                                      └─ f5a6b7c8d9e0  van_sales
                                                                                                                           └─ a6b7c8d9e0f1  contracts
                                                                                                                                └─ b8c9d0e1f2a3  moto_sales
                                                                                                                                     └─ c9d0e1f2a3b4  commissions
                                                                                                                                          └─ d0e1f2a3b4c5  expense_claims
                                                                                                                                               └─ e1f2a3b4c5d6  recruitment_ats
                                                                                                                                                    └─ f2a3b4c5d6e7  employee_self_service
                                                                                                                                                         └─ a3b4c5d6e8f7  performance_appraisals
                                                                                                                                                              └─ b4c5d6e7a8f9  training_skills
                                                                                                                                                                   └─ c5d6e7f8b0a9  timesheet_approval
                                                                                                                                                                        └─ d6e7f8a9c0b1  notification_center
                                                                                                                                                                             └─ e7f8a9b0d1c2  kanban_boards
                                                                                                                                                                                  └─ f8a9b0c1d2e3  custom_report_builder
                                                                                                                                                                                       └─ a9b0c1d2f3e4  calendar_scheduling
                                                                                                                                                                                            └─ b0c1d2e3f4a5  chatter_timeline
                                                                                                                                                                                                 └─ c1d2e3f4a5b6  custom_fields
                                                                                                                                                                                                      └─ d2e3f4a5b6c7  two_factor_auth
                                                                                                                                                                                                           └─ e3f4a5b6c7d8  webhook_engine
                                                                                                                                                                                                                └─ f4a5b6c7d8e9  fleet_management
                                                                                                                                                                                                                     └─ a5b6c7d8e9f0  cycle_count
                                                                                                                                                                                                                          └─ b6c7d8e9f0a1  putaway_rules
                                                                                                                                                                                                                               └─ c7d8e9f0a1b2  secondary_sales
                                                                                                                                                                                                                                    └─ d8e9f0a1b2c3  esg_sustainability
                                                                                                                                                                                                                                         └─ e9f0a1b2c3d4  payroll_ke
                                                                                                                                                                                                                                              └─ f0a1b2c3d4e5  esg_intelligence_gap69
                                                                                                                                                                                                                                                   └─ f1a2b3c4e5d6  plugin_marketplace_gap70
                                                                                                                                                                                                                                                        └─ 1a2b3c4d5e6f  audit_logs_schema_repair
                                                                                                                                                                                                                                                             └─ 20260510_0700  user_must_change_password
                                                                                                                                                                                                                                                                  └─ 20260510_0710  fix_fixed_assets_schedule_enum
                                                                                                                                                                                                                                                                       └─ 20260511_0010  enterprise_accounting_core
                                                                                                                                                                                                                                                                            └─ 20260511_0020  operational_posting_integration
                                                                                                                                                                                                                                                                                 └─ 20260511_0030  access_scopes
                                                                                                                                                                                                                                                                                      └─ 20260511_0040  finance_journal_scopes
                                                                                                                                                                                                                                                                                           └─ 20260514_0010  aps_planning_tables
                                                                                                                                                                                                                                                                                                └─ 20260514_0020  wms_depth_reconciliation
                                                                                                                                                                                                                                                                                                     └─ 20260514_0030  procurement_scope_governance
                                                                                                                                                                                                                                                                                                          └─ 20260515_0010  crm_sales_scope_reconciliation
                                                                                                                                                                                                                                                                                                               └─ 20260515_0020  hrms_payroll_reconciliation
                                                                                                                                                                                                                                                                                                                    └─ 20260515_0030  document_knowledge_reconciliation
                                                                                                                                                                                                                                                                                                                         ├─ 20260515_0040  report_builder_schedule_run_log ─┐
                                                                                                                                                                                                                                                                                                                         └─ 20260515_0050  haccp_pdca_audit_scheduling       │
                                                                                                                                                                                                                                                                                                                                └─ 20260515_0060  gs1_product_config_fields ─────┘
                                                                                                                                                                                                                                                                                                                         20260516_0010  npd_formula_governance (2 parents above)
                                                                                                                                                                                                                                                                                                                              └─ 20260516_0020  iot_machine_streaming
                                                                                                                                                                                                                                                                                                                                   └─ 20260516_0030  maintenance_predictive
                                                                                                                                                                                                                                                                                                                                        └─ 20260516_0040  ai_prompt_registry
                                                                                                                                                                                                                                                                                                                                             └─ 20260516_0050  multi_company_warehouse
                                                                                                                                                                                                                                                                                                                                                  └─ 20260516_0060  performance_indexes  ← HEAD
```

**Total migrations: 76**  
**Merge points: 2** (`87ad3195d2c5`, `20260516_0010`)  
**Heads: 1** (`20260516_0060`)

## Key Findings

### 1. Base Migration Is Misnamed and Incomplete

`3c45d9071c98_initial_schema.py` has `down_revision = None` (it IS the base) but only adds 3 columns to `sales_orders`. It does NOT create base tables.

**Why this exists**: Alembic was introduced after the original schema was deployed via `create_all()`. This migration was the first incremental change tracked in Alembic.

### 2. All Migrations Assume Pre-Existing Base Tables

Migration `a1b2c3d4e5f6_finance_accounting_module.py` (the second migration) creates `purchase_invoices` with:
```sql
FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
FOREIGN KEY (po_id)        REFERENCES purchase_orders(id)
FOREIGN KEY (created_by_id) REFERENCES users(id)
```

None of these tables (`suppliers`, `purchase_orders`, `users`, `materials`, `products`) are created by any migration. They exist only because the project was bootstrapped via `Base.metadata.create_all()`.

### 3. `alembic upgrade head` Fails on Fresh Databases

Root cause: `3c45d9071c98` tries to ALTER `sales_orders`. If the table doesn't exist:
- **Original migration**: `op.add_column('sales_orders', ...)` → PostgreSQL error: `table "sales_orders" does not exist`
- **Gordon's patched migration**: column guards skip → migration succeeds
- **But**: `a1b2c3d4e5f6` runs next and fails immediately with FK reference errors

Gordon's patch to `3c45d9071c98` helps migration 1 but migration 2 still fails.

### 4. Tables Never Created by Migrations

These core tables are in SQLAlchemy models but never in any migration's `create_table()`:
- `users`, `roles`, `permissions`, `user_role`, `role_permission`
- `products`, `materials`, `customers`, `suppliers`
- `purchase_orders`, `sales_orders`, `inventory_items`
- ...and many more (the entire initial schema)

They exist only in `Base.metadata` (via `app.models`) and must be bootstrapped via `create_all()`.

### 5. Dev Reset Path

For a fresh dev database, the correct sequence (now implemented in `dev_migrate.py`) is:
1. `Base.metadata.create_all()` — creates all tables from current SQLAlchemy models
2. `alembic stamp head` — tells Alembic that all migrations are already applied
3. Future incremental migrations run normally via `alembic upgrade head`

## Production Note

In production, the schema must already exist (from a previous deployment or manual setup). Running `alembic upgrade head` applies only incremental changes. **Do not run `create_all()` in production** — it cannot replace migrations and would create schema drift.

If production is being set up for the first time, the database administrator must:
1. Create the database
2. Create base tables via a controlled process (e.g., running `dev_migrate.py` in a staging environment, exporting the schema, and applying it to production)
3. `alembic stamp head`
4. Then `alembic upgrade head` applies future changes normally

## Gordon's Changes Assessment

| File | Gordon's Change | Assessment | Action |
|------|----------------|------------|--------|
| `3c45d9071c98_initial_schema.py` | Added `_has_table()` + `_has_column()` guards | Correct — prevents migration 1 from failing. Bare `except:` was unsafe. | Kept, fixed bare `except:` → `except Exception:` |
| `dev_migrate.py` | Replaced Alembic with pure `create_all()` | Partially correct (create_all needed) but wrong: (a) missing `import app.models` so 0 tables created, (b) no Alembic stamp so future migrations broken | Reverted and rewrote properly |
| `docker-compose.yml` | Added `env_file:` to db, changed healthcheck defaults, increased start_period + resources | Mostly correct. Wrong defaults: `:-postgres` should be `:-erp_user`/`:-fmcg_erp` | Kept, fixed defaults |
