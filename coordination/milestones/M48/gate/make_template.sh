#!/usr/bin/env bash
# M48 gate: build the head template DB (empty -> alembic head) plus the minimal synthetic POVU rows several DB tests
# expect (a product, two customers, two CRM stages) — same as the M47 runner. Disposable container only.
set -eu
TMPL=${1:-m48_tmpl}
cd "$(dirname "$0")/../../../../backend"
docker exec ${GATE_PG:-m49-gate-pg} psql -U postgres -q -c "DROP DATABASE IF EXISTS $TMPL WITH (FORCE)" -c "CREATE DATABASE $TMPL" >/dev/null
DATABASE_URL="postgresql+asyncpg://postgres@127.0.0.1:25432/$TMPL" python -m alembic upgrade head 2>&1 | tail -1
docker exec -i ${GATE_PG:-m49-gate-pg} psql -U postgres -d "$TMPL" -q <<'SQL'
INSERT INTO customers (id, code, name, channel, payment_terms_days, currency, is_active, is_prepaid, email) VALUES
 (gen_random_uuid(), 'SYN-T1', 'POVU Synthetic Outlet 1', 'RETAIL', 30, 'KES', true, false, 'o1@povu-demo.test'),
 (gen_random_uuid(), 'SYN-T2', 'POVU Synthetic Outlet 2', 'WHOLESALE', 30, 'KES', true, false, 'o2@povu-demo.test');
INSERT INTO products (id, sku, name, category, uom, units_per_carton, reorder_point, is_active) VALUES
 (gen_random_uuid(), 'POVU-SYN-ALC-1L', 'POVU AllClean 1 L (synthetic)', 'HOUSEHOLD', 'PCS', 12, 0, true);
INSERT INTO crm_pipeline_stages (id, stage_code, stage_name, stage_type, sequence_no, default_probability, active_flag, pipeline_id)
 SELECT gen_random_uuid(), c, n, t::crmstagetype, s, p, true, (SELECT id FROM crm_pipelines WHERE is_default)
 FROM (VALUES ('SYN-LEAD','Lead','LEAD',1,10), ('SYN-QUAL','Qualified','OPPORTUNITY',2,40)) v(c,n,t,s,p);
SQL
docker exec ${GATE_PG:-m49-gate-pg} psql -U postgres -d "$TMPL" -tc "select version_num from alembic_version"
