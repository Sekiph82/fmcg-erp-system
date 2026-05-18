#!/usr/bin/env node
/**
 * Validates docs/user-manual/screenshots/routes.json
 *
 * Checks:
 *  - required fields present on every route
 *  - no duplicate IDs
 *  - no duplicate paths among capture=true routes
 *  - paths start with /login or /dashboard
 *  - warns about likely old redirect-only paths
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROUTES_FILE = path.join(
  __dirname,
  "../../docs/user-manual/screenshots/routes.json"
);

const REQUIRED_FIELDS = ["id", "title", "module", "path", "priority", "capture"];

// Old redirect-only paths that should not appear as capture targets
const KNOWN_OLD_REDIRECTS = [
  "/dashboard/mrp", "/dashboard/mps", "/dashboard/van-sales",
  "/dashboard/shelf-life", "/dashboard/traceability", "/dashboard/cycle-count",
  "/dashboard/payroll-ke", "/dashboard/gs1", "/dashboard/allergen",
  "/dashboard/qms", "/dashboard/fleet", "/dashboard/wms",
  "/dashboard/bank-reconciliation", "/dashboard/fixed-assets",
  "/dashboard/recruitment", "/dashboard/appraisals", "/dashboard/training",
];

let errors = 0;
let warnings = 0;

function error(msg) {
  console.error(`  ERROR: ${msg}`);
  errors++;
}

function warn(msg) {
  console.warn(`  WARN:  ${msg}`);
  warnings++;
}

let routes;
try {
  routes = JSON.parse(fs.readFileSync(ROUTES_FILE, "utf-8"));
} catch (e) {
  console.error(`Cannot read ${ROUTES_FILE}: ${e.message}`);
  process.exit(1);
}

console.log(`Validating ${routes.length} routes in routes.json\n`);

const seenIds = new Map();
const seenPaths = new Map();

for (const route of routes) {
  const loc = `id=${route.id ?? "(missing)"}, path=${route.path ?? "(missing)"}`;

  // Required fields
  for (const field of REQUIRED_FIELDS) {
    if (!(field in route)) {
      error(`Missing field "${field}" — ${loc}`);
    }
  }

  if (!route.id) continue;

  // Duplicate ID
  if (seenIds.has(route.id)) {
    error(`Duplicate id "${route.id}" (first at path ${seenIds.get(route.id)})`);
  } else {
    seenIds.set(route.id, route.path);
  }

  // Path format
  if (
    route.path &&
    !route.path.startsWith("/login") &&
    !route.path.startsWith("/dashboard")
  ) {
    error(`Path "${route.path}" must start with /login or /dashboard — ${loc}`);
  }

  // Duplicate path among capture=true
  if (route.capture) {
    if (seenPaths.has(route.path)) {
      error(
        `Duplicate capture path "${route.path}" (ids: ${seenPaths.get(route.path)} & ${route.id})`
      );
    } else {
      seenPaths.set(route.path, route.id);
    }
  }

  // Old redirect-only path warning
  if (route.capture && KNOWN_OLD_REDIRECTS.includes(route.path)) {
    warn(
      `"${route.path}" is a known redirect-only path — set capture=false or update to workspace tab URL`
    );
  }
}

// Summary
console.log(`Results:`);
console.log(`  Routes: ${routes.length}`);
console.log(`  Capture=true: ${routes.filter((r) => r.capture).length}`);
console.log(`  Capture=false: ${routes.filter((r) => !r.capture).length}`);
console.log(`  Errors: ${errors}`);
console.log(`  Warnings: ${warnings}`);

if (errors > 0) {
  console.error(`\nValidation FAILED — ${errors} error(s)`);
  process.exit(1);
} else {
  console.log(`\nValidation PASSED`);
}
