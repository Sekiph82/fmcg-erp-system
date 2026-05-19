/**
 * FMCG ERP Marketing Module Manual — PDF Generator
 *
 * Uses Playwright Chromium (frontend/node_modules) + marked to produce:
 *   docs/user-manual/pdf-output/FMCG-ERP-Marketing-Manual.pdf
 *
 * Run from repo root:
 *   node docs/user-manual/module-manuals/marketing/pdf-export/generate-marketing-pdf.mjs
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
  process.exit(1);
}

const MANUAL_DIR      = path.join(REPO_ROOT, "docs", "user-manual", "module-manuals", "marketing");
const SCREENSHOTS_DIR = path.join(REPO_ROOT, "docs", "user-manual", "screenshots", "captured");
const OUTPUT_DIR      = path.join(REPO_ROOT, "docs", "user-manual", "pdf-output");
const OUTPUT_FILE     = path.join(OUTPUT_DIR, "FMCG-ERP-Marketing-Manual.pdf");

const CHAPTERS = [
  "00-overview.md",
  "01-campaigns.md",
  "02-promotions.md",
  "03-tpm-trade-spend.md",
  "04-ads-social.md",
  "05-segments-influencers.md",
  "06-ecommerce-brand.md",
  "07-visits-intel-analytics.md",
];

const REQUIRED_SCREENSHOTS = [
  "module-ui/marketing/marketing/overview-tab.png",
  "module-ui/marketing/marketing/campaigns-tab.png",
  "module-ui/marketing/marketing/promotions-tab.png",
  "module-ui/marketing/marketing/schemes-tab.png",
  "module-ui/marketing/marketing/tpm-tab.png",
  "module-ui/marketing/marketing/trade-spend-tab.png",
  "module-ui/marketing/marketing/ads-tab.png",
  "module-ui/marketing/marketing/social-tab.png",
  "module-ui/marketing/marketing/segments-tab.png",
  "module-ui/marketing/marketing/influencers-tab.png",
  "module-ui/marketing/marketing/ecommerce-tab.png",
  "module-ui/marketing/marketing/brand-spend-tab.png",
  "module-ui/marketing/marketing/visits-tab.png",
  "module-ui/marketing/marketing/market-intel-tab.png",
  "module-ui/marketing/marketing/analytics-tab.png",
  "module-ui/marketing/campaigns/new-campaign-form.png",
  "module-ui/marketing/promotions/new-promotion-form.png",
];

function getCapturedFileSet() {
  if (!fs.existsSync(SCREENSHOTS_DIR)) return new Set();
  const files = new Set();
  function scan(dir, prefix) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
      if (entry.isDirectory()) scan(path.join(dir, entry.name), rel);
      else if (entry.name.endsWith(".png")) files.add(rel);
    }
  }
  scan(SCREENSHOTS_DIR, "");
  return files;
}

function validateChapters() {
  const missing = CHAPTERS.filter((c) => !fs.existsSync(path.join(MANUAL_DIR, c)));
  if (missing.length > 0) { console.error("ERROR: Missing chapters:", missing); return false; }
  console.log(`Chapters: ${CHAPTERS.length} verified`);
  return true;
}

function validateRequiredScreenshots(capturedFiles) {
  const missing = REQUIRED_SCREENSHOTS.filter((f) => !capturedFiles.has(f));
  if (missing.length > 0) {
    console.error("ERROR: Required screenshots missing:");
    for (const f of missing) console.error(`  MISSING: ${f}`);
    return false;
  }
  console.log(`Required screenshots: ${REQUIRED_SCREENSHOTS.length}/${REQUIRED_SCREENSHOTS.length} present`);
  return true;
}

function fixImagePaths(mdContent) {
  if (!fs.existsSync(SCREENSHOTS_DIR)) return mdContent;
  return mdContent.replace(
    /!\[([^\]]*)\]\([^)]*?screenshots\/captured\/([^)]+\.png)\)/g,
    (match, alt, filename) => {
      const fullPath = path.join(SCREENSHOTS_DIR, filename);
      if (!fs.existsSync(fullPath)) return `<!-- image missing: ${filename} -->`;
      return `![${alt}](file:///${fullPath.replace(/\\/g, "/")})`;
    }
  );
}

function buildHtml() {
  const dateStr = new Date().toLocaleDateString("en-GB", { year: "numeric", month: "long", day: "numeric" });
  const cover = `
<div class="cover-page">
  <div class="cover-content">
    <h1 class="cover-title">FMCG ERP</h1>
    <h2 class="cover-subtitle">Marketing Module Manual</h2>
    <div class="cover-meta">
      <p><strong>Version:</strong> 1.0</p>
      <p><strong>Date:</strong> ${dateStr}</p>
      <p><strong>Scope:</strong> Campaigns · Promotions · TPM · Trade Spend · Ads · Social · Segments · Influencers · E-Commerce · Brand Spend · Visits · Market Intel · Analytics</p>
      <p><strong>Chapters:</strong> ${CHAPTERS.length}</p>
    </div>
    <div class="cover-disclaimer"><p><strong>Confidential — Internal Use Only</strong></p></div>
  </div>
</div>`;

  const parts = CHAPTERS.map((c, i) => {
    const raw = fs.readFileSync(path.join(MANUAL_DIR, c), "utf-8");
    const html = marked.parse(fixImagePaths(raw));
    return `${i > 0 ? '<div class="chapter-break"></div>' : ""}<div class="chapter">${html}</div>`;
  });

  const css = `
body{font-family:'Helvetica Neue',Arial,sans-serif;font-size:11pt;line-height:1.6;color:#1a1a1a}
h1{font-size:18pt;font-weight:700;color:#1e3a5f;margin-top:24pt;border-bottom:2px solid #1e3a5f;padding-bottom:4pt}
h2{font-size:14pt;font-weight:600;color:#7c3aed;margin-top:18pt}
h3{font-size:12pt;font-weight:600;color:#5b21b6;margin-top:14pt}
table{border-collapse:collapse;width:100%;margin:12pt 0;font-size:9.5pt}
th{background:#ede9fe;font-weight:600;text-align:left;padding:6pt 8pt;border:1px solid #c4b5fd}
td{padding:5pt 8pt;border:1px solid #e2e8f0;vertical-align:top}
tr:nth-child(even){background:#f5f3ff}
code{font-family:'Courier New',monospace;font-size:9pt;background:#f5f3ff;padding:1pt 3pt;border-radius:2pt}
pre{background:#f5f3ff;padding:10pt;border-radius:4pt;font-size:9pt}
blockquote{border-left:4px solid #c4b5fd;margin:8pt 0;padding:4pt 12pt;background:#faf5ff;color:#4a5568}
img{max-width:100%;border:1px solid #e2e8f0;border-radius:4pt;margin:8pt 0}
.cover-page{display:flex;align-items:center;justify-content:center;min-height:100vh;background:linear-gradient(135deg,#4c1d95 0%,#7c3aed 100%);color:white;text-align:center}
.cover-content{max-width:80%}
.cover-title{font-size:36pt;font-weight:800;margin-bottom:8pt}
.cover-subtitle{font-size:22pt;font-weight:300;margin-bottom:24pt;opacity:.9}
.cover-meta{font-size:11pt;line-height:2}
.cover-disclaimer{margin-top:32pt;font-size:9pt;opacity:.7}
.chapter-break{page-break-before:always}
@page{margin:20mm 18mm}`;

  return `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>FMCG ERP Marketing Module Manual</title><style>${css}</style></head><body>${cover}${parts.join("\n")}</body></html>`;
}

async function generatePdf() {
  console.log("\n=== FMCG ERP Marketing Module Manual — PDF Generator ===\n");
  if (!validateChapters()) process.exit(1);
  const capturedFiles = getCapturedFileSet();
  if (!validateRequiredScreenshots(capturedFiles)) process.exit(1);

  const html = buildHtml();
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  const tmp = path.join(OUTPUT_DIR, "_temp_marketing_manual.html");
  fs.writeFileSync(tmp, html, "utf-8");

  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(`file:///${tmp.replace(/\\/g, "/")}`, { waitUntil: "networkidle" });

  let imgLoaded = 0, imgFailed = 0;
  for (const img of await page.$$("img")) {
    const ok = await img.evaluate(el => el.complete && el.naturalWidth > 0);
    if (ok) imgLoaded++; else imgFailed++;
  }
  console.log(`Images: ${imgLoaded} loaded, ${imgFailed} failed`);

  await page.pdf({
    path: OUTPUT_FILE, format: "A4", printBackground: true,
    margin: { top: "20mm", bottom: "20mm", left: "18mm", right: "18mm" },
    displayHeaderFooter: true,
    headerTemplate: `<div style="font-size:8pt;color:#999;width:100%;text-align:center;padding-top:4mm;">FMCG ERP — Marketing Module Manual — Confidential</div>`,
    footerTemplate: `<div style="font-size:8pt;color:#999;width:100%;text-align:center;padding-bottom:4mm;">Page <span class="pageNumber"></span> of <span class="totalPages"></span></div>`,
  });

  await browser.close();
  fs.unlinkSync(tmp);

  const { size } = fs.statSync(OUTPUT_FILE);
  console.log(`\n✓ PDF generated: ${OUTPUT_FILE}`);
  console.log(`  Size: ${(size / 1024 / 1024).toFixed(1)} MB`);
  console.log(`  Chapters: ${CHAPTERS.length}\n`);
}

generatePdf().catch(e => { console.error("PDF generation failed:", e); process.exit(1); });
