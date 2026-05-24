#!/usr/bin/env node
/**
 * Strict PDF verification: all 13 PDFs exist, meet minimum size thresholds.
 * Outputs JSON and MD reports to docs/manuals/
 */
const fs = require("fs");
const path = require("path");

const MANUALS_DIR = path.resolve(__dirname, "../docs/manuals");
const REPORT_JSON = path.join(MANUALS_DIR, "STRICT_MANUAL_PDF_VERIFICATION.json");
const REPORT_MD = path.join(MANUALS_DIR, "STRICT_MANUAL_PDF_VERIFICATION.md");

const EXPECTED_PDFS = [
  { slug: "manufacturing",       file: "FMCG-ERP-Manufacturing-Manual-v2-Post-Recovery.pdf",          minMB: 10 },
  { slug: "supply-chain",        file: "FMCG-ERP-Supply-Chain-Manual-v2-Post-Recovery.pdf",           minMB: 8 },
  { slug: "sales-distribution",  file: "FMCG-ERP-Sales-Distribution-Manual-v2-Post-Recovery.pdf",    minMB: 5 },
  { slug: "commercial",          file: "FMCG-ERP-Commercial-CRM-Marketing-Manual-v2-Post-Recovery.pdf", minMB: 5 },
  { slug: "finance-payroll",     file: "FMCG-ERP-Finance-Payroll-Manual-v2-Post-Recovery.pdf",       minMB: 7 },
  { slug: "hr",                  file: "FMCG-ERP-HR-Manual-v2-Post-Recovery.pdf",                    minMB: 4 },
  { slug: "logistics",           file: "FMCG-ERP-Logistics-Manual-v2-Post-Recovery.pdf",             minMB: 1 },
  { slug: "maintenance",         file: "FMCG-ERP-Maintenance-Utilities-Manual-v2-Post-Recovery.pdf", minMB: 4 },
  { slug: "documents",           file: "FMCG-ERP-Documents-Communication-Manual-v2-Post-Recovery.pdf", minMB: 2 },
  { slug: "admin",               file: "FMCG-ERP-Administration-Manual-v2-Post-Recovery.pdf",        minMB: 4 },
  { slug: "intelligence",        file: "FMCG-ERP-Intelligence-Analytics-AI-Manual-v2-Post-Recovery.pdf", minMB: 2 },
  { slug: "kenya-go-live",       file: "Kenya-Go-Live-ERP-Training-Manual-v2-Post-Recovery.pdf",     minMB: 5 },
  { slug: "full-reference",      file: "FMCG-ERP-Full-Reference-Manual-v2-Post-Recovery.pdf",        minMB: 10 },
];

const results = [];
let allPass = true;

for (const { slug, file, minMB } of EXPECTED_PDFS) {
  const pdfPath = path.join(MANUALS_DIR, slug, file);
  const exists = fs.existsSync(pdfPath);
  const sizeMB = exists ? Math.round(fs.statSync(pdfPath).size / 1024 / 1024 * 100) / 100 : 0;
  const pass = exists && sizeMB >= minMB;
  if (!pass) allPass = false;
  results.push({ slug, file, pdfPath, exists, sizeMB, minMB, pass });
}

const report = { generatedAt: new Date().toISOString(), pass: allPass, pdfs: results };
fs.writeFileSync(REPORT_JSON, JSON.stringify(report, null, 2));

let md = `# Strict Manual PDF Verification\n\nGenerated: ${report.generatedAt}\n\n`;
md += `## Result: ${allPass ? "✅ ALL PASS" : "❌ FAILURES"}\n\n`;
md += `| Manual | File | Size MB | Min MB | Pass |\n|--------|------|---------|--------|------|\n`;
for (const r of results) {
  md += `| ${r.slug} | ${r.file} | ${r.sizeMB} | ${r.minMB} | ${r.pass ? "✅" : "❌"} |\n`;
}
fs.writeFileSync(REPORT_MD, md);

console.log(JSON.stringify({ pass: allPass, pdfs: results.map(r => ({ slug: r.slug, sizeMB: r.sizeMB, pass: r.pass })) }, null, 2));
if (!allPass) process.exit(1);
