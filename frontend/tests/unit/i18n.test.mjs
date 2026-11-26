// M46.S01.T007: the customer-screen missing-key report is empty, and locale formats differ as expected.
import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const script = fileURLToPath(new URL("../../scripts/i18n-report.mjs", import.meta.url));

test("missing-key report is empty for customer screens", () => {
  const r = spawnSync(process.execPath, [script], { encoding: "utf8" });
  const report = JSON.parse(r.stdout);
  assert.deepEqual(report.missing_in_catalog, []);
  assert.deepEqual(report.unknown_keys_in_code, []);
  assert.deepEqual(report.hardcoded_formatting, []);
  assert.ok(report.files_checked >= 10);
  assert.equal(r.status, 0);
});

test("number, money and date formats follow the locale", () => {
  const n = (tag) => new Intl.NumberFormat(tag, { maximumFractionDigits: 2 }).format(1234567.5);
  assert.equal(n("en-KE"), "1,234,567.5");
  assert.equal(n("tr-TR"), "1.234.567,5");
  const kes = (tag) => new Intl.NumberFormat(tag, { style: "currency", currency: "KES" }).format(1500);
  assert.match(kes("sw-KE"), /Ksh|KES/);
  assert.match(kes("tr-TR"), /1\.500,00/);
  const d = new Date("2026-11-26T09:30:00Z");
  assert.notEqual(new Intl.DateTimeFormat("tr-TR", { dateStyle: "medium", timeZone: "UTC" }).format(d),
    new Intl.DateTimeFormat("en-KE", { dateStyle: "medium", timeZone: "UTC" }).format(d));
});

// M51 re-review: an <option> without `value` submits its text, so translated text must never reach it.
import { scanAll, scanSource } from "../../scripts/i18n-options.mjs";
import { report } from "../../scripts/i18n-codemod.mjs";

test("no <option> without value carries tx() text, and no data attribute is translated", () => {
  assert.deepEqual(scanAll(), []);
});

test("the option scanner flags the unsafe patterns", () => {
  const bad = (src) => scanSource("x.tsx", src).map((i) => i.reason);
  assert.deepEqual(bad(`const A = () => <select><option>{tx("customer")}</option></select>;`), ["option_without_value_wraps_tx"]);
  assert.deepEqual(bad(`const A = () => <select>{[tx("a"), "b"].map((t) => <option key={t}>{t}</option>)}</select>;`), ["option_without_value_mapped_from_translated_array"]);
  assert.deepEqual(bad(`const L = lx(() => [tx("a")]); const A = () => <select>{L.map((t) => <option key={t}>{t}</option>)}</select>;`), ["option_without_value_mapped_from_translated_array"]);
  assert.deepEqual(bad(`const A = () => <input value={tx("x")} />;`), ["translated_text_in_data_attribute"]);
  assert.deepEqual(bad(`const A = () => <input onChange={(e) => set(e.target.textContent)} />;`), ["displayed_text_read_back_as_data"]);
  assert.deepEqual(bad(`const A = () => <select><option value="customer">{tx("customer")}</option>{["A","B"].map((t) => <option key={t}>{t}</option>)}</select>;`), []);
});

test("the codemod is idempotent and leaves option text alone", () => {
  assert.equal(report().totals.would_wrap, 0);
});
