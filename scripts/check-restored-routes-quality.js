#!/usr/bin/env node
/**
 * Checks every BYPASS_PREFIX_REDIRECT route and reports:
 * - page file exists
 * - line count
 * - redirect-only (≤8 non-empty lines with redirect())
 * - contains meaningful UI (has JSX/return statement beyond redirect)
 */
const fs = require("fs");
const path = require("path");

const FRONTEND = path.join(__dirname, "..", "frontend", "src", "app");
const MIDDLEWARE = path.join(__dirname, "..", "frontend", "src", "middleware.ts");

// Extract BYPASS_PREFIX_REDIRECT set from middleware.ts
const mw = fs.readFileSync(MIDDLEWARE, "utf8");
const m = mw.match(/const BYPASS_PREFIX_REDIRECT = new Set\(\[([\s\S]*?)\]\)/);
if (!m) { console.error("Could not find BYPASS_PREFIX_REDIRECT"); process.exit(1); }
const routes = (m[1].match(/"(\/dashboard\/[^"]+)"/g) || []).map((s) => s.replace(/"/g, ""));

const results = routes.map((route) => {
  const rel = route.replace("/dashboard", "dashboard");
  const file = path.join(FRONTEND, rel, "page.tsx");
  if (!fs.existsSync(file)) {
    return { route, exists: false, lineCount: 0, redirectOnly: false, hasUI: false, status: "MISSING" };
  }
  const src = fs.readFileSync(file, "utf8");
  const lines = src.split("\n");
  const nonEmpty = lines.filter((l) => l.trim().length > 0);
  const lineCount = nonEmpty.length;
  const hasRedirect = /^\s*import.*redirect.*from.*next|redirect\(/.test(src);
  const redirectOnly = hasRedirect && lineCount <= 8 && !src.includes("return (") && !src.includes("export default");
  // Meaningful UI: has export default function + JSX return
  const hasUI = /export default (function|const)/.test(src) && src.includes("return (");
  let status = "OK";
  if (redirectOnly) status = "REDIRECT_ONLY";
  else if (!hasUI) status = "NO_UI";
  return { route, exists: true, lineCount, redirectOnly, hasUI, status };
});

const missing = results.filter((r) => !r.exists);
const redirectOnly = results.filter((r) => r.redirectOnly);
const noUI = results.filter((r) => r.exists && !r.redirectOnly && !r.hasUI);
const valid = results.filter((r) => r.hasUI);

console.log(`\nRestored Route Quality Report`);
console.log(`Total bypass routes checked: ${results.length}`);
console.log(`  Valid (has UI):             ${valid.length}`);
console.log(`  Missing page file:          ${missing.length}`);
console.log(`  Redirect-only:              ${redirectOnly.length}`);
console.log(`  No UI detected:             ${noUI.length}`);

if (missing.length) {
  console.log(`\nMISSING PAGE FILES:`);
  missing.forEach((r) => console.log(`  ${r.route}`));
}
if (redirectOnly.length) {
  console.log(`\nREDIRECT-ONLY PAGES (should not be in bypass):`);
  redirectOnly.forEach((r) => console.log(`  ${r.route}  (${r.lineCount} lines)`));
}
if (noUI.length) {
  console.log(`\nNO UI DETECTED (might be placeholder):`);
  noUI.forEach((r) => console.log(`  ${r.route}  (${r.lineCount} lines)`));
}

// Write reports
const md = [
  "# Restored Route Quality Report",
  "",
  `| Metric | Count |`,
  `|--------|-------|`,
  `| Total bypass routes | ${results.length} |`,
  `| Valid (has UI) | ${valid.length} |`,
  `| Missing page file | ${missing.length} |`,
  `| Redirect-only | ${redirectOnly.length} |`,
  `| No UI detected | ${noUI.length} |`,
  "",
  "## Detail",
  "",
  "| Route | Exists | Lines | Redirect-Only | Has UI | Status |",
  "|-------|--------|-------|--------------|--------|--------|",
  ...results.map((r) => `| \`${r.route}\` | ${r.exists} | ${r.lineCount} | ${r.redirectOnly} | ${r.hasUI} | ${r.status} |`),
].join("\n");

const docsDir = path.join(__dirname, "..", "docs");
fs.writeFileSync(path.join(docsDir, "RESTORED_ROUTE_QUALITY_REPORT.md"), md);
fs.writeFileSync(path.join(docsDir, "RESTORED_ROUTE_QUALITY_REPORT.json"), JSON.stringify({ summary: { total: results.length, valid: valid.length, missing: missing.length, redirectOnly: redirectOnly.length, noUI: noUI.length }, results }, null, 2));
console.log(`\nWrote docs/RESTORED_ROUTE_QUALITY_REPORT.md`);
console.log(`Wrote docs/RESTORED_ROUTE_QUALITY_REPORT.json`);
