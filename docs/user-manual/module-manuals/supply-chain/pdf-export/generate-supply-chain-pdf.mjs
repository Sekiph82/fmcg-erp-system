/**
 * FMCG ERP Supply Chain Module Manual — PDF Generator
 *
 * Uses Playwright Chromium (frontend/node_modules) + marked to produce:
 *   docs/user-manual/pdf-output/FMCG-ERP-Supply-Chain-Manual.pdf
 *
 * Run from repo root:
 *   node docs/user-manual/module-manuals/supply-chain/pdf-export/generate-supply-chain-pdf.mjs
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

const MANUAL_DIR      = path.join(REPO_ROOT, "docs", "user-manual", "module-manuals", "supply-chain");
const SCREENSHOTS_DIR = path.join(REPO_ROOT, "docs", "user-manual", "screenshots", "captured");
const CSS_FILE        = path.join(__dirname, "supply-chain-style.css");
const OUTPUT_DIR      = path.join(REPO_ROOT, "docs", "user-manual", "pdf-output");
const OUTPUT_FILE     = path.join(OUTPUT_DIR, "FMCG-ERP-Supply-Chain-Manual.pdf");

// ── Chapter order ──────────────────────────────────────────────────────────

const CHAPTERS = [
  "00-overview.md",
  "01-purchase-requisitions.md",
  "02-purchase-orders.md",
  "03-rfq.md",
  "04-deliveries.md",
  "05-suppliers.md",
  "06-blanket-reorder.md",
  "07-inventory-stock.md",
  "08-movements.md",
  "09-warehouses.md",
  "10-wms.md",
  "11-logistics.md",
];

// ── Validation ─────────────────────────────────────────────────────────────

function validateScreenshots() {
  if (!fs.existsSync(SCREENSHOTS_DIR)) {
    console.warn(`WARNING: Screenshots folder missing: ${SCREENSHOTS_DIR}`);
    console.warn("Images in chapters will be skipped.");
    return true;
  }
  const pngs = fs.readdirSync(SCREENSHOTS_DIR).filter((f) => f.endsWith(".png"));
  console.log(`Screenshots: ${pngs.length} PNGs found`);
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

function validateImageRefs() {
  if (!fs.existsSync(SCREENSHOTS_DIR)) {
    console.log("Image ref check skipped — no screenshots directory");
    return true;
  }
  const capturedFiles = new Set(fs.readdirSync(SCREENSHOTS_DIR));
  let totalRefs = 0;
  let missingRefs = 0;
  for (const chapter of CHAPTERS) {
    const content = fs.readFileSync(path.join(MANUAL_DIR, chapter), "utf-8");
    const refs = [...content.matchAll(/!\[.*?\]\(.*?screenshots\/captured\/([^)]+\.png)\)/g)];
    for (const ref of refs) {
      totalRefs++;
      if (!capturedFiles.has(ref[1])) {
        console.warn(`  WARNING: Image not found: ${ref[1]} (in ${chapter})`);
        missingRefs++;
      }
    }
  }
  if (totalRefs === 0) {
    console.log("Image refs: 0 image references in chapters");
  } else {
    console.log(`Image refs: ${totalRefs} total, ${totalRefs - missingRefs} valid, ${missingRefs} missing`);
  }
  if (missingRefs > 0) {
    console.warn(`WARNING: ${missingRefs} image references are broken — they will be skipped in the PDF`);
  }
  return true;
}

// ── Markdown processing ─────────────────────────────────────────────────────

function fixImagePaths(mdContent) {
  if (!fs.existsSync(SCREENSHOTS_DIR)) return mdContent;
  return mdContent.replace(
    /!\[([^\]]*)\]\(.*?screenshots\/captured\/([^)]+\.png)\)/g,
    (match, alt, filename) => {
      const absPath = path.join(SCREENSHOTS_DIR, filename).replace(/\\/g, "/");
      const uri = `file:///${absPath}`;
      if (!fs.existsSync(path.join(SCREENSHOTS_DIR, filename))) {
        return `<!-- image missing: ${filename} -->`;
      }
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
    <h2 class="cover-subtitle">Supply Chain Module Manual</h2>
    <div class="cover-meta">
      <p><strong>Version:</strong> 1.0</p>
      <p><strong>Date:</strong> ${dateStr}</p>
      <p><strong>Scope:</strong> Procurement · Inventory · Warehouses · WMS · Logistics</p>
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
<title>FMCG ERP Supply Chain Module Manual</title>
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
h1 { font-size: 18pt; font-weight: 700; color: #1a4731; margin-top: 24pt; border-bottom: 2px solid #1a4731; padding-bottom: 4pt; }
h2 { font-size: 14pt; font-weight: 600; color: #276749; margin-top: 18pt; }
h3 { font-size: 12pt; font-weight: 600; color: #2d3748; margin-top: 14pt; }
table { border-collapse: collapse; width: 100%; margin: 12pt 0; font-size: 9.5pt; }
th { background: #e6f4ea; font-weight: 600; text-align: left; padding: 6pt 8pt; border: 1px solid #b7dfc6; }
td { padding: 5pt 8pt; border: 1px solid #e2e8f0; vertical-align: top; }
tr:nth-child(even) { background: #f7faf8; }
code { font-family: 'Courier New', monospace; font-size: 9pt; background: #f0f4f0; padding: 1pt 3pt; border-radius: 2pt; }
pre { background: #f0f4f0; padding: 10pt; border-radius: 4pt; overflow-x: auto; font-size: 9pt; }
img { max-width: 100%; border: 1px solid #e2e8f0; border-radius: 4pt; margin: 8pt 0; }
.cover-page { display: flex; align-items: center; justify-content: center; min-height: 100vh; background: linear-gradient(135deg, #1a4731 0%, #276749 100%); color: white; text-align: center; }
.cover-content { max-width: 80%; }
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
  console.log("\n=== FMCG ERP Supply Chain Module Manual — PDF Generator ===\n");

  validateScreenshots();
  if (!validateChapters()) process.exit(1);
  validateImageRefs();

  console.log("\nBuilding HTML...");
  const html = buildCombinedHtml();

  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  const tmpHtml = path.join(OUTPUT_DIR, "_temp_supply_chain_manual.html");
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
    headerTemplate: `<div style="font-size:8pt;color:#999;width:100%;text-align:center;padding-top:4mm;">FMCG ERP — Supply Chain Module Manual — Confidential</div>`,
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
