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

console.log(`\nTotal redirect stubs: ${stubs.length}\n`);

// Group by target
const byTarget = {};
for (const s of stubs) {
  byTarget[s.target] = byTarget[s.target] || [];
  byTarget[s.target].push(s.route);
}

for (const [t, routes] of Object.entries(byTarget).sort()) {
  console.log(`Target: ${t} (${routes.length} routes)`);
  for (const r of routes) console.log(`  ${r}`);
}

// Save JSON
fs.writeFileSync('docs/REDIRECT_STUB_ROUTE_AUDIT.json', JSON.stringify(stubs, null, 2));
console.log('\nSaved docs/REDIRECT_STUB_ROUTE_AUDIT.json');
