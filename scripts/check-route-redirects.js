#!/usr/bin/env node
/**
 * check-route-redirects.js
 * Verifies consistency between routeRedirectMap.ts and middleware.ts.
 *
 * Checks:
 *   1. Every top-level redirect key in routeRedirectMap is in middleware
 *   2. Every middleware redirect key has an entry in routeRedirectMap
 *   3. No redirect loops
 *   4. All redirect targets exist as dashboard directories
 *   5. No duplicate keys
 *
 * Outputs: docs/ROUTE_REDIRECT_REPORT.md
 * Exit 1 if any mismatches found.
 */

const fs   = require("fs");
const path = require("path");

const ROOT     = process.argv[2] === "--root" ? process.argv[3]
               : path.resolve(__dirname, "..");
const FRONTEND = path.join(ROOT, "frontend", "src");
const DASH_DIR = path.join(FRONTEND, "app", "dashboard");
const OUT_DIR  = path.join(ROOT, "docs");

// ── Parse routeRedirectMap.ts ─────────────────────────────────────────────────

function parseRedirectMap() {
  const file = path.join(FRONTEND, "lib", "routeRedirectMap.ts");
  if (!fs.existsSync(file)) {
    console.error("routeRedirectMap.ts not found at", file);
    return {};
  }
  const text = fs.readFileSync(file, "utf8");
  const result = {};
  // Match: "/dashboard/foo": { pathname: "...", tab: "..." }
  const re = /"(\/dashboard\/[^"]+)"\s*:\s*\{([^}]+)\}/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    const route = m[1];
    const body  = m[2];
    if (result[route]) {
      result[route].duplicate = true;
    } else {
      const pnMatch = body.match(/pathname:\s*"([^"]+)"/);
      const tabMatch= body.match(/tab:\s*"([^"]+)"/);
      result[route] = {
        target: pnMatch ? pnMatch[1] : "",
        tab:    tabMatch ? tabMatch[1] : "",
      };
    }
  }
  return result;
}

// ── Parse middleware.ts ────────────────────────────────────────────────────────

function parseMiddleware() {
  const file = path.join(FRONTEND, "middleware.ts");
  if (!fs.existsSync(file)) {
    console.error("middleware.ts not found at", file);
    return {};
  }
  const text = fs.readFileSync(file, "utf8");
  const result = {};
  const re = /"(\/dashboard\/[^"]+)"\s*:\s*\{([^}]+)\}/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    const route = m[1];
    const body  = m[2];
    if (result[route]) {
      result[route].duplicate = true;
    } else {
      const pMatch = body.match(/p:\s*"([^"]+)"/);
      const tMatch = body.match(/t:\s*"([^"]+)"/);
      result[route] = {
        target: pMatch ? pMatch[1] : "",
        tab:    tMatch ? tMatch[1] : "",
      };
    }
  }
  return result;
}

// ── Get top-level keys (first-level paths) ─────────────────────────────────────

function topLevelKey(route) {
  // "/dashboard/bank-reconciliation/import" → "/dashboard/bank-reconciliation"
  const parts = route.split("/");
  return parts.slice(0, 3).join("/");
}

// ── Check if target dashboard dir exists ──────────────────────────────────────

function targetExists(target) {
  if (!target) return false;
  const rel  = target.replace(/^\/dashboard\//, "");
  const dir  = path.join(DASH_DIR, rel);
  return fs.existsSync(dir);
}

// ── Main ──────────────────────────────────────────────────────────────────────

function main() {
  const rmMap = parseRedirectMap();
  const mwMap = parseMiddleware();

  const issues = [];
  const lines  = [];

  // Get unique top-level keys from routeRedirectMap
  const rmTopKeys = new Set(Object.keys(rmMap).map(topLevelKey));
  // Get keys from middleware
  const mwKeys = new Set(Object.keys(mwMap));

  // Simulate matchRedirect: does middleware handle this route?
  function mwHandles(route) {
    if (mwMap[route]) return true;
    const parts = route.split("/");
    for (let i = parts.length - 1; i >= 2; i--) {
      const prefix = parts.slice(0, i).join("/");
      if (mwMap[prefix]) return true;
    }
    return false;
  }

  // Check 1: routeRedirectMap entries NOT covered by middleware
  // Only report top-level entries that have no middleware coverage (not intra-workspace child redirects)
  const inRmNotMw = [];
  // Only consider routes where top-level != workspace destination
  const wsDestinations = new Set([
    "/dashboard/admin", "/dashboard/ai", "/dashboard/analytics", "/dashboard/bom",
    "/dashboard/communication", "/dashboard/compliance", "/dashboard/crm", "/dashboard/documents",
    "/dashboard/finance", "/dashboard/helpdesk", "/dashboard/hr", "/dashboard/integrations",
    "/dashboard/inventory", "/dashboard/logistics", "/dashboard/maintenance", "/dashboard/marketing",
    "/dashboard/materials", "/dashboard/npd", "/dashboard/payroll", "/dashboard/planning",
    "/dashboard/pos", "/dashboard/procurement", "/dashboard/production", "/dashboard/products",
    "/dashboard/quality", "/dashboard/recipes", "/dashboard/sales", "/dashboard/shop-floor",
    "/dashboard/suppliers", "/dashboard/utility-management", "/dashboard/warehouses",
  ]);
  for (const k of rmTopKeys) {
    // Skip workspace destinations — intra-workspace child redirects are handled differently
    if (wsDestinations.has(k)) continue;
    if (!mwKeys.has(k)) {
      // Get a sample entry from rmMap for this top-level key
      const sample = rmMap[k] || Object.entries(rmMap).find(([r]) => r.startsWith(k + "/"))?.[1];
      inRmNotMw.push({ key: k, sample });
    }
  }

  // Check 2: middleware keys vs routeRedirectMap (exact or prefix match)
  const inMwNotRm = [];
  for (const k of mwKeys) {
    // Skip if in rmMap directly
    if (rmMap[k]) continue;
    // Skip if a child of a workspace destination that's in rmMap
    // (e.g. /dashboard/logistics/containers is in rmMap as exact key)
    if (rmMap[k] !== undefined) continue;
    // Check if rmMap has this exact key
    const inRm = Object.keys(rmMap).some((rk) => rk === k || k.startsWith(rk + "/") || rk.startsWith(k + "/"));
    if (!inRm && !wsDestinations.has(topLevelKey(k))) {
      inMwNotRm.push(k);
    }
  }

  // Check 3b: intra-workspace routes in routeRedirectMap that have no middleware coverage
  const intraWorkspaceNotMw = [];
  for (const [route, val] of Object.entries(rmMap)) {
    const topKey = topLevelKey(route);
    if (wsDestinations.has(topKey) && !mwHandles(route)) {
      intraWorkspaceNotMw.push({ route, target: val.target, tab: val.tab });
    }
  }

  // Check 3: duplicate keys
  const rmDupes = Object.entries(rmMap).filter(([, v]) => v.duplicate).map(([k]) => k);
  const mwDupes = Object.entries(mwMap).filter(([, v]) => v.duplicate).map(([k]) => k);

  // Check 4: redirect loops
  const loops = [];
  for (const [route, val] of Object.entries(mwMap)) {
    if (val.target === topLevelKey(route)) {
      // target is the same top-level as source — potential loop
      // Only a real loop if source == target (without ?tab)
      if (val.target === topLevelKey(route) && val.target !== route) {
        // This is intentional (e.g., /dashboard/planning → /dashboard/planning?tab=advanced)
        // Not a loop since the tab param prevents re-match
      } else if (val.target === route) {
        loops.push(route);
      }
    }
  }

  // Check 5: missing targets
  const missingTargets = [];
  for (const [route, val] of Object.entries(mwMap)) {
    if (!targetExists(val.target)) {
      missingTargets.push({ route, target: val.target });
    }
  }

  // ── Write report ────────────────────────────────────────────────────────────

  const now = new Date().toISOString().slice(0, 10);
  lines.push("# Route Redirect Report");
  lines.push("");
  lines.push(`Generated: ${now}`);
  lines.push("");

  const totalIssues = inRmNotMw.length + inMwNotRm.length + rmDupes.length + mwDupes.length + loops.length + missingTargets.length + intraWorkspaceNotMw.length;

  lines.push("## Summary");
  lines.push("");
  lines.push(`| Check | Count |`);
  lines.push(`|-------|-------|`);
  lines.push(`| routeRedirectMap top-level keys | ${rmTopKeys.size} |`);
  lines.push(`| middleware redirect keys        | ${mwKeys.size} |`);
  lines.push(`| In routeRedirectMap NOT middleware | ${inRmNotMw.length} |`);
  lines.push(`| In middleware NOT routeRedirectMap | ${inMwNotRm.length} |`);
  lines.push(`| Duplicate keys in routeRedirectMap | ${rmDupes.length} |`);
  lines.push(`| Duplicate keys in middleware        | ${mwDupes.length} |`);
  lines.push(`| Redirect loops                      | ${loops.length} |`);
  lines.push(`| Missing redirect targets            | ${missingTargets.length} |`);
  lines.push(`| Intra-workspace routes not in MW    | ${intraWorkspaceNotMw.length} |`);
  lines.push(`| **Total issues**                    | **${totalIssues}** |`);
  lines.push("");

  if (inRmNotMw.length > 0) {
    lines.push("## In routeRedirectMap top-level keys but NOT in middleware");
    lines.push("");
    lines.push("These routes are documented in routeRedirectMap.ts but have no middleware redirect.");
    lines.push("Users who navigate directly will NOT be redirected.");
    lines.push("");
    for (const { key, sample } of inRmNotMw.sort((a, b) => a.key.localeCompare(b.key))) {
      const target = sample ? `${sample.target}?tab=${sample.tab}` : "unknown";
      lines.push(`- \`${key}\` → \`${target}\``);
    }
    lines.push("");
    issues.push(...inRmNotMw.map(({ key }) => `Missing middleware: ${key}`));
  }

  if (intraWorkspaceNotMw.length > 0) {
    lines.push("## Intra-workspace routes in routeRedirectMap NOT in middleware");
    lines.push("");
    lines.push("These routes live INSIDE a workspace directory but redirect to a specific tab.");
    lines.push("They need their own middleware entries since prefix matching won't help.");
    lines.push("");
    for (const { route, target, tab } of intraWorkspaceNotMw.sort((a, b) => a.route.localeCompare(b.route))) {
      lines.push(`- \`${route}\` → \`${target}?tab=${tab}\``);
    }
    lines.push("");
    issues.push(...intraWorkspaceNotMw.map(({ route }) => `Intra-workspace not in MW: ${route}`));
  }

  if (inMwNotRm.length > 0) {
    lines.push("## In middleware but NOT in routeRedirectMap");
    lines.push("");
    lines.push("These routes redirect in middleware but are not documented in routeRedirectMap.ts.");
    lines.push("");
    for (const k of inMwNotRm.sort()) {
      const r = mwMap[k];
      lines.push(`- \`${k}\` → \`${r.target}?tab=${r.tab}\``);
    }
    lines.push("");
    issues.push(...inMwNotRm.map((k) => `Not in routeRedirectMap: ${k}`));
  }

  if (rmDupes.length > 0) {
    lines.push("## Duplicate keys in routeRedirectMap.ts");
    lines.push("");
    for (const k of rmDupes) lines.push(`- \`${k}\``);
    lines.push("");
    issues.push(...rmDupes.map((k) => `Duplicate in routeRedirectMap: ${k}`));
  }

  if (mwDupes.length > 0) {
    lines.push("## Duplicate keys in middleware.ts");
    lines.push("");
    for (const k of mwDupes) lines.push(`- \`${k}\``);
    lines.push("");
    issues.push(...mwDupes.map((k) => `Duplicate in middleware: ${k}`));
  }

  if (loops.length > 0) {
    lines.push("## Redirect loops");
    lines.push("");
    for (const k of loops) lines.push(`- \`${k}\``);
    lines.push("");
    issues.push(...loops.map((k) => `Redirect loop: ${k}`));
  }

  if (missingTargets.length > 0) {
    lines.push("## Missing redirect targets");
    lines.push("");
    lines.push("These redirect targets do not have a corresponding dashboard directory.");
    lines.push("");
    for (const { route, target } of missingTargets) {
      lines.push(`- \`${route}\` → \`${target}\` (directory not found)`);
    }
    lines.push("");
    issues.push(...missingTargets.map(({ route }) => `Missing target for: ${route}`));
  }

  if (totalIssues === 0) {
    lines.push("## All checks passed");
    lines.push("");
    lines.push("routeRedirectMap.ts and middleware.ts are in sync. No issues found.");
    lines.push("");
  }

  // ── Full middleware redirect table ─────────────────────────────────────────
  lines.push("## Full Middleware Redirect Table");
  lines.push("");
  lines.push("| Source | Target | Tab |");
  lines.push("|--------|--------|-----|");
  for (const [route, val] of Object.entries(mwMap).sort(([a], [b]) => a.localeCompare(b))) {
    lines.push(`| \`${route}\` | \`${val.target}\` | ${val.tab || "—"} |`);
  }

  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(path.join(OUT_DIR, "ROUTE_REDIRECT_REPORT.md"), lines.join("\n"), "utf8");
  console.log("Wrote docs/ROUTE_REDIRECT_REPORT.md");

  if (issues.length > 0) {
    console.log("\n⚠️  Issues found:");
    for (const i of issues) console.log("  -", i);
    process.exit(1);
  } else {
    console.log("✅ No redirect drift issues found.");
  }
}

main();
