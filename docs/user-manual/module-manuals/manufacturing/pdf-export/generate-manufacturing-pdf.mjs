/**
 * FMCG ERP Manufacturing Module Manual — PDF Generator
 *
 * Uses Playwright Chromium (frontend/node_modules) + marked to produce:
 *   docs/user-manual/pdf-output/FMCG-ERP-Manufacturing-Manual.pdf
 *
 * Run from repo root:
 *   node docs/user-manual/module-manuals/manufacturing/pdf-export/generate-manufacturing-pdf.mjs
 *
 * Requirements:
 *   - Node.js 18+
 *   - frontend/node_modules/playwright installed  (cd frontend && npm install)
 *   - frontend/node_modules/marked installed      (cd frontend && npm install)
 *   - Shared screenshots at docs/user-manual/screenshots/captured/ (optional — skips if absent)
 */

import { createRequire } from "module";
import { fileURLToPath } from "url";
import path from "path";
import fs from "fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..", "..", "..", "..", "..");
const FE_MODULES = path.join(REPO_ROOT, "frontend", "node_modules");

const require = createRequire(import.meta.url);
let chromium, marked;
try {
  ({ chromium } = require(path.join(FE_MODULES, "playwright")));
  ({ marked } = require(path.join(FE_MODULES, "marked")));
} catch (e) {
  console.error("Failed to load playwright or marked from frontend/node_modules:", e.message);
  console.error("Run: cd frontend && npm install");
  process.exit(1);
}

// ── Paths ──────────────────────────────────────────────────────────────────

const MANUAL_DIR    = path.join(REPO_ROOT, "docs", "user-manual", "module-manuals", "manufacturing");
const SCREENSHOTS_DIR = path.join(REPO_ROOT, "docs", "user-manual", "screenshots", "captured");
const CSS_FILE      = path.join(__dirname, "manufacturing-style.css");
const OUTPUT_DIR    = path.join(REPO_ROOT, "docs", "user-manual", "pdf-output");
const OUTPUT_FILE   = path.join(OUTPUT_DIR, "FMCG-ERP-Manufacturing-Manual.pdf");

// ── Chapter order ──────────────────────────────────────────────────────────

const CHAPTERS = [
  "00-overview.md",
  "01-recipes.md",
  "02-recipes-import.md",
  "03-bom-formula.md",
  "04-production-plans.md",
  "05-work-orders.md",
  "06-batch-lots.md",
  "07-quality-control.md",
  "08-shop-floor.md",
  "09-planning-scheduling.md",
  "10-npd.md",
  "11-oee-reporting.md",
  "12-compliance.md",
];

// ── Required screenshots — loaded from manifest ────────────────────────────

const MANUFACTURING_MANIFEST_FILE = path.join(REPO_ROOT, "docs", "user-manual", "screenshots", "manufacturing-ui-screenshot-manifest.json");
const MANUFACTURING_INDEX_FILE    = path.join(REPO_ROOT, "docs", "user-manual", "screenshots", "manufacturing-ui-screenshots-index.json");

function loadManufacturingManifest() {
  if (!fs.existsSync(MANUFACTURING_MANIFEST_FILE)) return [];
  return JSON.parse(fs.readFileSync(MANUFACTURING_MANIFEST_FILE, "utf-8"));
}

function loadManufacturingIndex() {
  if (!fs.existsSync(MANUFACTURING_INDEX_FILE)) return {};
  try {
    const arr = JSON.parse(fs.readFileSync(MANUFACTURING_INDEX_FILE, "utf-8"));
    return Object.fromEntries(arr.map((e) => [e.id, e]));
  } catch { return {}; }
}

// Legacy hardcoded list (keeps old screenshots valid while new ones are captured)
const LEGACY_REQUIRED_SCREENSHOTS = [
  "tabs/recipes-list.png",
  "tabs/bom-list.png",
  "tabs/production-plans.png",
  "tabs/production-orders.png",
  "tabs/production-execution.png",
  "tabs/production-material-flow.png",
  "tabs/production-costing.png",
  "tabs/production-batch-lots.png",
  "tabs/production-oee.png",
  "tabs/quality-inspections.png",
  "tabs/quality-qms.png",
  "tabs/quality-allergen.png",
  "tabs/shop-floor-overview.png",
  "tabs/shop-floor-terminal.png",
  "tabs/shop-floor-supervisor.png",
  "tabs/planning-dashboard.png",
  "tabs/planning-capacity.png",
  "tabs/planning-mrp.png",
  "tabs/planning-mps.png",
  "tabs/npd-new-products.png",
  "tabs/compliance-gs1.png",
  "actions/recipes-new-recipe-modal.png",
  "actions/recipes-import-bom-modal.png",
  "actions/quality-new-inspection-modal.png",
];

const REQUIRED_SCREENSHOTS = LEGACY_REQUIRED_SCREENSHOTS;

// ── Validation ─────────────────────────────────────────────────────────────

function getCapturedFileSet() {
  if (!fs.existsSync(SCREENSHOTS_DIR)) return new Set();
  const files = new Set();
  function scan(dir, prefix) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
      if (entry.isDirectory()) {
        scan(path.join(dir, entry.name), rel);
      } else if (entry.name.endsWith(".png")) {
        files.add(rel);
      }
    }
  }
  scan(SCREENSHOTS_DIR, "");
  return files;
}

function validateScreenshots() {
  if (!fs.existsSync(SCREENSHOTS_DIR)) {
    console.warn(`WARNING: Screenshots folder missing: ${SCREENSHOTS_DIR}`);
    return true;
  }
  const files = getCapturedFileSet();
  console.log(`Screenshots: ${files.size} PNGs found (including subdirs)`);
  return true;
}

function validateChapters() {
  const missing = CHAPTERS.filter((c) => !fs.existsSync(path.join(MANUAL_DIR, c)));
  if (missing.length > 0) {
    console.error("ERROR: Missing chapter files:", missing);
    return false;
  }
  console.log(`Chapters: ${CHAPTERS.length} files verified`);
  return true;
}

function validateRequiredScreenshots(capturedFiles) {
  const missing = REQUIRED_SCREENSHOTS.filter((f) => !capturedFiles.has(f));
  if (missing.length > 0) {
    console.error("ERROR: Required screenshots missing — PDF is NOT COMPLETE:");
    for (const f of missing) console.error(`  MISSING: ${f}`);
    return false;
  }
  console.log(`Required screenshots (legacy): ${REQUIRED_SCREENSHOTS.length}/${REQUIRED_SCREENSHOTS.length} present`);
  return true;
}

function validateManifestCoverage(capturedFiles) {
  const manifest = loadManufacturingManifest();
  const index    = loadManufacturingIndex();

  const total     = manifest.length;
  const required  = manifest.filter((i) => i.requiredForPdf && i.output !== null && i.status !== "captured_as_part_of_parent_screen");
  const captured  = manifest.filter((i) => index[i.id]?.status === "captured");
  const parentCap = manifest.filter((i) => i.status === "captured_as_part_of_parent_screen");
  const failed    = manifest.filter((i) => index[i.id]?.status === "failed");
  const pending   = manifest.filter((i) => !index[i.id] && i.output !== null && i.status !== "captured_as_part_of_parent_screen");

  const requiredCaptured = required.filter((i) => index[i.id]?.status === "captured");
  const requiredMissing  = required.filter((i) => index[i.id]?.status !== "captured");

  console.log(`\n── Manufacturing Screenshot Manifest ─────────────────────────`);
  console.log(`  Total manifest items:          ${total}`);
  console.log(`  Required for PDF:              ${required.length}`);
  console.log(`  Captured:                      ${captured.length}`);
  console.log(`  Captured as part of parent:    ${parentCap.length}`);
  console.log(`  Failed:                        ${failed.length}`);
  console.log(`  Pending (not yet run):         ${pending.length}`);
  console.log(`  Required + captured:           ${requiredCaptured.length}/${required.length}`);

  if (requiredMissing.length > 0) {
    console.warn(`\n  MISSING REQUIRED screenshots (${requiredMissing.length}):`);
    for (const i of requiredMissing) {
      const entry = index[i.id];
      const reason = entry ? `status=${entry.status}: ${entry.reason}` : "not yet run";
      console.warn(`    MISSING [${i.id}]: ${reason}`);
    }
  }
  console.log(`──────────────────────────────────────────────────────────────`);
  return requiredMissing.length === 0;
}

function validateImageRefs() {
  if (!fs.existsSync(SCREENSHOTS_DIR)) {
    console.log("Image ref check skipped — no screenshots directory");
    return true;
  }
  const capturedFiles = getCapturedFileSet();
  let totalRefs = 0;
  let actionRefs = 0;
  let missingRefs = 0;
  for (const chapter of CHAPTERS) {
    const content = fs.readFileSync(path.join(MANUAL_DIR, chapter), "utf-8");
    const refs = [...content.matchAll(/!\[.*?\]\(.*?screenshots\/captured\/([^)]+\.png)\)/g)];
    for (const ref of refs) {
      totalRefs++;
      if (ref[1].startsWith("actions/") || ref[1].startsWith("tabs/") || ref[1].startsWith("module-ui/")) actionRefs++;
      if (!capturedFiles.has(ref[1])) {
        console.warn(`  WARNING: Image not found: ${ref[1]} (in ${chapter})`);
        missingRefs++;
      }
    }
  }
  if (totalRefs === 0) {
    console.log("Image refs: 0 image references in chapters");
  } else {
    console.log(`Image refs: ${totalRefs} total (${actionRefs} action/modal), ${totalRefs - missingRefs} valid, ${missingRefs} missing`);
  }
  if (missingRefs > 0) {
    console.warn(`WARNING: ${missingRefs} image references are broken — they will be skipped in the PDF`);
  }
  return missingRefs === 0;
}

// ── Markdown processing ─────────────────────────────────────────────────────

function fixImagePaths(mdContent) {
  if (!fs.existsSync(SCREENSHOTS_DIR)) return mdContent;
  return mdContent.replace(
    /!\[([^\]]*)\]\([^)]*?screenshots\/captured\/([^)]+\.png)\)/g,
    (match, alt, filename) => {
      const fullPath = path.join(SCREENSHOTS_DIR, filename);
      if (!fs.existsSync(fullPath)) {
        return `<!-- image missing: ${filename} -->`;
      }
      const uri = `file:///${fullPath.replace(/\\/g, "/")}`;
      return `![${alt}](${uri})`;
    }
  );
}

function buildCombinedHtml() {
  const css = fs.existsSync(CSS_FILE) ? fs.readFileSync(CSS_FILE, "utf-8") : defaultCss();

  const dateStr = new Date().toLocaleDateString("en-GB", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const cover = `
<div class="cover-page">
  <div class="cover-content">
    <h1 class="cover-title">FMCG ERP</h1>
    <h2 class="cover-subtitle">Manufacturing Module Manual</h2>
    <div class="cover-meta">
      <p><strong>Version:</strong> 1.0</p>
      <p><strong>Date:</strong> ${dateStr}</p>
      <p><strong>Scope:</strong> Recipes · BOM · Production · Planning · Shop Floor · NPD · Quality · Compliance</p>
      <p><strong>Chapters:</strong> ${CHAPTERS.length}</p>
    </div>
    <div class="cover-disclaimer">
      <p>Field names and workflows reflect the actual ERP codebase. Screens may change as the ERP evolves.</p>
      <p><strong>Confidential — Internal Use Only</strong></p>
    </div>
  </div>
</div>
`;

  const chapterHtmlParts = CHAPTERS.map((chapter, i) => {
    const mdPath = path.join(MANUAL_DIR, chapter);
    const raw = fs.readFileSync(mdPath, "utf-8");
    const fixed = fixImagePaths(raw);
    const html = marked.parse(fixed);
    const pageBreak = i > 0 ? '<div class="chapter-break"></div>' : "";
    return `${pageBreak}<div class="chapter" id="chapter-${i}">${html}</div>`;
  });

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FMCG ERP Manufacturing Module Manual</title>
<style>
${css}
</style>
</head>
<body>
${cover}
${chapterHtmlParts.join("\n")}
</body>
</html>`;
}

function defaultCss() {
  return `
body { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 11pt; line-height: 1.6; color: #1a1a1a; margin: 0; padding: 0; }
h1 { font-size: 18pt; font-weight: 700; color: #1e3a5f; margin-top: 24pt; border-bottom: 2px solid #1e3a5f; padding-bottom: 4pt; }
h2 { font-size: 14pt; font-weight: 600; color: #2c5282; margin-top: 18pt; }
h3 { font-size: 12pt; font-weight: 600; color: #2d3748; margin-top: 14pt; }
table { border-collapse: collapse; width: 100%; margin: 12pt 0; font-size: 9.5pt; }
th { background: #e2e8f0; font-weight: 600; text-align: left; padding: 6pt 8pt; border: 1px solid #cbd5e0; }
td { padding: 5pt 8pt; border: 1px solid #e2e8f0; vertical-align: top; }
tr:nth-child(even) { background: #f7fafc; }
code { font-family: 'Courier New', monospace; font-size: 9pt; background: #f0f4f8; padding: 1pt 3pt; border-radius: 2pt; }
pre { background: #f0f4f8; padding: 10pt; border-radius: 4pt; overflow-x: auto; font-size: 9pt; }
img { max-width: 100%; border: 1px solid #e2e8f0; border-radius: 4pt; margin: 8pt 0; }
.cover-page { display: flex; align-items: center; justify-content: center; min-height: 100vh; background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%); color: white; text-align: center; }
.cover-title { font-size: 36pt; font-weight: 800; margin-bottom: 8pt; }
.cover-subtitle { font-size: 22pt; font-weight: 300; margin-bottom: 24pt; opacity: 0.9; }
.cover-meta { font-size: 11pt; line-height: 2; }
.cover-disclaimer { margin-top: 32pt; font-size: 9pt; opacity: 0.7; }
.chapter-break { page-break-before: always; }
@page { margin: 20mm 18mm; }
`;
}

// ── PDF generation ─────────────────────────────────────────────────────────

async function generatePdf() {
  console.log("\n=== FMCG ERP Manufacturing Module Manual — PDF Generator ===\n");

  validateScreenshots();
  if (!validateChapters()) process.exit(1);
  const capturedFiles = getCapturedFileSet();
  if (!validateRequiredScreenshots(capturedFiles)) process.exit(1);
  validateManifestCoverage(capturedFiles);
  validateImageRefs();

  console.log("\nBuilding HTML...");
  const html = buildCombinedHtml();

  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  const tmpHtml = path.join(OUTPUT_DIR, "_temp_manufacturing_manual.html");
  fs.writeFileSync(tmpHtml, html, "utf-8");
  console.log(`Temp HTML written: ${tmpHtml}`);

  console.log("\nLaunching Chromium...");
  const browser = await chromium.launch();
  const page = await browser.newPage();

  await page.goto(`file:///${tmpHtml.replace(/\\/g, "/")}`, { waitUntil: "networkidle" });

  let imgLoaded = 0;
  let imgFailed = 0;
  const imgHandles = await page.$$("img");
  for (const img of imgHandles) {
    const ok = await img.evaluate((el) => el.complete && el.naturalWidth > 0);
    if (ok) imgLoaded++;
    else imgFailed++;
  }
  console.log(`Images: ${imgLoaded} loaded, ${imgFailed} failed`);

  console.log("\nGenerating PDF...");
  await page.pdf({
    path: OUTPUT_FILE,
    format: "A4",
    printBackground: true,
    margin: { top: "20mm", bottom: "20mm", left: "18mm", right: "18mm" },
    displayHeaderFooter: true,
    headerTemplate: `<div style="font-size:8pt;color:#999;width:100%;text-align:center;padding-top:4mm;">FMCG ERP — Manufacturing Module Manual — Confidential</div>`,
    footerTemplate: `<div style="font-size:8pt;color:#999;width:100%;text-align:center;padding-bottom:4mm;">Page <span class="pageNumber"></span> of <span class="totalPages"></span></div>`,
  });

  await browser.close();

  fs.unlinkSync(tmpHtml);
  console.log("Temp HTML cleaned up.");

  const stat = fs.statSync(OUTPUT_FILE);
  const sizeMB = (stat.size / 1024 / 1024).toFixed(1);
  console.log(`\n✓ PDF generated: ${OUTPUT_FILE}`);
  console.log(`  Size: ${sizeMB} MB`);
  console.log(`  Chapters: ${CHAPTERS.length}`);
  console.log(`  Images loaded: ${imgLoaded} / ${imgLoaded + imgFailed}`);
  console.log("\nDone.\n");
}

generatePdf().catch((e) => {
  console.error("PDF generation failed:", e);
  process.exit(1);
});
