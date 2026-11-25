#!/usr/bin/env bash
# M45 gate: run every M45 DB-gated test file (FILES overrides) on its own fresh copy of a head template (disposable PostgreSQL only).
set -u
PG=127.0.0.1:25432
cd "$(dirname "$0")/../../../../backend"
docker exec m45-gate-pg psql -U postgres -q -c "DROP DATABASE IF EXISTS m45_tmpl" -c "CREATE DATABASE m45_tmpl TEMPLATE m45_head" >/dev/null
docker exec -i m45-gate-pg psql -U postgres -d m45_tmpl -q <<'SQL'
INSERT INTO customers (id, code, name, channel, payment_terms_days, currency, is_active, is_prepaid, email) VALUES
 (gen_random_uuid(), 'SYN-T1', 'POVU Synthetic Outlet 1', 'RETAIL', 30, 'KES', true, false, 'o1@povu-demo.test'),
 (gen_random_uuid(), 'SYN-T2', 'POVU Synthetic Outlet 2', 'WHOLESALE', 30, 'KES', true, false, 'o2@povu-demo.test');
INSERT INTO products (id, sku, name, category, uom, units_per_carton, reorder_point, is_active) VALUES
 (gen_random_uuid(), 'POVU-SYN-500', 'POVU Synthetic 500 ml', 'BEVERAGE', 'PCS', 24, 0, true);
INSERT INTO crm_pipeline_stages (id, stage_code, stage_name, stage_type, sequence_no, default_probability, active_flag, pipeline_id)
 SELECT gen_random_uuid(), c, n, t::crmstagetype, s, p, true, (SELECT id FROM crm_pipelines WHERE is_default)
 FROM (VALUES ('SYN-LEAD','Lead','LEAD',1,10), ('SYN-QUAL','Qualified','OPPORTUNITY',2,40)) v(c,n,t,s,p);
SQL
pass=0; fail=0
for f in ${FILES:-tests/test_m45_*.py}; do
  db="g_$(basename "$f" .py | tr -c 'a-z0-9_' '_' | cut -c1-50)"
  docker exec m45-gate-pg psql -U postgres -q -c "DROP DATABASE IF EXISTS $db" -c "CREATE DATABASE $db TEMPLATE m45_tmpl" >/dev/null
  out=$(DATABASE_URL="postgresql+asyncpg://postgres@$PG/$db" M43_S01_DB=1 M43_S00_T004_DB=1 M44_DB=1 M45_DB=1 \
        timeout 600 python -m pytest -q --no-header -p no:cacheprovider "$f" 2>&1 | tail -25)
  line=$(echo "$out" | tail -1)
  echo "== $f :: $line"
  if echo "$line" | grep -qE "failed|error"; then fail=$((fail+1)); echo "$out"; else pass=$((pass+1)); fi
  docker exec m45-gate-pg psql -U postgres -q -c "DROP DATABASE IF EXISTS $db" >/dev/null
done
echo "FILES PASS=$pass FAIL=$fail"
