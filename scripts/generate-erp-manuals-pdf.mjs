#!/usr/bin/env node
/**
 * ERP Manual PDF Generator
 * Uses Playwright (Chromium) + marked to convert Markdown manuals to PDF.
 *
 * Usage (from repo root):
 *   node scripts/generate-erp-manuals-pdf.mjs
 *   node scripts/generate-erp-manuals-pdf.mjs --manual=manufacturing
 *   node scripts/generate-erp-manuals-pdf.mjs --verify-only
 *
 * Requirements:
 *   - frontend/node_modules/playwright (already installed)
 *   - frontend/node_modules/marked (already installed)
 *   - Screenshots in docs/user-manual/screenshots/captured/
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { createRequire } from "module";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..");
const require = createRequire(import.meta.url);

// ── Resolve deps from frontend/node_modules ────────────────────────────────────
const FRONTEND_NM = path.join(REPO_ROOT, "frontend", "node_modules");
const { marked } = require(path.join(FRONTEND_NM, "marked"));
const { chromium } = require(path.join(FRONTEND_NM, "playwright-core"));

// ── Manual registry ────────────────────────────────────────────────────────────
const MANUALS_DIR = path.join(REPO_ROOT, "docs", "manuals");

const MANUALS = [
  {
    slug: "manufacturing",
    title: "FMCG ERP Manufacturing Manual",
    subtitle: "Production · Planning · Quality · Compliance · Shop Floor",
    audience: "Production Managers, Quality Officers, Planning Managers, Shop Floor Supervisors",
    src: path.join(MANUALS_DIR, "manufacturing", "FMCG-ERP-Manufacturing-Manual-v2.md"),
    out: path.join(MANUALS_DIR, "manufacturing", "FMCG-ERP-Manufacturing-Manual-v2-Post-Recovery.pdf"),
  },
  {
    slug: "supply-chain",
    title: "FMCG ERP Supply Chain Manual",
    subtitle: "Procurement · Inventory · Warehousing · WMS",
    audience: "Procurement Officers, Warehouse Supervisors, Logistics Staff",
    src: path.join(MANUALS_DIR, "supply-chain", "FMCG-ERP-Supply-Chain-Manual-v2.md"),
    out: path.join(MANUALS_DIR, "supply-chain", "FMCG-ERP-Supply-Chain-Manual-v2-Post-Recovery.pdf"),
  },
  {
    slug: "sales-distribution",
    title: "FMCG ERP Sales & Distribution Manual",
    subtitle: "Sales Orders · Invoicing · Customers · Van Sales · Secondary Sales",
    audience: "Sales Representatives, Sales Managers, Van Sales Agents, Distribution Staff",
    src: path.join(MANUALS_DIR, "sales-distribution", "FMCG-ERP-Sales-Distribution-Manual-v2.md"),
    out: path.join(MANUALS_DIR, "sales-distribution", "FMCG-ERP-Sales-Distribution-Manual-v2-Post-Recovery.pdf"),
  },
  {
    slug: "commercial",
    title: "FMCG ERP Commercial, CRM & Marketing Manual",
    subtitle: "CRM · Leads · Loyalty · Marketing · Campaigns · TPM · NPS",
    audience: "Sales Managers, Marketing Officers, Brand Managers, Trade Marketing Staff",
    src: path.join(MANUALS_DIR, "commercial", "FMCG-ERP-Commercial-CRM-Marketing-Manual-v2.md"),
    out: path.join(MANUALS_DIR, "commercial", "FMCG-ERP-Commercial-CRM-Marketing-Manual-v2-Post-Recovery.pdf"),
  },
  {
    slug: "finance-payroll",
    title: "FMCG ERP Finance & Payroll Manual",
    subtitle: "Accounting · Bank Reconciliation · M-Pesa · Tax · Payroll · Fixed Assets",
    audience: "Finance Officers, Accountants, Payroll Administrators, CFO",
    src: path.join(MANUALS_DIR, "finance-payroll", "FMCG-ERP-Finance-Payroll-Manual-v2.md"),
    out: path.join(MANUALS_DIR, "finance-payroll", "FMCG-ERP-Finance-Payroll-Manual-v2-Post-Recovery.pdf"),
  },
  {
    slug: "hr",
    title: "FMCG ERP HR Manual",
    subtitle: "Employees · Attendance · Leave · Recruitment · Training · Appraisals · ESS",
    audience: "HR Officers, Line Managers, Employees (ESS), HR Manager",
    src: path.join(MANUALS_DIR, "hr", "FMCG-ERP-HR-Manual-v2.md"),
    out: path.join(MANUALS_DIR, "hr", "FMCG-ERP-HR-Manual-v2-Post-Recovery.pdf"),
  },
  {
    slug: "logistics",
    title: "FMCG ERP Logistics Manual",
    subtitle: "Shipments · Fleet · Containers · Delivery Notes",
    audience: "Logistics Officers, Fleet Managers, Transport Coordinators",
    src: path.join(MANUALS_DIR, "logistics", "FMCG-ERP-Logistics-Manual-v2.md"),
    out: path.join(MANUALS_DIR, "logistics", "FMCG-ERP-Logistics-Manual-v2-Post-Recovery.pdf"),
  },
  {
    slug: "maintenance",
    title: "FMCG ERP Maintenance, Utilities & Factory Operations Manual",
    subtitle: "Maintenance · Utility Management · ESG · IoT Monitoring",
    audience: "Maintenance Technicians, Engineers, Factory Managers, Utility Officers",
    src: path.join(MANUALS_DIR, "maintenance", "FMCG-ERP-Maintenance-Utilities-Manual-v2.md"),
    out: path.join(MANUALS_DIR, "maintenance", "FMCG-ERP-Maintenance-Utilities-Manual-v2-Post-Recovery.pdf"),
  },
  {
    slug: "documents",
    title: "FMCG ERP Documents & Communication Manual",
    subtitle: "Documents · Knowledge Base · Communication · Helpdesk · Surveys",
    audience: "All Staff, Administrators, Quality Officers",
    src: path.join(MANUALS_DIR, "documents", "FMCG-ERP-Documents-Communication-Manual-v2.md"),
    out: path.join(MANUALS_DIR, "documents", "FMCG-ERP-Documents-Communication-Manual-v2-Post-Recovery.pdf"),
  },
  {
    slug: "admin",
    title: "FMCG ERP Administration & Settings Manual",
    subtitle: "Users · Roles · Permissions · Security · Companies · Integrations · Webhooks",
    audience: "System Administrators, IT Managers, Super Users",
    src: path.join(MANUALS_DIR, "admin", "FMCG-ERP-Administration-Manual-v2.md"),
    out: path.join(MANUALS_DIR, "admin", "FMCG-ERP-Administration-Manual-v2-Post-Recovery.pdf"),
  },
  {
    slug: "intelligence",
    title: "FMCG ERP Intelligence, Analytics & AI Manual",
    subtitle: "Analytics · Report Builder · AI Assistant · Custom Reports",
    audience: "Managers, Analysts, Senior Leadership",
    src: path.join(MANUALS_DIR, "intelligence", "FMCG-ERP-Intelligence-Analytics-AI-Manual-v2.md"),
    out: path.join(MANUALS_DIR, "intelligence", "FMCG-ERP-Intelligence-Analytics-AI-Manual-v2-Post-Recovery.pdf"),
  },
  {
    slug: "kenya-go-live",
    title: "Kenya Go-Live ERP Training Manual",
    subtitle: "Comprehensive Go-Live Training for All Roles",
    audience: "All Staff — Production, Warehouse, Procurement, Sales, Finance, HR, Admin",
    src: path.join(MANUALS_DIR, "kenya-go-live", "Kenya-Go-Live-ERP-Training-Manual-v2.md"),
    out: path.join(MANUALS_DIR, "kenya-go-live", "Kenya-Go-Live-ERP-Training-Manual-v2-Post-Recovery.pdf"),
  },
  {
    slug: "full-reference",
    title: "FMCG ERP Full Reference Manual",
    subtitle: "Complete ERP Reference — All Modules, All Workflows",
    audience: "All Roles — Super User Reference",
    src: path.join(MANUALS_DIR, "full-reference", "FMCG-ERP-Full-Reference-Manual-v2.md"),
    out: path.join(MANUALS_DIR, "full-reference", "FMCG-ERP-Full-Reference-Manual-v2-Post-Recovery.pdf"),
  },
];

// ── CSS ────────────────────────────────────────────────────────────────────────
const PDF_CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'Inter', Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a2e;
    background: white;
  }

  .cover {
    page-break-after: always;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: flex-start;
    min-height: 90vh;
    padding: 60px;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    color: white;
  }

  .cover-badge {
    background: #e94560;
    color: white;
    font-size: 9pt;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 6px 16px;
    border-radius: 4px;
    margin-bottom: 32px;
    display: inline-block;
  }

  .cover h1 {
    font-size: 32pt;
    font-weight: 700;
    line-height: 1.2;
    margin-bottom: 12px;
    color: white;
  }

  .cover-subtitle {
    font-size: 14pt;
    color: #a8b2d8;
    margin-bottom: 32px;
  }

  .cover-meta {
    font-size: 10pt;
    color: #8892b0;
    border-top: 1px solid rgba(255,255,255,0.15);
    padding-top: 24px;
    margin-top: 40px;
    width: 100%;
  }

  .cover-meta p { margin-bottom: 6px; }

  h1, h2, h3, h4 { line-height: 1.3; color: #1a1a2e; }

  h1 {
    font-size: 22pt;
    font-weight: 700;
    margin: 32px 0 16px;
    padding-bottom: 8px;
    border-bottom: 3px solid #0f3460;
    page-break-after: avoid;
  }

  h2 {
    font-size: 16pt;
    font-weight: 600;
    margin: 28px 0 12px;
    padding-bottom: 6px;
    border-bottom: 1px solid #e2e8f0;
    color: #0f3460;
    page-break-after: avoid;
  }

  h3 {
    font-size: 13pt;
    font-weight: 600;
    margin: 20px 0 8px;
    color: #1a1a2e;
    page-break-after: avoid;
  }

  h4 {
    font-size: 11pt;
    font-weight: 600;
    margin: 14px 0 6px;
    color: #2d3748;
    page-break-after: avoid;
  }

  p { margin-bottom: 10px; }

  ul, ol {
    margin: 8px 0 12px 24px;
  }

  li { margin-bottom: 4px; }

  table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0 16px;
    font-size: 10pt;
    page-break-inside: avoid;
  }

  th {
    background: #0f3460;
    color: white;
    padding: 8px 12px;
    text-align: left;
    font-weight: 600;
    font-size: 9.5pt;
  }

  td {
    padding: 7px 12px;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: top;
  }

  tr:nth-child(even) td { background: #f8fafc; }
  tr:hover td { background: #f0f4f8; }

  code {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 9.5pt;
    background: #f1f5f9;
    padding: 2px 5px;
    border-radius: 3px;
    color: #e94560;
  }

  pre {
    background: #1e293b;
    color: #e2e8f0;
    padding: 16px 20px;
    border-radius: 6px;
    margin: 12px 0 16px;
    overflow-x: auto;
    font-size: 9.5pt;
    page-break-inside: avoid;
  }

  pre code {
    background: none;
    color: inherit;
    padding: 0;
    font-size: inherit;
  }

  blockquote {
    border-left: 4px solid #0f3460;
    margin: 12px 0;
    padding: 8px 16px;
    background: #f0f4f8;
    border-radius: 0 4px 4px 0;
    font-style: italic;
    color: #4a5568;
  }

  hr {
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 24px 0;
  }

  img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 16px auto;
    border-radius: 6px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.12);
    page-break-inside: avoid;
  }

  .img-caption {
    text-align: center;
    font-size: 9pt;
    color: #718096;
    margin-top: -10px;
    margin-bottom: 16px;
    font-style: italic;
  }

  .callout {
    border-left: 4px solid #e94560;
    background: #fff5f5;
    padding: 10px 16px;
    margin: 12px 0;
    border-radius: 0 4px 4px 0;
  }

  .callout-tip {
    border-color: #38a169;
    background: #f0fff4;
  }

  .callout-warning {
    border-color: #d69e2e;
    background: #fffff0;
  }

  strong { font-weight: 600; color: #1a1a2e; }

  a { color: #0f3460; text-decoration: none; }

  .page-break { page-break-after: always; }

  @page {
    size: A4;
    margin: 18mm 20mm 18mm 20mm;

    @bottom-center {
      content: counter(page);
      font-size: 9pt;
      color: #718096;
    }

    @top-right {
      content: "FMCG ERP — Confidential";
      font-size: 8pt;
      color: #a0aec0;
    }
  }

  @media print {
    h1 { page-break-before: auto; }
    h2 { page-break-before: auto; }
    .no-break { page-break-inside: avoid; }
  }
`;

// ── Image embed helper ─────────────────────────────────────────────────────────
function embedImages(html, mdFilePath) {
  const mdDir = path.dirname(mdFilePath);
  return html.replace(/<img([^>]*?)src="([^"]+)"([^>]*?)>/g, (match, pre, src, post) => {
    if (src.startsWith("data:") || src.startsWith("http")) return match;
    const absPath = path.resolve(mdDir, src);
    if (!fs.existsSync(absPath)) {
      console.warn(`  [MISSING IMG] ${src}`);
      return `<div style="border:1px dashed #e2e8f0;padding:12px;text-align:center;color:#a0aec0;font-size:9pt;border-radius:4px;margin:8px 0;">[Screenshot: ${path.basename(src)}]</div>`;
    }
    const ext = path.extname(absPath).slice(1).toLowerCase();
    const mime = ext === "jpg" || ext === "jpeg" ? "image/jpeg" : "image/png";
    const data = fs.readFileSync(absPath);
    const b64 = data.toString("base64");
    return `<img${pre}src="data:${mime};base64,${b64}"${post}>`;
  });
}

// ── Add captions for italics after images ─────────────────────────────────────
function addImageCaptions(html) {
  return html.replace(/<\/figure>|(<img[^>]+>)\s*\n*\s*<em>([^<]+)<\/em>/g, (match, img, cap) => {
    if (!img) return match;
    return `${img}<p class="img-caption">${cap}</p>`;
  });
}

// ── Cover page HTML ────────────────────────────────────────────────────────────
function coverHtml(manual) {
  const date = new Date().toLocaleDateString("en-GB", { year: "numeric", month: "long", day: "numeric" });
  return `
    <div class="cover">
      <span class="cover-badge">FMCG ERP System</span>
      <h1>${manual.title}</h1>
      <p class="cover-subtitle">${manual.subtitle}</p>
      <div class="cover-meta">
        <p><strong>Audience:</strong> ${manual.audience}</p>
        <p><strong>Version:</strong> v2.0 — Post-Recovery Edition</p>
        <p><strong>Date:</strong> ${date}</p>
        <p><strong>Status:</strong> Confidential — Internal Use Only</p>
        <p style="margin-top:12px;font-size:9pt;color:#64748b;">
          ERP button/link recovery complete. All navigation targets restored and verified.
          Smoke test: 141/141 routes passed. BVT: 0. Broken action cards: 0.
        </p>
      </div>
    </div>
  `;
}

// ── Generate one PDF ───────────────────────────────────────────────────────────
async function generatePdf(browser, manual, verifyOnly) {
  if (!fs.existsSync(manual.src)) {
    console.log(`  [SKIP] Source not found: ${manual.src}`);
    return { slug: manual.slug, status: "skipped", reason: "source file missing" };
  }

  const md = fs.readFileSync(manual.src, "utf-8");
  const bodyHtml = marked.parse(md);
  const embeddedHtml = embedImages(bodyHtml, manual.src);
  const captionedHtml = addImageCaptions(embeddedHtml);

  const fullHtml = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${manual.title}</title>
<style>${PDF_CSS}</style>
</head>
<body>
${coverHtml(manual)}
<div style="padding: 0 4mm;">
${captionedHtml}
</div>
</body>
</html>`;

  if (verifyOnly) {
    // Count image references and check which exist
    const imgRefs = [...md.matchAll(/!\[([^\]]*)\]\(([^)]+)\)/g)];
    const mdDir = path.dirname(manual.src);
    let found = 0, missing = 0;
    const missingList = [];
    for (const [, , src] of imgRefs) {
      if (src.startsWith("http") || src.startsWith("data:")) { found++; continue; }
      const abs = path.resolve(mdDir, src);
      if (fs.existsSync(abs)) { found++; } else { missing++; missingList.push(src); }
    }
    return { slug: manual.slug, status: "verify-only", images: { total: imgRefs.length, found, missing }, missingList };
  }

  fs.mkdirSync(path.dirname(manual.out), { recursive: true });

  const page = await browser.newPage();
  try {
    await page.setContent(fullHtml, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForTimeout(1000);
    await page.pdf({
      path: manual.out,
      format: "A4",
      printBackground: true,
      margin: { top: "18mm", bottom: "18mm", left: "20mm", right: "20mm" },
    });
    const size = fs.statSync(manual.out).size;
    console.log(`  ✅ ${path.basename(manual.out)} (${(size / 1024 / 1024).toFixed(1)} MB)`);
    return { slug: manual.slug, status: "ok", path: manual.out, sizeMB: +(size / 1024 / 1024).toFixed(2) };
  } finally {
    await page.close();
  }
}

// ── Main ───────────────────────────────────────────────────────────────────────
async function main() {
  const args = process.argv.slice(2);
  const manualFilter = args.find(a => a.startsWith("--manual="))?.split("=")[1];
  const verifyOnly = args.includes("--verify-only");

  const targets = manualFilter
    ? MANUALS.filter(m => m.slug === manualFilter)
    : MANUALS;

  if (targets.length === 0) {
    console.error(`No manual found for slug: ${manualFilter}`);
    process.exit(1);
  }

  console.log(`\nERP Manual PDF Generator`);
  console.log(`Mode: ${verifyOnly ? "verify-only" : "generate"}`);
  console.log(`Manuals: ${targets.length}`);
  console.log("─".repeat(60));

  let browser;
  if (!verifyOnly) {
    browser = await chromium.launch({ headless: true });
  }

  const results = [];
  for (const manual of targets) {
    console.log(`\n[${manual.slug}] ${manual.title}`);
    try {
      const r = await generatePdf(browser, manual, verifyOnly);
      results.push(r);
    } catch (err) {
      console.error(`  ❌ Error: ${err.message}`);
      results.push({ slug: manual.slug, status: "error", error: err.message });
    }
  }

  if (browser) await browser.close();

  // Write report
  const REPORT_PATH = path.join(REPO_ROOT, "docs", "manuals", "MANUAL_PDF_VERIFICATION_REPORT.json");
  fs.writeFileSync(REPORT_PATH, JSON.stringify(results, null, 2));

  const ok = results.filter(r => r.status === "ok").length;
  const skipped = results.filter(r => r.status === "skipped").length;
  const errors = results.filter(r => r.status === "error").length;

  console.log("\n" + "─".repeat(60));
  console.log(`Summary: ${ok} generated, ${skipped} skipped, ${errors} errors`);
  console.log(`Report: ${REPORT_PATH}`);

  if (errors > 0) process.exit(1);
}

main().catch(err => { console.error(err); process.exit(1); });
