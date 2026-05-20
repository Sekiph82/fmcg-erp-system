/**
 * Find action cards in consolidated workspace pages that link to redirect stubs.
 * A "broken action card" is an href/router.push in a workspace page that points
 * to a sub-route which is itself a redirect stub back to the same workspace.
 */
const fs = require('fs');
const path = require('path');

// Build stub map: route -> target
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
const stubMap = {}; // route -> target

for (const p of pages) {
  const content = fs.readFileSync(p, 'utf8');
  const lines = content.split('\n').filter(l => l.trim());
  if (content.includes('redirect(') && lines.length <= 8) {
    const m = content.match(/redirect\(["'`]([^"'`]+)["'`]\)/);
    const target = m ? m[1] : null;
    if (!target) continue;
    const normalized = p.split(path.sep).join('/');
    const route = normalized
      .replace('frontend/src/app', '')
      .replace('/page.tsx', '');
    stubMap[route] = target;
  }
}

const stubRoutes = Object.keys(stubMap);

// Now search all TSX files for hrefs pointing to stub routes
function walkTsx(dir) {
  let results = [];
  try {
    const list = fs.readdirSync(dir);
    for (const f of list) {
      const fp = path.join(dir, f);
      const stat = fs.statSync(fp);
      if (stat.isDirectory()) results = results.concat(walkTsx(fp));
      else if (f.endsWith('.tsx') || f.endsWith('.ts')) results.push(fp);
    }
  } catch (e) {}
  return results;
}

const tsxFiles = walkTsx('frontend/src');
const broken = [];

for (const f of tsxFiles) {
  const content = fs.readFileSync(f, 'utf8');
  const normalized = f.split(path.sep).join('/');

  for (const stub of stubRoutes) {
    // Check if this file references the stub route as a navigation target
    // Match href="/dashboard/foo", href={"/dashboard/foo"}, router.push("/dashboard/foo")
    const escaped = stub.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(?:href|push)\\s*[=({:]+\\s*["'\`]${escaped}["'\`]`, 'g');
    const matches = content.match(regex);
    if (matches) {
      // Skip the stub file itself
      if (normalized.includes(stub.replace(/^\/dashboard\//, 'dashboard/'))) continue;
      broken.push({
        sourceFile: normalized,
        stubRoute: stub,
        redirectTarget: stubMap[stub],
        matches,
      });
    }
  }
}

console.log(`\nBroken action cards (pointing to redirect stubs): ${broken.length}\n`);
for (const b of broken) {
  console.log(`FILE: ${b.sourceFile}`);
  console.log(`  HREF: ${b.stubRoute} → redirects to: ${b.redirectTarget}`);
  console.log(`  MATCHES: ${b.matches.join(' | ')}`);
  console.log('');
}

fs.writeFileSync('docs/BROKEN_ACTION_CARDS.json', JSON.stringify(broken, null, 2));
console.log('Saved docs/BROKEN_ACTION_CARDS.json');
