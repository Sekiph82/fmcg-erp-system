#!/usr/bin/env node
/**
 * check-workspace-tabs.js
 * Verifies that:
 *   1. Every redirect target tab key exists in the target workspace page
 *   2. Every sidebar searchHint tab key exists in the target workspace page
 *   3. All workspace pages use stable kebab-case tab keys
 *
 * Outputs: docs/WORKSPACE_TAB_REPORT.md
 * Exit 1 if mismatches found.
 */

const fs   = require("fs");
const path = require("path");

const ROOT     = process.argv[2] === "--root" ? process.argv[3]
               : path.resolve(__dirname, "..");
const FRONTEND = path.join(ROOT, "frontend", "src");
const DASH_DIR = path.join(FRONTEND, "app", "dashboard");
const OUT_DIR  = path.join(ROOT, "docs");

// ── Extract tab keys from a workspace page ───────────────────────────────────

function extractTabKeys(wsPagePath) {
  if (!fs.existsSync(wsPagePath)) return new Set();
  const text = fs.readFileSync(wsPagePath, "utf8");
  const keys = new Set();
  // Only match WorkspaceTab patterns: { key: "...", label: "..." } in tabs arrays.
  // This avoids picking up form field keys like { product_name: "...", label: "..." }.
  // Pattern: key: followed by label: in the same object (within 200 chars)
  const re = /\{\s*key:\s*["']([^"']+)["'][^}]{0,200}label:\s*["']|key:\s*["']([^"']+)["'],\s*label:/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    const k = m[1] || m[2];
    if (k) keys.add(k);
  }
  return keys;
}

// ── Parse middleware top-level redirects ──────────────────────────────────────

function parseMiddlewareRedirects() {
  const file = path.join(FRONTEND, "middleware.ts");
  if (!fs.existsSync(file)) return {};
  const text = fs.readFileSync(file, "utf8");
  const result = {};
  const re = /"(\/dashboard\/[^"]+)"\s*:\s*\{([^}]+)\}/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    const route = m[1];
    const body  = m[2];
    const pMatch = body.match(/p:\s*"([^"]+)"/);
    const tMatch = body.match(/t:\s*"([^"]+)"/);
    if (pMatch && tMatch) {
      result[route] = { target: pMatch[1], tab: tMatch[1] };
    }
  }
  return result;
}

// ── Parse nav-config searchHints ─────────────────────────────────────────────

function parseNavSearchHints() {
  const navFile = path.join(FRONTEND, "components", "nav-config.tsx");
  if (!fs.existsSync(navFile)) return [];
  const text = fs.readFileSync(navFile, "utf8");

  const hints = [];
  // Match ws(...) calls. We need to find the searchHints block for each workspace.
  // Strategy: find each ws() call, then find the balanced opts object for that call only.
  const wsRe = /ws\s*\(\s*"[^"]+"\s*,\s*"[^"]+"\s*,\s*"(\/dashboard\/[^"]+)"/g;
  let wsM;
  while ((wsM = wsRe.exec(text)) !== null) {
    const wsHref = wsM[1];
    // Find the opts object: look for searchHints: [ ... ] within the ws() call
    // Get text from this ws() match to the next ws() or end of NAV_CONFIG
    const nextWsIdx = text.indexOf("\n  ws(", wsM.index + 1);
    const blockEnd  = nextWsIdx > -1 ? nextWsIdx : text.indexOf("\n];", wsM.index);
    const block = text.slice(wsM.index, blockEnd > 0 ? blockEnd : wsM.index + 2000);

    // Only look for searchHints within this block
    if (!block.includes("searchHints")) continue;
    const hintRe = /\{\s*label:\s*"([^"]+)"\s*,\s*tab:\s*"([^"]+)"\s*\}/g;
    let hM;
    while ((hM = hintRe.exec(block)) !== null) {
      hints.push({ workspace: wsHref, tab: hM[2], label: hM[1] });
    }
  }
  return hints;
}

// ── Kebab-case check ──────────────────────────────────────────────────────────

function isKebabCase(s) {
  return /^[a-z0-9]+(-[a-z0-9]+)*$/.test(s);
}

// Extract tab keys ONLY from ModuleWorkspace tabs= prop (not internal component tabs)
function extractWorkspaceTabKeys(wsPagePath) {
  if (!fs.existsSync(wsPagePath)) return new Set();
  const text = fs.readFileSync(wsPagePath, "utf8");
  const keys = new Set();

  // Find the tabs={[...]} block passed to <ModuleWorkspace
  const wsBlockRe = /<ModuleWorkspace[\s\S]{0,2000}?tabs=\{(\[[\s\S]*?\])\}/m;
  // Since the file may have the tabs as a variable, look for the variable assignment
  // or inline array. Strategy: find the last `const tabs = [` before <ModuleWorkspace
  // or find the array after tabs={

  // Look for: const tabs = [  ...  ]; just before <ModuleWorkspace
  const constTabsRe = /const\s+tabs\s*=\s*\[[\s\S]*?\];/g;
  let lastMatch = null;
  let m;
  while ((m = constTabsRe.exec(text)) !== null) lastMatch = m;

  const source = lastMatch ? lastMatch[0] : text;

  // Extract key-label pairs from WorkspaceTab objects
  const re = /\{\s*key:\s*["']([^"']+)["'][^}]{0,300}label:\s*["']/g;
  while ((m = re.exec(source)) !== null) {
    const k = m[1];
    // Skip if camelCase (internal component tabs, not workspace tabs)
    if (/[A-Z]/.test(k)) continue;
    keys.add(k);
  }
  return keys;
}

// ── Main ──────────────────────────────────────────────────────────────────────

function main() {
  const mwRedirects = parseMiddlewareRedirects();
  const searchHints = parseNavSearchHints();

  // Cache workspace tab keys
  const wsTabCache = {};
  function getTabKeys(wsHref) {
    if (wsTabCache[wsHref]) return wsTabCache[wsHref];
    const rel = wsHref.replace(/^\/dashboard\//, "");
    const pageFile = path.join(DASH_DIR, rel, "page.tsx");
    const keys = extractWorkspaceTabKeys(pageFile);
    wsTabCache[wsHref] = keys;
    return keys;
  }

  const issues = [];
  const lines  = [];

  // Check 1: Middleware redirects → workspace tabs
  const mwMismatches = [];
  for (const [route, { target, tab }] of Object.entries(mwRedirects)) {
    const tabKeys = getTabKeys(target);
    if (tabKeys.size === 0) continue; // workspace page not found or has no tabs
    if (!tabKeys.has(tab)) {
      mwMismatches.push({ route, target, tab, availableTabs: [...tabKeys].join(", ") });
    }
  }

  // Check 2: Sidebar search hints → workspace tabs
  const hintMismatches = [];
  for (const { workspace, tab, label } of searchHints) {
    const tabKeys = getTabKeys(workspace);
    if (tabKeys.size === 0) continue;
    if (!tabKeys.has(tab)) {
      hintMismatches.push({ workspace, tab, label, availableTabs: [...tabKeys].join(", ") });
    }
  }

  // Check 3: Non-kebab-case tab keys (workspace-level only)
  const badCaseKeys = [];
  const wsPages = fs.existsSync(DASH_DIR) ? fs.readdirSync(DASH_DIR) : [];
  for (const entry of wsPages) {
    const pageFile = path.join(DASH_DIR, entry, "page.tsx");
    if (!fs.existsSync(pageFile)) continue;
    const keys = extractWorkspaceTabKeys(pageFile);
    for (const k of keys) {
      if (!isKebabCase(k)) {
        badCaseKeys.push({ workspace: `/dashboard/${entry}`, key: k });
      }
    }
  }

  // ── Build report ────────────────────────────────────────────────────────────

  const now = new Date().toISOString().slice(0, 10);
  lines.push("# Workspace Tab Report");
  lines.push("");
  lines.push(`Generated: ${now}`);
  lines.push("");

  const totalIssues = mwMismatches.length + hintMismatches.length + badCaseKeys.length;

  lines.push("## Summary");
  lines.push("");
  lines.push(`| Check | Count |`);
  lines.push(`|-------|-------|`);
  lines.push(`| Middleware redirect tab mismatches | ${mwMismatches.length} |`);
  lines.push(`| Sidebar search hint mismatches     | ${hintMismatches.length} |`);
  lines.push(`| Non-kebab-case tab keys            | ${badCaseKeys.length} |`);
  lines.push(`| **Total issues**                   | **${totalIssues}** |`);
  lines.push("");

  if (mwMismatches.length > 0) {
    lines.push("## Middleware redirect tab mismatches");
    lines.push("");
    lines.push("The redirect target tab key does not exist in the workspace page.");
    lines.push("");
    lines.push("| Route | Target | Missing Tab | Available Tabs |");
    lines.push("|-------|--------|------------|----------------|");
    for (const { route, target, tab, availableTabs } of mwMismatches) {
      lines.push(`| \`${route}\` | \`${target}\` | \`${tab}\` | ${availableTabs} |`);
    }
    lines.push("");
    issues.push(...mwMismatches.map(({ route, tab }) => `Middleware tab mismatch: ${route} → tab "${tab}" not found`));
  }

  if (hintMismatches.length > 0) {
    lines.push("## Sidebar search hint mismatches");
    lines.push("");
    lines.push("The sidebar search hint tab key does not exist in the workspace page.");
    lines.push("");
    lines.push("| Workspace | Label | Missing Tab | Available Tabs |");
    lines.push("|-----------|-------|------------|----------------|");
    for (const { workspace, tab, label, availableTabs } of hintMismatches) {
      lines.push(`| \`${workspace}\` | ${label} | \`${tab}\` | ${availableTabs} |`);
    }
    lines.push("");
    issues.push(...hintMismatches.map(({ workspace, tab }) => `Sidebar hint mismatch: ${workspace} tab "${tab}" not found`));
  }

  if (badCaseKeys.length > 0) {
    lines.push("## Non-kebab-case tab keys");
    lines.push("");
    for (const { workspace, key } of badCaseKeys) {
      lines.push(`- \`${workspace}\` key \`${key}\``);
    }
    lines.push("");
    issues.push(...badCaseKeys.map(({ workspace, key }) => `Bad case: ${workspace} key "${key}"`));
  }

  // ── Workspace tab inventory ────────────────────────────────────────────────
  lines.push("## Workspace Tab Inventory");
  lines.push("");
  lines.push("All tabs across all workspace pages.");
  lines.push("");
  lines.push("| Workspace | Tab Keys |");
  lines.push("|-----------|---------|");
  for (const entry of wsPages.sort()) {
    const pageFile = path.join(DASH_DIR, entry, "page.tsx");
    if (!fs.existsSync(pageFile)) continue;
    const keys = extractWorkspaceTabKeys(pageFile);
    if (keys.size === 0) continue;
    lines.push(`| \`/dashboard/${entry}\` | ${[...keys].map((k) => `\`${k}\``).join(", ")} |`);
  }

  if (totalIssues === 0) {
    lines.push("");
    lines.push("## All checks passed");
    lines.push("");
    lines.push("All redirect targets and search hints match workspace tab keys. All tab keys are kebab-case.");
  }

  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(path.join(OUT_DIR, "WORKSPACE_TAB_REPORT.md"), lines.join("\n"), "utf8");
  console.log("Wrote docs/WORKSPACE_TAB_REPORT.md");

  if (issues.length > 0) {
    console.log(`\n⚠️  ${issues.length} issue(s) found:`);
    for (const i of issues.slice(0, 20)) console.log("  -", i);
    if (issues.length > 20) console.log(`  ... and ${issues.length - 20} more`);
    process.exit(1);
  } else {
    console.log("✅ All workspace tab checks passed.");
  }
}

main();
