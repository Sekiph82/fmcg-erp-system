/**
 * ERP-wide action card / navigation tile source inventory.
 *
 * Scans all TSX/TS files in frontend/src for patterns that look like
 * clickable action cards, navigation tiles, or quick-nav links.
 *
 * Output:
 *   docs/ACTION_CARD_SOURCE_INVENTORY.json
 *   docs/ACTION_CARD_SOURCE_INVENTORY.md
 *
 * Usage:
 *   node scripts/audit-action-card-sources.js
 */

const fs   = require('fs');
const path = require('path');

// ── Helpers ────────────────────────────────────────────────────────────────────

function walk(dir, exts) {
  let results = [];
  try {
    for (const f of fs.readdirSync(dir)) {
      const fp = path.join(dir, f);
      if (fs.statSync(fp).isDirectory()) {
        results = results.concat(walk(fp, exts));
      } else if (exts.some(e => f.endsWith(e))) {
        results.push(fp);
      }
    }
  } catch (_) {}
  return results;
}

function extractHrefs(content) {
  const hrefs = [];
  // href="..." or href={"/..."}
  const re = /href\s*[=:]\s*["'`{]+(\/dashboard[^"'`}\s]+)["'`}]+/g;
  let m;
  while ((m = re.exec(content)) !== null) hrefs.push(m[1]);
  return hrefs;
}

function extractPushes(content) {
  const pushes = [];
  const re = /(?:router\.push|router\.replace|push|replace)\s*\(\s*["'`](\/dashboard[^"'`]+)["'`]/g;
  let m;
  while ((m = re.exec(content)) !== null) pushes.push(m[1]);
  return pushes;
}

// ── Build stub map ─────────────────────────────────────────────────────────────

const pages = walk('frontend/src/app/dashboard', ['/page.tsx']);
const stubMap = {};

for (const p of pages) {
  const content = fs.readFileSync(p, 'utf8');
  const lines = content.split('\n').filter(l => l.trim());
  if (content.includes('redirect(') && lines.length <= 8) {
    const m = content.match(/redirect\(["'`]([^"'`]+)["'`]\)/);
    const target = m ? m[1] : null;
    if (!target) continue;
    const normalized = p.split(path.sep).join('/');
    const route = normalized.replace('frontend/src/app', '').replace('/page.tsx', '');
    stubMap[route] = target;
  }
}

// ── Build middleware redirect set ──────────────────────────────────────────────

const middlewareContent = fs.readFileSync('frontend/src/middleware.ts', 'utf8');
const middlewareRoutes = new Set();
const mwRe = /"(\/dashboard[^"]+)":\s*\{/g;
let mwMatch;
while ((mwMatch = mwRe.exec(middlewareContent)) !== null) {
  middlewareRoutes.add(mwMatch[1]);
}

// ── Scan source files ──────────────────────────────────────────────────────────

const srcFiles = walk('frontend/src', ['.tsx', '.ts']);
const inventory = [];

for (const f of srcFiles) {
  const content = fs.readFileSync(f, 'utf8');
  const normalized = f.split(path.sep).join('/');

  // Skip test/spec files
  if (normalized.includes('.spec.') || normalized.includes('/e2e/')) continue;

  const hrefs  = extractHrefs(content);
  const pushes = extractPushes(content);
  const targets = [...new Set([...hrefs, ...pushes])];

  for (const href of targets) {
    const isStub        = !!stubMap[href];
    const isMiddleware  = middlewareRoutes.has(href);
    const stubTarget    = stubMap[href] || null;

    let potentialIssue = '';
    let staticAnalysisStatus = 'linked_route';

    if (isStub) {
      potentialIssue = `Links to redirect stub → ${stubTarget}`;
      staticAnalysisStatus = 'broken_redirect_stub';
    } else if (isMiddleware) {
      potentialIssue = 'Route is intercepted by middleware redirect';
      staticAnalysisStatus = 'middleware_redirect';
    }

    inventory.push({
      sourceFile:           normalized,
      href,
      isRedirectStub:       isStub,
      isMiddlewareRedirect: isMiddleware,
      stubRedirectTarget:   stubTarget,
      staticAnalysisStatus,
      potentialIssue,
    });
  }
}

// ── Write outputs ──────────────────────────────────────────────────────────────

const docsDir = 'docs';
if (!fs.existsSync(docsDir)) fs.mkdirSync(docsDir);

fs.writeFileSync(
  path.join(docsDir, 'ACTION_CARD_SOURCE_INVENTORY.json'),
  JSON.stringify(inventory, null, 2)
);

// Summary counts
const stubs    = inventory.filter(i => i.isRedirectStub);
const mwItems  = inventory.filter(i => i.isMiddlewareRedirect && !i.isRedirectStub);
const clean    = inventory.filter(i => !i.isRedirectStub && !i.isMiddlewareRedirect);

const md = `# Action Card Source Inventory

**Generated:** ${new Date().toISOString().slice(0,10)}
**Method:** Static scan of all TSX/TS source files for dashboard hrefs and router.push calls.

## Summary

| Metric | Count |
|--------|-------|
| Total href / push references scanned | ${inventory.length} |
| **Pointing to redirect stub page** | ${stubs.length} |
| Pointing to middleware-redirected route | ${mwItems.length} |
| Pointing to direct route (no redirect) | ${clean.length} |

## Redirect Stub References

${stubs.length === 0
  ? '*None — all action cards point to direct routes or middleware-handled routes.*'
  : stubs.map(i =>
      `- \`${i.sourceFile}\`\n  - href: \`${i.href}\` → stub redirects to: \`${i.stubRedirectTarget}\``
    ).join('\n')}

## Middleware-Redirected References

${mwItems.length === 0
  ? '*None.*'
  : mwItems.slice(0, 30).map(i =>
      `- \`${i.href}\` in \`${i.sourceFile}\``
    ).join('\n') + (mwItems.length > 30 ? `\n- *(${mwItems.length - 30} more — see JSON)*` : '')}

## Notes

- Redirect stubs: page.tsx files with \`redirect()\` and ≤8 non-empty lines.
- Middleware redirects: routes intercepted by middleware.ts REDIRECTS map.
- Both cause extra redirect hops. Stubs are classified broken; middleware redirects are usually safe consolidation routes.
- See \`docs/BROKEN_ACTION_CARDS.json\` for cross-referenced report.
`;

fs.writeFileSync(path.join(docsDir, 'ACTION_CARD_SOURCE_INVENTORY.md'), md);

console.log(`Action card source inventory complete.`);
console.log(`  Total hrefs/pushes scanned: ${inventory.length}`);
console.log(`  Redirect stub refs:         ${stubs.length}`);
console.log(`  Middleware redirect refs:    ${mwItems.length}`);
console.log(`  Direct route refs:          ${clean.length}`);
console.log(`Saved: docs/ACTION_CARD_SOURCE_INVENTORY.json`);
console.log(`Saved: docs/ACTION_CARD_SOURCE_INVENTORY.md`);
