#!/usr/bin/env node
/**
 * Screenshot coverage audit: images per manual, sections without screenshots.
 */
const fs = require("fs");
const path = require("path");

const MANUALS_DIR = path.resolve(__dirname, "../docs/manuals");
const REPORT_JSON = path.join(MANUALS_DIR, "MANUAL_SCREENSHOT_COVERAGE_AUDIT.json");
const REPORT_MD = path.join(MANUALS_DIR, "MANUAL_SCREENSHOT_COVERAGE_AUDIT.md");

const SLUGS = [
  "manufacturing","supply-chain","sales-distribution","commercial",
  "finance-payroll","hr","logistics","maintenance","documents",
  "admin","intelligence","kenya-go-live","full-reference",
];

const results = [];
for (const slug of SLUGS) {
  const dir = path.join(MANUALS_DIR, slug);
  const mdFiles = fs.readdirSync(dir).filter(f => f.endsWith(".md"));
  for (const mdFile of mdFiles) {
    const content = fs.readFileSync(path.join(dir, mdFile), "utf8");
    const imgs = [...content.matchAll(/!\[.*?\]\((.+?)\)/g)].map(m => m[1]);
    const lines = content.split("\n");
    const sections = [];
    let cur = null, curImgs = 0;
    for (const line of lines) {
      if (/^#{2,3} /.test(line)) {
        if (cur) sections.push({ heading: cur, images: curImgs });
        cur = line.trim(); curImgs = 0;
      } else if (/!\[/.test(line)) curImgs++;
    }
    if (cur) sections.push({ heading: cur, images: curImgs });
    const sectionsNoImg = sections.filter(s => s.images === 0).map(s => s.heading);
    results.push({ slug, mdFile, totalImages: imgs.length, totalSections: sections.length, sectionsWithImages: sections.filter(s => s.images > 0).length, sectionsWithoutImages: sectionsNoImg.length, sectionsWithoutImagesList: sectionsNoImg });
  }
}

fs.writeFileSync(REPORT_JSON, JSON.stringify({ generatedAt: new Date().toISOString(), manuals: results }, null, 2));

let md = `# Manual Screenshot Coverage Audit\n\nGenerated: ${new Date().toISOString()}\n\n`;
md += `| Manual | Images | Sections | w/Screenshot | w/o Screenshot |\n|--------|--------|----------|--------------|----------------|\n`;
for (const r of results) {
  md += `| ${r.slug} | ${r.totalImages} | ${r.totalSections} | ${r.sectionsWithImages} | ${r.sectionsWithoutImages} |\n`;
}
const totalImgs = results.reduce((a, r) => a + r.totalImages, 0);
md += `\n**Total images across all manuals: ${totalImgs}**\n`;
fs.writeFileSync(REPORT_MD, md);

console.log("Coverage audit complete.");
results.forEach(r => console.log(`  ${r.slug.padEnd(20)} images: ${r.totalImages}, sections w/o img: ${r.sectionsWithoutImages}`));
