#!/usr/bin/env node
/**
 * audit-page-count.js
 * Classifies every page.tsx under frontend/src/app/dashboard/.
 *
 * Classifications:
 *   A  WORKSPACE_PAGE        – renders <ModuleWorkspace tabs={...}>
 *   B  REDIRECT_ONLY         – file body is just a redirect() / permanentRedirect()
 *   C  LIGHTWEIGHT_WRAPPER   – dynamically imported as a tab by a workspace page
 *   D  FULL_DUPLICATE_UI     – has own API/state/forms, NOT imported as a tab
 *   E  STANDALONE_OPERATIONAL– special full-screen tools (POS, shop-floor, login)
 *   F  UNKNOWN               – cannot classify
 *
 * Outputs: docs/PAGE_ROUTE_CLASSIFICATION_REPORT.md
 *          docs/PAGE_COUNT_REPORT.md
 *
 * Usage: node scripts/audit-page-count.js [--root <dir>]
 */

const fs   = require("fs");
const path = require("path");

// ── Config ────────────────────────────────────────────────────────────────────

const ROOT     = process.argv[2] === "--root" ? process.argv[3]
               : path.resolve(__dirname, "..");
const FRONTEND = path.join(ROOT, "frontend", "src");
const DASH_DIR = path.join(FRONTEND, "app", "dashboard");
const OUT_DIR  = path.join(ROOT, "docs");

// ── Known standalone operational pages ────────────────────────────────────────

const STANDALONE_DIRS = new Set([
  "pos",
  "shop-floor",
  "login",
  "auth",
  "npd",
  "recipes",
]);

// ── Middleware top-level redirect keys ────────────────────────────────────────
// Parsed from frontend/src/middleware.ts at runtime below.

function parseMiddlewareRedirects() {
  const mwPath = path.join(FRONTEND, "middleware.ts");
  if (!fs.existsSync(mwPath)) return {};
  const text = fs.readFileSync(mwPath, "utf8");
  const result = {};
  // Match: "/dashboard/foo/bar": { p: "...", t: "..." }
  const re = /"(\/dashboard\/[^"]+)"\s*:\s*\{([^}]+)\}/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    const route = m[1];
    const body  = m[2];
    const pMatch = body.match(/p:\s*"([^"]+)"/);
    const tMatch = body.match(/t:\s*"([^"]+)"/);
    result[route] = {
      target: pMatch ? pMatch[1] : "",
      tab:    tMatch ? tMatch[1] : "",
    };
  }
  return result;
}

// ── Parse dynamic imports from workspace pages ─────────────────────────────────

function collectWorkspaceImports() {
  // imported[normalizedPath] = true
  const imported = {};
  if (!fs.existsSync(DASH_DIR)) return imported;
  for (const entry of fs.readdirSync(DASH_DIR)) {
    const pageFile = path.join(DASH_DIR, entry, "page.tsx");
    if (!fs.existsSync(pageFile)) continue;
    const text = fs.readFileSync(pageFile, "utf8");
    // Match: dynamic(() => import("@/app/dashboard/..."))
    const re = /dynamic\(\s*\(\)\s*=>\s*import\(\s*"@\/app\/dashboard\/([^"]+)"\s*\)/g;
    let m;
    while ((m = re.exec(text)) !== null) {
      // Normalize: strip trailing /page if present
      let imp = m[1].replace(/\/page$/, "");
      imported[imp] = true;
    }
  }
  return imported;
}

// ── Walk files ────────────────────────────────────────────────────────────────

function walkPages(dir, results = []) {
  if (!fs.existsSync(dir)) return results;
  for (const entry of fs.readdirSync(dir)) {
    const full = path.join(dir, entry);
    const stat = fs.statSync(full);
    if (stat.isDirectory()) {
      walkPages(full, results);
    } else if (entry === "page.tsx") {
      results.push(full);
    }
  }
  return results;
}

// ── Classify a single page ────────────────────────────────────────────────────

function classify(filePath, workspaceImports, mwRedirects) {
  const text = fs.existsSync(filePath) ? fs.readFileSync(filePath, "utf8") : "";

  // Route path relative to /dashboard
  const rel      = path.relative(DASH_DIR, filePath).replace(/\\/g, "/");
  const parts    = rel.split("/");
  const topDir   = parts[0];
  const routePath= "/dashboard/" + parts.slice(0, -1).join("/");  // strip /page.tsx

  // ── A. WORKSPACE_PAGE ──────────────────────────────────────────────────────
  if (text.includes("<ModuleWorkspace") && text.includes("tabs={")) {
    return { cls: "A", label: "WORKSPACE_PAGE" };
  }

  // ── B. REDIRECT_ONLY ──────────────────────────────────────────────────────
  const nonComment = text.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*/g, "");
  const hasRedirect = /\bpermanentRedirect\s*\(|(?<!\w)redirect\s*\(/.test(nonComment);
  const hasRealContent = /useQuery|useMutation|useState|useEffect|fetch\s*\(|axios\s*\.|<form|<Form/.test(text);
  if (hasRedirect && !hasRealContent) {
    return { cls: "B", label: "REDIRECT_ONLY" };
  }

  // ── Path-specific STANDALONE overrides ────────────────────────────────────
  // Root dashboard page — primary landing page, not a navigation duplicate
  if (parts.length === 1 && parts[0] === "page.tsx") {
    return { cls: "E", label: "STANDALONE_OPERATIONAL" };
  }
  // bom/[id] and its sub-pages (costing, compliance, explode) — rich formula editors.
  // Cannot add "bom" to STANDALONE_DIRS because bom/compare, bom/substitutes,
  // bom/conversion are C=LIGHTWEIGHT_WRAPPER (dynamically imported by bom/page.tsx).
  if (topDir === "bom" && parts[1] === "[id]") {
    return { cls: "E", label: "STANDALONE_OPERATIONAL" };
  }

  // ── E. STANDALONE_OPERATIONAL ─────────────────────────────────────────────
  if (STANDALONE_DIRS.has(topDir)) {
    return { cls: "E", label: "STANDALONE_OPERATIONAL" };
  }

  // ── C. LIGHTWEIGHT_WRAPPER (dynamically imported by a workspace) ──────────
  // Build the import key from the relative path (strip /page.tsx)
  const importKey = parts.slice(0, -1).join("/");  // e.g. "finance/cashbook"
  if (workspaceImports[importKey]) {
    return { cls: "C", label: "LIGHTWEIGHT_WRAPPER" };
  }
  // Also check just top-level e.g. "bank-reconciliation"
  if (workspaceImports[topDir] && parts.length === 2) {
    return { cls: "C", label: "LIGHTWEIGHT_WRAPPER" };
  }

  // ── D. FULL_DUPLICATE_UI ──────────────────────────────────────────────────
  const hasDuplUI = /useQuery|useMutation|useState|useEffect|fetch\s*\(|axios\s*\./.test(text);
  if (hasDuplUI) {
    return { cls: "D", label: "FULL_DUPLICATE_UI" };
  }

  return { cls: "F", label: "UNKNOWN" };
}

// ── Check middleware coverage ─────────────────────────────────────────────────

function isCoveredByMiddleware(routePath, mwRedirects) {
  if (mwRedirects[routePath]) return true;
  // Prefix match
  const parts = routePath.split("/");
  for (let i = parts.length - 1; i >= 2; i--) {
    const prefix = parts.slice(0, i).join("/");
    if (mwRedirects[prefix]) return true;
  }
  return false;
}

// ── Read nav-config for sidebar links ─────────────────────────────────────────

function getSidebarWorkspaceHrefs() {
  const navFile = path.join(FRONTEND, "components", "nav-config.tsx");
  if (!fs.existsSync(navFile)) return new Set();
  const text = fs.readFileSync(navFile, "utf8");
  const hrefs = new Set();
  const re = /href:\s*"(\/dashboard\/[^"]+)"/g;
  let m;
  while ((m = re.exec(text)) !== null) hrefs.add(m[1]);
  return hrefs;
}

// ── Main ──────────────────────────────────────────────────────────────────────

function main() {
  console.log("Auditing pages in", DASH_DIR);

  const mwRedirects      = parseMiddlewareRedirects();
  const workspaceImports = collectWorkspaceImports();
  const sidebarHrefs     = getSidebarWorkspaceHrefs();

  const pages = walkPages(DASH_DIR);
  console.log(`Found ${pages.length} page.tsx files`);

  const rows = [];
  const counts = { A: 0, B: 0, C: 0, D: 0, E: 0, F: 0 };

  for (const filePath of pages.sort()) {
    const rel       = path.relative(DASH_DIR, filePath).replace(/\\/g, "/");
    const parts     = rel.split("/");
    const routePath = "/dashboard/" + parts.slice(0, -1).join("/");
    const { cls, label } = classify(filePath, workspaceImports, mwRedirects);
    const mwCovered  = isCoveredByMiddleware(routePath, mwRedirects);
    const inSidebar  = sidebarHrefs.has(routePath);
    counts[cls]++;

    // Determine target workspace/tab from middleware
    let targetWorkspace = "";
    let targetTab = "";
    if (mwRedirects[routePath]) {
      targetWorkspace = mwRedirects[routePath].target;
      targetTab = mwRedirects[routePath].tab;
    } else {
      // Prefix match
      const ps = routePath.split("/");
      for (let i = ps.length - 1; i >= 2; i--) {
        const prefix = ps.slice(0, i).join("/");
        if (mwRedirects[prefix]) {
          targetWorkspace = mwRedirects[prefix].target;
          targetTab = mwRedirects[prefix].tab;
          break;
        }
      }
    }

    rows.push({ routePath, filePath: rel, cls, label, mwCovered, inSidebar, targetWorkspace, targetTab });
  }

  // ── Write PAGE_COUNT_REPORT.md ─────────────────────────────────────────────
  const now = new Date().toISOString().slice(0, 10);
  const countLines = [
    "# Page Count Report",
    "",
    `Generated: ${now}`,
    "",
    "## Summary",
    "",
    `| Classification            | Code | Count |`,
    `|---------------------------|------|-------|`,
    `| WORKSPACE_PAGE            | A    | ${counts.A}   |`,
    `| REDIRECT_ONLY             | B    | ${counts.B}   |`,
    `| LIGHTWEIGHT_WRAPPER       | C    | ${counts.C}   |`,
    `| FULL_DUPLICATE_UI         | D    | ${counts.D}   |`,
    `| STANDALONE_OPERATIONAL    | E    | ${counts.E}   |`,
    `| UNKNOWN                   | F    | ${counts.F}   |`,
    `| **Total**                 |      | **${pages.length}** |`,
    "",
    "## Definitions",
    "",
    "- **A WORKSPACE_PAGE** — renders `<ModuleWorkspace tabs={...}>` — these are the destination pages.",
    "- **B REDIRECT_ONLY** — page body only calls `redirect()` / `permanentRedirect()` — no UI.",
    "- **C LIGHTWEIGHT_WRAPPER** — dynamically imported as a tab by a workspace page. Stays as-is.",
    "- **D FULL_DUPLICATE_UI** — has own API calls/state/forms and is NOT used as a workspace tab.",
    "  These are the pages to migrate or convert to redirect-only.",
    "- **E STANDALONE_OPERATIONAL** — full-screen tool that must remain standalone (POS, shop-floor).",
    "- **F UNKNOWN** — could not classify from content heuristics.",
    "",
    "## FULL_DUPLICATE_UI pages by module",
    "",
  ];

  // Group D pages by top-level module
  const dupsByModule = {};
  for (const row of rows) {
    if (row.cls !== "D") continue;
    const top = row.routePath.split("/")[2] || "root";
    if (!dupsByModule[top]) dupsByModule[top] = [];
    dupsByModule[top].push(row);
  }

  const modules = Object.entries(dupsByModule).sort((a, b) => b[1].length - a[1].length);
  for (const [mod, rs] of modules) {
    countLines.push(`### ${mod} (${rs.length} pages)`);
    countLines.push("");
    for (const r of rs) {
      const mw = r.mwCovered ? "✅" : "❌";
      countLines.push(`- \`${r.routePath}\` ${mw} MW`);
    }
    countLines.push("");
  }

  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(path.join(OUT_DIR, "PAGE_COUNT_REPORT.md"), countLines.join("\n"), "utf8");
  console.log("Wrote docs/PAGE_COUNT_REPORT.md");

  // ── Write PAGE_ROUTE_CLASSIFICATION_REPORT.md ──────────────────────────────

  const reportLines = [
    "# Page Route Classification Report",
    "",
    `Generated: ${now}`,
    "",
    "## Summary",
    "",
    `| Classification            | Count |`,
    `|---------------------------|-------|`,
    `| A WORKSPACE_PAGE          | ${counts.A}     |`,
    `| B REDIRECT_ONLY           | ${counts.B}     |`,
    `| C LIGHTWEIGHT_WRAPPER     | ${counts.C}     |`,
    `| D FULL_DUPLICATE_UI       | ${counts.D}     |`,
    `| E STANDALONE_OPERATIONAL  | ${counts.E}     |`,
    `| F UNKNOWN                 | ${counts.F}     |`,
    `| Total                     | ${pages.length}   |`,
    "",
    "## All Routes",
    "",
    "| Route | Classification | MW Covered | Sidebar | Target Workspace | Target Tab |",
    "|-------|---------------|-----------|---------|-----------------|-----------|",
  ];

  for (const row of rows) {
    const mw  = row.mwCovered ? "✅" : "❌";
    const sb  = row.inSidebar ? "✅" : "—";
    const tw  = row.targetWorkspace || "—";
    const tt  = row.targetTab || "—";
    reportLines.push(`| \`${row.routePath}\` | ${row.cls} ${row.label} | ${mw} | ${sb} | ${tw} | ${tt} |`);
  }

  fs.writeFileSync(
    path.join(OUT_DIR, "PAGE_ROUTE_CLASSIFICATION_REPORT.md"),
    reportLines.join("\n"),
    "utf8"
  );
  console.log("Wrote docs/PAGE_ROUTE_CLASSIFICATION_REPORT.md");

  // ── Summary ────────────────────────────────────────────────────────────────
  console.log("\n=== Summary ===");
  console.log(`A WORKSPACE_PAGE:       ${counts.A}`);
  console.log(`B REDIRECT_ONLY:        ${counts.B}`);
  console.log(`C LIGHTWEIGHT_WRAPPER:  ${counts.C}`);
  console.log(`D FULL_DUPLICATE_UI:    ${counts.D}`);
  console.log(`E STANDALONE_OPERATIONAL: ${counts.E}`);
  console.log(`F UNKNOWN:              ${counts.F}`);
  console.log(`Total pages:            ${pages.length}`);
}

main();
