#!/usr/bin/env node
// M46.S01.T007 missing-key report for the customer-facing screens.
// 1. Every English key exists, non-empty, in sw and tr (and no stray keys).
// 2. Every t("…") / translate(locale, "…") key used in a customer screen exists in English.
// 3. Customer screens do not hard-code en-KE formatting or toLocale*String (use the i18n formatters).
// Exit code 1 when anything is found; prints a JSON report.
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(fileURLToPath(new URL(".", import.meta.url)), "..");
const msgDir = join(root, "src/lib/i18n/messages");
const LOCALES = ["en", "sw", "tr"];
const CUSTOMER = ["src/app/portal", "src/app/chat", "src/app/kb", "src/app/book", "src/app/nps", "src/app/survey", "src/app/pay",
  "src/components/site/SiteView.tsx", "src/components/PartnerLogin.tsx", "src/components/PartnerActivate.tsx", "src/components/LanguageSwitcher.tsx",
  // M47.S01.T011 staff shell
  "src/components/Sidebar.tsx", "src/components/DashboardShell.tsx", "src/app/login/page.tsx", "src/app/dashboard/page.tsx",
  // M47.S01.T003 shared quotation / e-signature and shared sales document
  "src/app/d/[token]/page.tsx", "src/app/docs/[token]/page.tsx"];

const catalogs = readdirSync(msgDir).filter((f) => f.endsWith(".json")).map((f) => ({ file: f, data: JSON.parse(readFileSync(join(msgDir, f), "utf8")) }));
const en = Object.assign({}, ...catalogs.map((c) => c.data.en));
const report = { catalogs: {}, missing_in_catalog: [], unknown_keys_in_code: [], hardcoded_formatting: [] };

for (const { file, data } of catalogs) {
  const r = { keys: Object.keys(data.en).length };
  for (const l of LOCALES.slice(1)) {
    r[`missing_${l}`] = Object.keys(data.en).filter((k) => !data[l] || !String(data[l][k] ?? "").trim());
    r[`extra_${l}`] = Object.keys(data[l] ?? {}).filter((k) => !(k in data.en));
    report.missing_in_catalog.push(...r[`missing_${l}`].map((k) => `${file}:${l}:${k}`), ...r[`extra_${l}`].map((k) => `${file}:${l}:extra:${k}`));
  }
  report.catalogs[file] = r;
}

const files = [];
const walk = (p) => {
  const abs = join(root, p);
  let st;
  try { st = statSync(abs); } catch { return; }
  if (st.isDirectory()) readdirSync(abs).forEach((f) => walk(join(p, f)));
  else if (/\.tsx?$/.test(abs)) files.push(abs);
};
CUSTOMER.forEach(walk);

const KEY_RE = /\b(?:t|translate\([^,()]+,)\s*\(?\s*["'`]([a-z][\w.-]+)["'`]/g;
for (const f of files) {
  const src = readFileSync(f, "utf8");
  for (const m of src.matchAll(KEY_RE)) if (!(m[1] in en)) report.unknown_keys_in_code.push(`${relative(root, f)}:${m[1]}`);
  src.split("\n").forEach((line, i) => {
    if (/en-KE|toLocale(Date|Time)?String\(|formatKES\(/.test(line)) report.hardcoded_formatting.push(`${relative(root, f)}:${i + 1}`);
  });
}
report.files_checked = files.length;
report.ok = !report.missing_in_catalog.length && !report.unknown_keys_in_code.length && !report.hardcoded_formatting.length;
console.log(JSON.stringify(report, null, 2));
process.exit(report.ok ? 0 : 1);
