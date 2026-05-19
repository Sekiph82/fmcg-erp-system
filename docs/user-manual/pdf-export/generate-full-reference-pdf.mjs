/**
 * FMCG ERP Full Reference Manual — PDF Generator
 *
 * Uses Playwright Chromium (already installed in frontend/node_modules) + marked
 * to produce docs/user-manual/pdf-output/FMCG-ERP-Full-Reference-Manual.pdf
 *
 * Run from repo root:
 *   node docs/user-manual/pdf-export/generate-full-reference-pdf.mjs
 *
 * Requirements:
 *   - Node.js 18+
 *   - frontend/node_modules/playwright installed  (npm install in frontend/)
 *   - frontend/node_modules/marked installed      (npm install in frontend/)
 *   - docs/user-manual/screenshots/captured/ exists with 140 PNGs
 */

import { createRequire } from "module";
import { fileURLToPath } from "url";
import path from "path";
import fs from "fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");
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

const FULL_REF_DIR = path.join(REPO_ROOT, "docs", "user-manual", "full-reference");
const SCREENSHOTS_DIR = path.join(REPO_ROOT, "docs", "user-manual", "screenshots", "captured");
const CSS_FILE = path.join(__dirname, "full-reference-style.css");
const OUTPUT_DIR = path.join(REPO_ROOT, "docs", "user-manual", "pdf-output");
const OUTPUT_FILE = path.join(OUTPUT_DIR, "FMCG-ERP-Full-Reference-Manual.pdf");

// ── Chapter order ──────────────────────────────────────────────────────────

const CHAPTERS = [
  "00_FULL_ERP_MANUAL_INDEX.md",
  "01_DASHBOARD_AND_NAVIGATION.md",
  "02_MASTER_DATA.md",
  "03_PROCUREMENT.md",
  "04_INVENTORY_AND_WAREHOUSE.md",
  "05_PRODUCTION.md",
  "06_QUALITY_AND_COMPLIANCE.md",
  "07_SALES_AND_DISTRIBUTION.md",
  "08_FINANCE.md",
  "09_HR_AND_PAYROLL.md",
  "10_ADMIN_AND_SECURITY.md",
  "11_AI_AND_AUTOMATION.md",
  "12_REPORTS_AND_EXPORTS.md",
  "13_STANDALONE_OPERATIONAL_PAGES.md",
  "14_OLD_ROUTE_COMPATIBILITY.md",
];

// ── Validation ─────────────────────────────────────────────────────────────

function validateScreenshots() {
  if (!fs.existsSync(SCREENSHOTS_DIR)) {
    console.error(`ERROR: Screenshots folder missing: ${SCREENSHOTS_DIR}`);
    console.error("Regenerate: cd frontend && E2E_SKIP_WEBSERVER=1 npm run test:manual-screenshots");
    return false;
  }
  const pngs = fs.readdirSync(SCREENSHOTS_DIR).filter((f) => f.endsWith(".png"));
  console.log(`Screenshots: ${pngs.length} PNGs found`);
  if (pngs.length < 100) {
    console.warn(`WARNING: Only ${pngs.length} screenshots — expected ~140`);
  }
  return true;
}

function validateChapters() {
  const missing = CHAPTERS.filter((c) => !fs.existsSync(path.join(FULL_REF_DIR, c)));
  if (missing.length > 0) {
    console.error("ERROR: Missing chapter files:", missing);
    return false;
  }
  console.log(`Chapters: ${CHAPTERS.length} files verified`);
  return true;
}

function validateImageRefs() {
  const capturedFiles = new Set(fs.readdirSync(SCREENSHOTS_DIR));
  let totalRefs = 0;
  let missingRefs = 0;
  for (const chapter of CHAPTERS) {
    const content = fs.readFileSync(path.join(FULL_REF_DIR, chapter), "utf-8");
    const refs = [...content.matchAll(/!\[.*?\]\(\.\.\/screenshots\/captured\/([^)]+\.png)\)/g)];
    for (const ref of refs) {
      totalRefs++;
      if (!capturedFiles.has(ref[1])) {
        console.warn(`  WARNING: Image not found: ${ref[1]} (in ${chapter})`);
        missingRefs++;
      }
    }
  }
  console.log(`Image refs: ${totalRefs} total, ${totalRefs - missingRefs} valid, ${missingRefs} missing`);
  if (missingRefs > 0) {
    console.error(`ERROR: ${missingRefs} image references are broken. Regenerate screenshots first.`);
    return false;
  }
  return true;
}

// ── Markdown processing ─────────────────────────────────────────────────────

function fixImagePaths(mdContent) {
  return mdContent.replace(
    /!\[([^\]]*)\]\(\.\.\/screenshots\/captured\/([^)]+\.png)\)/g,
    (match, alt, filename) => {
      const absPath = path.join(SCREENSHOTS_DIR, filename).replace(/\\/g, "/");
      const uri = `file:///${absPath}`;
      if (!fs.existsSync(path.join(SCREENSHOTS_DIR, filename))) {
        console.warn(`  WARNING: Image not found: ${filename}`);
      }
      return `![${alt}](${uri})`;
    }
  );
}

function buildCombinedHtml() {
  const css = fs.existsSync(CSS_FILE) ? fs.readFileSync(CSS_FILE, "utf-8") : "";

  const dateStr = new Date().toLocaleDateString("en-GB", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const cover = `
<div class="cover-page">
  <div class="cover-content">
    <h1 class="cover-title">FMCG ERP</h1>
    <h2 class="cover-subtitle">Full Reference Manual</h2>
    <div class="cover-meta">
      <p><strong>Version:</strong> 1.0</p>
      <p><strong>Date:</strong> ${dateStr}</p>
      <p><strong>Scope:</strong> All Modules — Complete Reference</p>
      <p><strong>Chapters:</strong> ${CHAPTERS.length}</p>
    </div>
    <div class="cover-disclaimer">
      <p>Screens may change as the ERP evolves. Always follow company SOPs and manager instructions.</p>
      <p><strong>Confidential — Internal Use Only</strong></p>
    </div>
  </div>
</div>
`;

  const chapterHtmlParts = CHAPTERS.map((chapter, i) => {
    const mdPath = path.join(FULL_REF_DIR, chapter);
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
<title>FMCG ERP Full Reference Manual</title>
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

// ── PDF generation ─────────────────────────────────────────────────────────

async function generatePdf() {
  console.log("\n=== FMCG ERP Full Reference Manual — PDF Generator ===\n");

  if (!validateScreenshots()) process.exit(1);
  if (!validateChapters()) process.exit(1);
  if (!validateImageRefs()) process.exit(1);

  console.log("\nBuilding HTML...");
  const html = buildCombinedHtml();

  const tmpHtml = path.join(OUTPUT_DIR, "_temp_full_reference_manual.html");
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  fs.writeFileSync(tmpHtml, html, "utf-8");
  console.log(`Temp HTML: ${tmpHtml}`);

  console.log("\nLaunching Playwright Chromium...");
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto(`file:///${tmpHtml.replace(/\\/g, "/")}`, {
    waitUntil: "networkidle",
    timeout: 120_000,
  });

  await page.evaluate(() => {
    return Promise.all(
      Array.from(document.images)
        .filter((img) => !img.complete)
        .map((img) => new Promise((resolve) => { img.onload = img.onerror = resolve; }))
    );
  });

  const imgStats = await page.evaluate(() => {
    const imgs = Array.from(document.images);
    return {
      total: imgs.length,
      loaded: imgs.filter((i) => i.complete && i.naturalWidth > 0).length,
      failed: imgs.filter((i) => i.complete && i.naturalWidth === 0).length,
    };
  });
  console.log(`Images: ${imgStats.loaded}/${imgStats.total} loaded, ${imgStats.failed} failed`);

  if (imgStats.failed > 0) {
    console.error(`ERROR: ${imgStats.failed} images failed to load in browser. PDF will be incomplete.`);
    await browser.close();
    fs.unlinkSync(tmpHtml);
    process.exit(1);
  }

  console.log(`\nGenerating PDF: ${OUTPUT_FILE}`);
  await page.pdf({
    path: OUTPUT_FILE,
    format: "A4",
    printBackground: true,
    margin: { top: "20mm", bottom: "20mm", left: "20mm", right: "20mm" },
    displayHeaderFooter: true,
    headerTemplate: `<div style="font-size:9px;color:#666;width:100%;text-align:center;padding-top:5px;">
      FMCG ERP — Full Reference Manual — Confidential
    </div>`,
    footerTemplate: `<div style="font-size:9px;color:#666;width:100%;text-align:center;padding-bottom:5px;">
      Page <span class="pageNumber"></span> of <span class="totalPages"></span>
    </div>`,
  });

  await browser.close();
  fs.unlinkSync(tmpHtml);

  const stat = fs.statSync(OUTPUT_FILE);
  const sizeMb = (stat.size / 1024 / 1024).toFixed(1);
  console.log(`\nSuccess! PDF generated: ${OUTPUT_FILE}`);
  console.log(`PDF size: ${sizeMb} MB`);
  console.log(`Images in PDF: ${imgStats.loaded} loaded, ${imgStats.failed} failed`);
}

generatePdf().catch((err) => {
  console.error("\nPDF generation failed:", err.message);
  process.exit(1);
});
