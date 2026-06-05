/**
 * FMCG ERP Administration Manual — PDF Generator
 *
 * Generates docs/user-manual/pdf-output/FMCG-ERP-Administration-Manual.pdf
 * from docs/manuals/admin/FMCG-ERP-Administration-Manual-v2.md (v2.1)
 *
 * Run from repo root:
 *   node docs/user-manual/pdf-export/generate-admin-pdf.mjs
 *
 * Requirements:
 *   - Node.js 18+
 *   - frontend/node_modules/playwright installed
 *   - frontend/node_modules/marked installed
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
  console.error("Failed to load playwright or marked:", e.message);
  console.error("Run: cd frontend && npm install");
  process.exit(1);
}

const SOURCE_MD = path.join(REPO_ROOT, "docs", "manuals", "admin", "FMCG-ERP-Administration-Manual-v2.md");
const SCREENSHOTS_DIR = path.join(REPO_ROOT, "docs", "user-manual", "screenshots", "captured");
const CSS_FILE = path.join(__dirname, "full-reference-style.css");
const OUTPUT_DIR = path.join(REPO_ROOT, "docs", "user-manual", "pdf-output");
const OUTPUT_FILE = path.join(OUTPUT_DIR, "FMCG-ERP-Administration-Manual.pdf");
const TEMP_HTML = path.join(OUTPUT_DIR, "_temp_admin_manual.html");

console.log("=== FMCG ERP Administration Manual — PDF Generator ===\n");

if (!fs.existsSync(SOURCE_MD)) {
  console.error("Source markdown not found:", SOURCE_MD);
  process.exit(1);
}

const css = fs.existsSync(CSS_FILE) ? fs.readFileSync(CSS_FILE, "utf8") : "";
const mdContent = fs.readFileSync(SOURCE_MD, "utf8");

// Resolve screenshot refs relative to docs/manuals/admin/ → actual captured folder
const resolvedMd = mdContent.replace(
  /!\[([^\]]*)\]\(([^)]+)\)/g,
  (match, alt, src) => {
    // Handle both relative paths and captured/ paths
    const basename = path.basename(src);
    const candidates = [
      path.join(SCREENSHOTS_DIR, basename),
      path.join(REPO_ROOT, "docs", "user-manual", "screenshots", "captured", basename),
      // For paths like ../../user-manual/screenshots/captured/XXX.png
      path.resolve(path.join(REPO_ROOT, "docs", "manuals", "admin"), src),
    ];
    for (const c of candidates) {
      if (fs.existsSync(c)) {
        const data = fs.readFileSync(c);
        const b64 = data.toString("base64");
        return `![${alt}](data:image/png;base64,${b64})`;
      }
    }
    // Image not found — render as text note
    return `<p class="img-missing"><em>[Screenshot: ${alt} — ${basename}]</em></p>`;
  }
);

const htmlBody = marked.parse(resolvedMd);

const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>FMCG ERP Administration Manual v2.1</title>
<style>
${css}
/* Admin manual overrides */
body { font-size: 11pt; }
.img-missing { color: #888; font-style: italic; border: 1px dashed #ccc; padding: 8px; margin: 8px 0; }
img { max-width: 100%; height: auto; border: 1px solid #e0e0e0; margin: 12px 0; border-radius: 4px; }
table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 10pt; }
th { background: #f0f4f8; font-weight: 600; }
th, td { border: 1px solid #d0d0d0; padding: 6px 10px; text-align: left; }
tr:nth-child(even) td { background: #fafafa; }
code { background: #f4f4f4; padding: 1px 4px; border-radius: 3px; font-size: 9.5pt; }
pre { background: #f4f4f4; padding: 12px; border-radius: 4px; overflow-x: auto; font-size: 9pt; }
h1 { color: #1a365d; border-bottom: 2px solid #2b6cb0; padding-bottom: 6px; }
h2 { color: #2b6cb0; border-bottom: 1px solid #bee3f8; padding-bottom: 4px; margin-top: 24px; }
h3 { color: #2c5282; margin-top: 18px; }
blockquote { border-left: 4px solid #f6ad55; background: #fffaf0; padding: 8px 14px; margin: 12px 0; }
</style>
</head>
<body>
${htmlBody}
</body>
</html>`;

fs.mkdirSync(OUTPUT_DIR, { recursive: true });
fs.writeFileSync(TEMP_HTML, html, "utf8");
console.log("HTML built. Launching Chromium...");

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  await page.goto(`file:///${TEMP_HTML.replace(/\\/g, "/")}`, { waitUntil: "networkidle" });

  const imgCount = await page.evaluate(() => document.images.length);
  const imgLoaded = await page.evaluate(() =>
    Array.from(document.images).filter(i => i.complete && i.naturalWidth > 0).length
  );
  console.log(`Images: ${imgLoaded}/${imgCount} loaded`);

  await page.pdf({
    path: OUTPUT_FILE,
    format: "A4",
    margin: { top: "20mm", bottom: "20mm", left: "20mm", right: "20mm" },
    printBackground: true,
  });

  await browser.close();
  fs.unlinkSync(TEMP_HTML);

  const size = fs.statSync(OUTPUT_FILE).size;
  console.log(`\nSuccess! PDF: ${OUTPUT_FILE}`);
  console.log(`Size: ${(size / 1048576).toFixed(1)} MB`);
  console.log(`Images: ${imgLoaded}/${imgCount}`);
})().catch(e => {
  console.error("PDF generation failed:", e);
  if (fs.existsSync(TEMP_HTML)) fs.unlinkSync(TEMP_HTML);
  process.exit(1);
});
