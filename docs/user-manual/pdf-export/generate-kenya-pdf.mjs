/**
 * Kenya Go-Live ERP Training Manual — PDF Generator
 *
 * Uses Playwright Chromium (already installed in frontend/node_modules) + marked
 * to produce docs/user-manual/pdf-output/Kenya-Go-Live-ERP-Training-Manual.pdf
 *
 * Run from repo root:
 *   node docs/user-manual/pdf-export/generate-kenya-pdf.mjs
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

// Load playwright and marked from frontend/node_modules
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

const KENYA_DIR = path.join(REPO_ROOT, "docs", "user-manual", "kenya-go-live");
const SCREENSHOTS_DIR = path.join(REPO_ROOT, "docs", "user-manual", "screenshots", "captured");
const CSS_FILE = path.join(__dirname, "pdf-style.css");
const OUTPUT_DIR = path.join(REPO_ROOT, "docs", "user-manual", "pdf-output");
const OUTPUT_FILE = path.join(OUTPUT_DIR, "Kenya-Go-Live-ERP-Training-Manual.pdf");

// ── Chapter order ──────────────────────────────────────────────────────────

const CHAPTERS = [
  "00_GO_LIVE_TRAINING_INDEX.md",
  "01_ADMIN_USER_MANUAL.md",
  "02_PRODUCTION_USER_MANUAL.md",
  "03_WAREHOUSE_INVENTORY_USER_MANUAL.md",
  "04_PROCUREMENT_USER_MANUAL.md",
  "05_QUALITY_CONTROL_USER_MANUAL.md",
  "06_SALES_LOGISTICS_USER_MANUAL.md",
  "07_HR_USER_MANUAL.md",
  "08_MANAGER_DASHBOARD_USER_MANUAL.md",
  "09_COMMON_PROBLEMS_AND_FAQ.md",
];

// ── Validation ─────────────────────────────────────────────────────────────

function validateScreenshots() {
  if (!fs.existsSync(SCREENSHOTS_DIR)) {
    console.error(`ERROR: Screenshots folder missing: ${SCREENSHOTS_DIR}`);
    console.error("Regenerate screenshots: cd frontend && E2E_SKIP_WEBSERVER=1 npm run test:manual-screenshots");
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
  const missing = CHAPTERS.filter((c) => !fs.existsSync(path.join(KENYA_DIR, c)));
  if (missing.length > 0) {
    console.error("ERROR: Missing chapter files:", missing);
    return false;
  }
  console.log(`Chapters: ${CHAPTERS.length} files verified`);
  return true;
}

// ── Markdown processing ─────────────────────────────────────────────────────

function fixImagePaths(mdContent) {
  // Convert ../screenshots/captured/xxx.png → file:/// absolute path
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

  const cover = `
<div class="cover-page">
  <div class="cover-content">
    <h1 class="cover-title">FMCG ERP</h1>
    <h2 class="cover-subtitle">Kenya Go-Live Training Manual</h2>
    <div class="cover-meta">
      <p><strong>Version:</strong> 1.0</p>
      <p><strong>Date:</strong> ${new Date().toLocaleDateString("en-KE", { year: "numeric", month: "long", day: "numeric" })}</p>
      <p><strong>Prepared for:</strong> Kenya Go-Live Training</p>
      <p><strong>Environment:</strong> FMCG ERP Production System</p>
    </div>
    <div class="cover-disclaimer">
      <p>Screenshots captured from FMCG ERP development environment.</p>
      <p>Screens may change as the ERP evolves. Always follow company SOPs and manager instructions.</p>
      <p><strong>Confidential — Internal Use Only</strong></p>
    </div>
  </div>
</div>
`;

  const chapterHtmlParts = CHAPTERS.map((chapter, i) => {
    const mdPath = path.join(KENYA_DIR, chapter);
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
<title>Kenya Go-Live ERP Training Manual</title>
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
  console.log("\n=== Kenya Go-Live ERP Training Manual — PDF Generator ===\n");

  if (!validateScreenshots()) process.exit(1);
  if (!validateChapters()) process.exit(1);

  console.log("\nBuilding HTML...");
  const html = buildCombinedHtml();

  // Write temp HTML for debugging (removed after PDF generation)
  const tmpHtml = path.join(OUTPUT_DIR, "_temp_kenya_manual.html");
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  fs.writeFileSync(tmpHtml, html, "utf-8");
  console.log(`Temp HTML: ${tmpHtml}`);

  console.log("\nLaunching Playwright Chromium...");
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Load via file:// so relative resources resolve
  await page.goto(`file:///${tmpHtml.replace(/\\/g, "/")}`, {
    waitUntil: "networkidle",
    timeout: 60_000,
  });

  // Wait for all images to load
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

  console.log(`\nGenerating PDF: ${OUTPUT_FILE}`);
  await page.pdf({
    path: OUTPUT_FILE,
    format: "A4",
    printBackground: true,
    margin: { top: "20mm", bottom: "20mm", left: "20mm", right: "20mm" },
    displayHeaderFooter: true,
    headerTemplate: `<div style="font-size:9px;color:#666;width:100%;text-align:center;padding-top:5px;">
      FMCG ERP — Kenya Go-Live Training Manual — Confidential
    </div>`,
    footerTemplate: `<div style="font-size:9px;color:#666;width:100%;text-align:center;padding-bottom:5px;">
      Page <span class="pageNumber"></span> of <span class="totalPages"></span>
    </div>`,
  });

  await browser.close();

  // Remove temp HTML
  fs.unlinkSync(tmpHtml);

  const stat = fs.statSync(OUTPUT_FILE);
  const sizeMb = (stat.size / 1024 / 1024).toFixed(1);
  console.log(`\nSuccess! PDF generated: ${OUTPUT_FILE}`);
  console.log(`PDF size: ${sizeMb} MB`);
  console.log(`Images in PDF: ${imgStats.loaded} loaded, ${imgStats.failed} failed`);

  if (imgStats.failed > 0) {
    console.warn(`\nWARNING: ${imgStats.failed} images failed to load. Check screenshot paths.`);
  }
}

generatePdf().catch((err) => {
  console.error("\nPDF generation failed:", err.message);
  process.exit(1);
});
