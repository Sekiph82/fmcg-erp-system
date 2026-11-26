#!/usr/bin/env bash
# M46 gate: prior-feature regressions touched by M46 (timeline, KB, web analytics, config bundles), each on a fresh
# copy of the M46 head template (run_m46_db_tests.sh creates m46_tmpl). Disposable PostgreSQL only.
set -u
PG=127.0.0.1:25432
cd "$(dirname "$0")/../../../../backend"
run() {  # file db-name extra-env...
  local f=$1 db=$2; shift 2
  docker exec m46-gate-pg psql -U postgres -q -c "DROP DATABASE IF EXISTS $db" -c "CREATE DATABASE $db TEMPLATE m46_tmpl"     -c "DROP DATABASE IF EXISTS ${db}_b" -c "CREATE DATABASE ${db}_b TEMPLATE m46_tmpl" >/dev/null 2>&1
  out=$(env "$@" DATABASE_URL="postgresql+asyncpg://postgres@$PG/$db" timeout 600 python -m pytest -q --no-header -p no:cacheprovider "$f" 2>&1 | tail -25)
  echo "== $f :: $(echo "$out" | tail -1)"
  echo "$out" | tail -1 | grep -qE "failed|error" && echo "$out"
  docker exec m46-gate-pg psql -U postgres -q -c "DROP DATABASE IF EXISTS $db" -c "DROP DATABASE IF EXISTS ${db}_b" >/dev/null 2>&1
}
h=$(printf '%024x' $RANDOM$RANDOM | cut -c1-24)
run tests/test_m36_s03_customer_timeline_db.py "fmcg_m36_s03_$h" M36_S03_DISPOSABLE_TEST_DATABASE=1 M36_S03_DISPOSABLE_TEST_DATABASE_NAME="fmcg_m36_s03_$h"
run tests/test_m36_s04_t005_kb_db.py "fmcg_m36_s04_$h" M36_S04_DISPOSABLE_TEST_DATABASE=1 M36_S04_DISPOSABLE_TEST_DATABASE_NAME="fmcg_m36_s04_$h"
run tests/test_m44_s01_t009_web_analytics_db.py "g_m44_web" M44_DB=1
run tests/test_m45_s01_t018_config_bundle.py "g_m45_bundle" M45_DB=1 M45_DB2_URL="postgresql+asyncpg://postgres@$PG/g_m45_bundle_b"
