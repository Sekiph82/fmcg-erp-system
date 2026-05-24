#!/usr/bin/env node
/**
 * Strict audit: all manual markdown image refs resolved, non-zero size, not placeholder.
 * Outputs JSON and MD reports to docs/manuals/
 */
const fs = require("fs");
const path = require("path");

const MANUALS_DIR = path.resolve(__dirname, "../docs/manuals");
const REPORT_JSON = path.join(MANUALS_DIR, "STRICT_MANUAL_IMAGE_AUDIT.json");
const REPORT_MD = path.join(MANUALS_DIR, "STRICT_MANUAL_IMAGE_AUDIT.md");
const MIN_SIZE_BYTES = 10 * 1024; // < 10 KB = likely placeholder
const PLACEHOLDER_PATTERNS = [/placeholder/i, /missing/i, /todo/i];

const SLUGS = [
  "manufacturing","supply-chain","sales-distribution","commercial",
  "finance-payroll","hr","logistics","maintenance","documents",
  "admin","intelligence","kenya-go-live","full-reference",
];

const manualResults = [];
let totalMissing = 0, totalSmall = 0, totalPlaceholder = 0, totalOk = 0;

for (const slug of SLUGS) {
  const dir = path.join(MANUALS_DIR, slug);
  const mdFiles = fs.readdirSync(dir).filter(f => f.endsWith(".md"));
  for (const mdFile of mdFiles) {
    const mdPath = path.join(dir, mdFile);
    const content = fs.readFileSync(mdPath, "utf8");
    const refs = [...content.matchAll(/!\[.*?\]\((.+?)\)/g)].map(m => m[1]);
    const images = [];
    for (const ref of refs) {
      const absPath = path.resolve(dir, ref);
      let status = "ok";
      let sizeBytes = 0;
      if (!fs.existsSync(absPath)) {
        status = "missing";
        totalMissing++;
      } else {
        sizeBytes = fs.statSync(absPath).size;
        if (sizeBytes < MIN_SIZE_BYTES) { status = "too_small"; totalSmall++; }
        else if (PLACEHOLDER_PATTERNS.some(p => ref.match(p))) { status = "placeholder"; totalPlaceholder++; }
        else totalOk++;
      }
      images.push({ ref, absPath, sizeBytes, status });
    }
    // Sections coverage: any H2/H3 that has zero images directly below it
    const lines = content.split("\n");
    const sectionsNoImg = [];
    let currentSection = null;
    let hasImg = false;
    for (const line of lines) {
      if (/^#{2,3} /.test(line)) {
        if (currentSection && !hasImg) sectionsNoImg.push(currentSection);
        currentSection = line.trim();
        hasImg = false;
      } else if (/!\[/.test(line)) {
        hasImg = true;
      }
    }
    if (currentSection && !hasImg) sectionsNoImg.push(currentSection);

    manualResults.push({
      slug, mdFile,
      totalImages: refs.length,
      ok: images.filter(i => i.status === "ok").length,
      missing: images.filter(i => i.status === "missing").length,
      too_small: images.filter(i => i.status === "too_small").length,
      placeholder: images.filter(i => i.status === "placeholder").length,
      sectionsWithoutImages: sectionsNoImg.length,
      images,
    });
  }
}

const report = {
  generatedAt: new Date().toISOString(),
  totalMissing, totalSmall, totalPlaceholder, totalOk,
  pass: totalMissing === 0 && totalSmall === 0 && totalPlaceholder === 0,
  manuals: manualResults,
};

fs.writeFileSync(REPORT_JSON, JSON.stringify(report, null, 2));

// MD report
let md = `# Strict Manual Image Audit\n\n`;
md += `Generated: ${report.generatedAt}\n\n`;
md += `## Summary\n\n`;
md += `| Metric | Count |\n|--------|-------|\n`;
md += `| Total OK | ${totalOk} |\n`;
md += `| Missing | ${totalMissing} |\n`;
md += `| Too Small (<10 KB) | ${totalSmall} |\n`;
md += `| Placeholder | ${totalPlaceholder} |\n`;
md += `| **PASS** | **${report.pass}** |\n\n`;
md += `## Per-Manual\n\n`;
md += `| Manual | Images | OK | Missing | Small | No-Img Sections |\n|--------|--------|----|---------|----|----|\n`;
for (const m of manualResults) {
  const flag = (m.missing > 0 || m.too_small > 0 || m.placeholder > 0) ? " ⚠" : " ✅";
  md += `| ${m.slug}${flag} | ${m.totalImages} | ${m.ok} | ${m.missing} | ${m.too_small} | ${m.sectionsWithoutImages} |\n`;
}
if (totalMissing > 0 || totalSmall > 0) {
  md += `\n## Issues\n\n`;
  for (const m of manualResults) {
    const issues = m.images.filter(i => i.status !== "ok");
    if (issues.length) {
      md += `### ${m.slug}\n`;
      issues.forEach(i => { md += `- \`${i.status}\` ${i.ref} (${i.sizeBytes} B)\n`; });
    }
  }
}
fs.writeFileSync(REPORT_MD, md);

console.log(JSON.stringify({ pass: report.pass, totalMissing, totalSmall, totalPlaceholder, totalOk }, null, 2));
if (!report.pass) process.exit(1);
