/**
 * FMCG ERP Commercial Module Manual — PDF Generator
 * Covers: CRM · Marketing · POS
 *
 * Uses Playwright Chromium (frontend/node_modules) + marked to produce:
 *   docs/user-manual/pdf-output/FMCG-ERP-Commercial-Manual.pdf
 *
 * Run from repo root:
 *   node docs/user-manual/module-manuals/commercial/pdf-export/generate-commercial-pdf.mjs
 *
 * Requirements:
 *   - Node.js 18+
 *   - frontend/node_modules/playwright installed  (cd frontend && npm install)
 *   - frontend/node_modules/marked installed      (cd frontend && npm install)
 *   - All commercial screenshots captured
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

const MANUALS_ROOT    = path.join(REPO_ROOT, "docs", "user-manual", "module-manuals");
const SCREENSHOTS_DIR = path.join(REPO_ROOT, "docs", "user-manual", "screenshots", "captured");
const OUTPUT_DIR      = path.join(REPO_ROOT, "docs", "user-manual", "pdf-output");
const OUTPUT_FILE     = path.join(OUTPUT_DIR, "FMCG-ERP-Commercial-Manual.pdf");

// ── Chapter order (module → file) ─────────────────────────────────────────

const SECTIONS = [
  {
    module: "crm",
    title: "CRM — Customer Relationship Management",
    chapters: [
      "00-overview.md",
      "01-crm-dashboard.md",
      "02-pipeline.md",
      "03-leads.md",
      "04-opportunities.md",
      "05-activities.md",
      "06-forecast-territory.md",
      "07-stages-win-loss.md",
      "08-loyalty.md",
      "09-nps-surveys.md",
    ],
  },
  {
    module: "marketing",
    title: "Marketing",
    chapters: [
      "00-overview.md",
      "01-campaigns.md",
      "02-promotions.md",
      "03-tpm-trade-spend.md",
      "04-ads-social.md",
      "05-segments-influencers.md",
      "06-ecommerce-brand.md",
      "07-visits-intel-analytics.md",
    ],
  },
  {
    module: "pos",
    title: "POS — Point of Sale",
    chapters: [
      "00-overview.md",
      "01-pos-terminal.md",
      "02-sales-sessions.md",
    ],
  },
];

// ── Required screenshots ───────────────────────────────────────────────────

const REQUIRED_SCREENSHOTS = [
  // CRM
  "module-ui/crm/crm/overview-tab.png",
  "module-ui/crm/crm/pipeline-tab.png",
  "module-ui/crm/crm/leads-tab.png",
  "module-ui/crm/crm/opportunities-tab.png",
  "module-ui/crm/crm/activities-tab.png",
  "module-ui/crm/crm/forecast-tab.png",
  "module-ui/crm/crm/territory-tab.png",
  "module-ui/crm/crm/stages-tab.png",
  "module-ui/crm/crm/win-loss-tab.png",
  "module-ui/crm/crm/loyalty-tab.png",
  "module-ui/crm/crm/nps-tab.png",
  "module-ui/crm/crm/surveys-tab.png",
  "module-ui/crm/leads/new-lead-form.png",
  "module-ui/crm/leads/leads-dropdowns.png",
  "module-ui/crm/leads/new-lead-source-dropdown.png",
  "module-ui/crm/opportunities/new-opportunity-form.png",
  "module-ui/crm/opportunities/opportunities-dropdowns.png",
  "module-ui/crm/loyalty/enroll-form.png",
  "module-ui/crm/nps/log-response-form.png",
  // Marketing
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
  // POS
  "module-ui/pos/pos/terminal-tab.png",
  "module-ui/pos/pos/sales-tab.png",
  "module-ui/pos/pos/sessions-tab.png",
  "module-ui/pos/terminal/open-session-modal.png",
  "module-ui/pos/terminal/payment-modal.png",
  "module-ui/pos/terminal/close-session-modal.png",
];

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
  console.log(`Screenshots: ${files.size} PNGs found`);
  return true;
}

function validateChapters() {
  const missing = [];
  for (const section of SECTIONS) {
    const dir = path.join(MANUALS_ROOT, section.module);
    for (const chapter of section.chapters) {
      const p = path.join(dir, chapter);
      if (!fs.existsSync(p)) missing.push(`${section.module}/${chapter}`);
    }
  }
  if (missing.length > 0) {
    console.error("ERROR: Missing chapter files:", missing);
    return false;
  }
  const total = SECTIONS.reduce((s, sec) => s + sec.chapters.length, 0);
  console.log(`Chapters: ${total} files verified across ${SECTIONS.length} modules`);
  return true;
}

function validateRequiredScreenshots(capturedFiles) {
  const missing = REQUIRED_SCREENSHOTS.filter((f) => !capturedFiles.has(f));
  if (missing.length > 0) {
    console.error("ERROR: Required screenshots missing — PDF is NOT COMPLETE:");
    for (const f of missing) console.error(`  MISSING: ${f}`);
    return false;
  }
  console.log(`Required screenshots: ${REQUIRED_SCREENSHOTS.length}/${REQUIRED_SCREENSHOTS.length} present`);
  return true;
}

function validateImageRefs() {
  if (!fs.existsSync(SCREENSHOTS_DIR)) {
    console.log("Image ref check skipped — no screenshots directory");
    return true;
  }
  const capturedFiles = getCapturedFileSet();
  let totalRefs = 0;
  let missingRefs = 0;
  for (const section of SECTIONS) {
    const dir = path.join(MANUALS_ROOT, section.module);
    for (const chapter of section.chapters) {
      const content = fs.readFileSync(path.join(dir, chapter), "utf-8");
      const refs = [...content.matchAll(/!\[.*?\]\([^)]*?screenshots\/captured\/([^)]+\.png)\)/g)];
      for (const ref of refs) {
        totalRefs++;
        if (!capturedFiles.has(ref[1])) {
          console.warn(`  WARNING: Image not found: ${ref[1]} (in ${section.module}/${chapter})`);
          missingRefs++;
        }
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
  const dateStr = new Date().toLocaleDateString("en-GB", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const totalChapters = SECTIONS.reduce((s, sec) => s + sec.chapters.length, 0);

  const cover = `
<div class="cover-page">
  <div class="cover-content">
    <h1 class="cover-title">FMCG ERP</h1>
    <h2 class="cover-subtitle">Commercial Module Manual</h2>
    <div class="cover-meta">
      <p><strong>Version:</strong> 1.0</p>
      <p><strong>Date:</strong> ${dateStr}</p>
      <p><strong>Scope:</strong> CRM · Marketing · Point of Sale</p>
      <p><strong>Chapters:</strong> ${totalChapters} across ${SECTIONS.length} modules</p>
    </div>
    <div class="cover-disclaimer">
      <p>Field names and workflows reflect the actual ERP codebase. Screens may change as the ERP evolves.</p>
      <p><strong>Confidential — Internal Use Only</strong></p>
    </div>
  </div>
</div>
`;

  const sectionDividers = {
    crm: `<div class="module-break">
      <div class="module-header">
        <div class="module-label">PART I</div>
        <div class="module-title">CRM — Customer Relationship Management</div>
        <div class="module-sub">Pipeline · Leads · Opportunities · Activities · Forecast · Territory · Loyalty · NPS · Surveys</div>
      </div>
    </div>`,
    marketing: `<div class="module-break">
      <div class="module-header">
        <div class="module-label">PART II</div>
        <div class="module-title">Marketing</div>
        <div class="module-sub">Campaigns · Promotions · TPM · Trade Spend · Ads · Social Media · Segments · Influencers · E-Commerce · Brand Spend · Visits · Market Intel · Analytics</div>
      </div>
    </div>`,
    pos: `<div class="module-break">
      <div class="module-header">
        <div class="module-label">PART III</div>
        <div class="module-title">POS — Point of Sale</div>
        <div class="module-sub">Terminal · Sales History · Sessions</div>
      </div>
    </div>`,
  };

  let chapterIndex = 0;
  const sectionHtmlParts = [];

  for (const section of SECTIONS) {
    const dir = path.join(MANUALS_ROOT, section.module);
    sectionHtmlParts.push(sectionDividers[section.module] || "");

    for (const chapter of section.chapters) {
      const mdPath = path.join(dir, chapter);
      const raw = fs.readFileSync(mdPath, "utf-8");
      const fixed = fixImagePaths(raw);
      const html = marked.parse(fixed);
      const pageBreak = chapterIndex > 0 ? '<div class="chapter-break"></div>' : "";
      sectionHtmlParts.push(`${pageBreak}<div class="chapter" id="chapter-${chapterIndex}">${html}</div>`);
      chapterIndex++;
    }
  }

  const css = `
body { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 11pt; line-height: 1.6; color: #1a1a1a; margin: 0; padding: 0; }
h1 { font-size: 18pt; font-weight: 700; color: #1e3a5f; margin-top: 24pt; border-bottom: 2px solid #1e3a5f; padding-bottom: 4pt; }
h2 { font-size: 14pt; font-weight: 600; color: #2563eb; margin-top: 18pt; }
h3 { font-size: 12pt; font-weight: 600; color: #1e40af; margin-top: 14pt; }
table { border-collapse: collapse; width: 100%; margin: 12pt 0; font-size: 9.5pt; }
th { background: #dbeafe; font-weight: 600; text-align: left; padding: 6pt 8pt; border: 1px solid #93c5fd; }
td { padding: 5pt 8pt; border: 1px solid #e2e8f0; vertical-align: top; }
tr:nth-child(even) { background: #f0f7ff; }
code { font-family: 'Courier New', monospace; font-size: 9pt; background: #f0f4ff; padding: 1pt 3pt; border-radius: 2pt; }
pre { background: #f0f4ff; padding: 10pt; border-radius: 4pt; overflow-x: auto; font-size: 9pt; }
blockquote { border-left: 4px solid #93c5fd; margin: 8pt 0; padding: 4pt 12pt; background: #f8faff; color: #4a5568; }
img { max-width: 100%; border: 1px solid #e2e8f0; border-radius: 4pt; margin: 8pt 0; }
.cover-page { display: flex; align-items: center; justify-content: center; min-height: 100vh; background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 50%, #7c3aed 100%); color: white; text-align: center; }
.cover-content { max-width: 80%; }
.cover-title { font-size: 36pt; font-weight: 800; margin-bottom: 8pt; }
.cover-subtitle { font-size: 22pt; font-weight: 300; margin-bottom: 24pt; opacity: 0.9; }
.cover-meta { font-size: 11pt; line-height: 2; }
.cover-disclaimer { margin-top: 32pt; font-size: 9pt; opacity: 0.7; }
.module-break { page-break-before: always; display: flex; align-items: center; justify-content: center; min-height: 60vh; }
.module-header { text-align: center; max-width: 70%; }
.module-label { font-size: 11pt; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 3px; margin-bottom: 12pt; }
.module-title { font-size: 28pt; font-weight: 800; color: #1e3a5f; margin-bottom: 12pt; border: none; padding: 0; }
.module-sub { font-size: 11pt; color: #4b5563; line-height: 1.8; }
.chapter-break { page-break-before: always; }
@page { margin: 20mm 18mm; }
`;

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FMCG ERP Commercial Module Manual</title>
<style>
${css}
</style>
</head>
<body>
${cover}
${sectionHtmlParts.join("\n")}
</body>
</html>`;
}

// ── PDF generation ─────────────────────────────────────────────────────────

async function generatePdf() {
  console.log("\n=== FMCG ERP Commercial Module Manual — PDF Generator ===");
  console.log("Covers: CRM · Marketing · POS\n");

  validateScreenshots();
  if (!validateChapters()) process.exit(1);
  const capturedFiles = getCapturedFileSet();
  if (!validateRequiredScreenshots(capturedFiles)) process.exit(1);
  validateImageRefs();

  console.log("\nBuilding HTML...");
  const html = buildCombinedHtml();

  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  const tmpHtml = path.join(OUTPUT_DIR, "_temp_commercial_manual.html");
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
    headerTemplate: `<div style="font-size:8pt;color:#999;width:100%;text-align:center;padding-top:4mm;">FMCG ERP — Commercial Module Manual (CRM · Marketing · POS) — Confidential</div>`,
    footerTemplate: `<div style="font-size:8pt;color:#999;width:100%;text-align:center;padding-bottom:4mm;">Page <span class="pageNumber"></span> of <span class="totalPages"></span></div>`,
  });

  await browser.close();

  fs.unlinkSync(tmpHtml);
  console.log("Temp HTML cleaned up.");

  const stat = fs.statSync(OUTPUT_FILE);
  const sizeMB = (stat.size / 1024 / 1024).toFixed(1);
  const totalChapters = SECTIONS.reduce((s, sec) => s + sec.chapters.length, 0);
  console.log(`\n✓ PDF generated: ${OUTPUT_FILE}`);
  console.log(`  Size: ${sizeMB} MB`);
  console.log(`  Modules: ${SECTIONS.length} (CRM · Marketing · POS)`);
  console.log(`  Chapters: ${totalChapters}`);
  console.log(`  Images loaded: ${imgLoaded} / ${imgLoaded + imgFailed}`);
  console.log("\nDone.\n");
}

generatePdf().catch((e) => {
  console.error("PDF generation failed:", e);
  process.exit(1);
});
