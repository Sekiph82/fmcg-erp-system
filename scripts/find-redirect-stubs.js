const fs = require('fs');
const path = require('path');

function walk(dir) {
  let results = [];
  try {
    const list = fs.readdirSync(dir);
    for (const f of list) {
      const fp = path.join(dir, f);
      const stat = fs.statSync(fp);
      if (stat.isDirectory()) results = results.concat(walk(fp));
      else if (f === 'page.tsx') results.push(fp);
    }
  } catch (e) {}
  return results;
}

const pages = walk('frontend/src/app/dashboard');
const stubs = [];

for (const p of pages) {
  const content = fs.readFileSync(p, 'utf8');
  const lines = content.split('\n').filter(l => l.trim());
  if (content.includes('redirect(') && lines.length <= 8) {
    const m = content.match(/redirect\(["'`]([^"'`]+)["'`]\)/);
    const target = m ? m[1] : 'unknown';
    const normalized = p.split(path.sep).join('/');
    const route = normalized
      .replace('frontend/src/app', '')
      .replace('/page.tsx', '');
    stubs.push({ route, file: normalized, target, lineCount: lines.length });
  }
}

console.log(JSON.stringify(stubs, null, 2));
console.error(`Found ${stubs.length} redirect stubs`);
