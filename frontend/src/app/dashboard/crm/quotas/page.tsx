"use client";
// M43.S01.T007 sales quotas: target vs actual (confirmed orders) and forecast by category, one currency per quota.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

interface Att { target: number; actual: number; commit: number; best_case: number; pipeline: number; omitted: number;
  weighted: number; projected: number; attainment_pct: number | null; projected_pct: number | null; gap: number;
  excluded_other_currency: { orders: Record<string, number>; deals: number } }
interface Quota { id: string; scope_type: string; scope_ref: string; scope_label: string | null; period_type: string;
  period_start: string; period_end: string; currency: string; target_amount: number; notes: string | null; attainment: Att }

const money = (v: number, c: string) => `${c} ${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
const BLANK = { scope_type: "REP", scope_ref: "", scope_label: "", period_type: "MONTH", period_start: "", period_end: "",
  currency: "KES", target_amount: 0, notes: "" };

export default function CRMQuotasPage() {
  const [rows, setRows] = useState<Quota[] | null>(null);
  const [w, setW] = useState({ commit: 1, best_case: 0.5, pipeline: 0.1 });
  const [form, setForm] = useState<typeof BLANK | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const load = useCallback(() => {
    apiClient.get("/api/v1/sales-quotas", { params: w }).then((r) => setRows(r.data)).catch(() => setRows([]));
  }, [w]);
  useEffect(() => { load(); }, [load]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    try {
      await apiClient.post("/api/v1/sales-quotas", { ...form, target_amount: Number(form.target_amount) });
      setForm(null); setErr(null); load();
    } catch (x) {
      const d = (x as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
      setErr(typeof d === "string" ? d : tx("Check the fields (only CRM managers can set quotas)."));
    }
  }
  const input = "border rounded px-2 py-1 text-sm w-full";
  return (
    <div className="p-4 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">{tx("Quotas & forecast")}</h2>
        <div className="flex gap-2 text-xs">
          <a className="underline" href={`${apiClient.defaults.baseURL ?? ""}/api/v1/sales-quotas/export.csv`}>{tx("Export CSV")}</a>
          <button className="text-indigo-600 underline" onClick={() => setForm({ ...BLANK })}>{tx("+ Quota")}</button>
        </div>
      </div>
      <fieldset className="flex flex-wrap gap-3 text-xs items-end">
        <legend className="text-gray-500 mb-1">{tx("Projection assumptions (share of each category expected to close)")}</legend>
        {(["commit", "best_case", "pipeline"] as const).map((k) => (
          <label key={k}>{k.replace("_", " ")}
            <input type="number" step="0.05" min={0} max={1} className="ml-1 border rounded px-1 w-16" value={w[k]}
                   onChange={(e) => setW({ ...w, [k]: Math.min(1, Math.max(0, +e.target.value)) })} /></label>
        ))}
      </fieldset>
      {form && (
        <form onSubmit={save} className="grid sm:grid-cols-3 gap-2 border rounded p-3 bg-white">
          <label className="text-xs">{tx("Scope")}<select className={input} value={form.scope_type} onChange={(e) => setForm({ ...form, scope_type: e.target.value })}>
            <option value="REP">{tx("Rep (user id)")}</option><option value="TEAM">{tx("Team")}</option><option value="TERRITORY">{tx("Territory / region")}</option><option value="COMPANY">{tx("Company")}</option></select></label>
          <label className="text-xs">{tx("Scope id")}<input required className={input} value={form.scope_ref} onChange={(e) => setForm({ ...form, scope_ref: e.target.value })} /></label>
          <label className="text-xs">{tx("Label")}<input className={input} value={form.scope_label} onChange={(e) => setForm({ ...form, scope_label: e.target.value })} /></label>
          <label className="text-xs">{tx("From")}<input type="date" required className={input} value={form.period_start} onChange={(e) => setForm({ ...form, period_start: e.target.value })} /></label>
          <label className="text-xs">{tx("To")}<input type="date" required className={input} value={form.period_end} onChange={(e) => setForm({ ...form, period_end: e.target.value })} /></label>
          <label className="text-xs">{tx("Period")}<select className={input} value={form.period_type} onChange={(e) => setForm({ ...form, period_type: e.target.value })}>
            {["MONTH", "QUARTER", "YEAR", "CUSTOM"].map((p) => <option key={p}>{p}</option>)}</select></label>
          <label className="text-xs">{tx("Currency")}<select className={input} value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}>
            {["KES", "USD", "EUR", "GBP", "UGX", "TZS"].map((c) => <option key={c}>{c}</option>)}</select></label>
          <label className="text-xs">{tx("Target")}<input type="number" min={1} required className={input} value={form.target_amount || ""} onChange={(e) => setForm({ ...form, target_amount: +e.target.value })} /></label>
          {err && <p role="alert" className="text-xs text-red-600 sm:col-span-3">{err}</p>}
          <div className="sm:col-span-3 flex gap-2"><button className="bg-indigo-600 text-white rounded px-3 py-1 text-sm">{tx("Save")}</button>
            <button type="button" className="text-sm" onClick={() => setForm(null)}>{tx("Close")}</button></div>
        </form>
      )}
      {rows === null && <p className="text-sm text-gray-500">{tx("Loading…")}</p>}
      {rows?.length === 0 && <p className="text-sm text-gray-500">{tx("No quotas you can see yet.")}</p>}
      <div className="grid md:grid-cols-2 gap-3">
        {rows?.map((q) => {
          const a = q.attainment;
          const bar = (v: number) => `${Math.min(100, Math.max(0, (v / (a.target || 1)) * 100))}%`;
          const other = Object.keys(a.excluded_other_currency.orders).length + a.excluded_other_currency.deals;
          return (
            <div key={q.id} className="border rounded-lg p-3 bg-white text-sm space-y-1">
              <div className="flex justify-between gap-2"><span className="font-medium">{q.scope_label || q.scope_ref}</span>
                <span className="text-xs text-gray-500">{q.scope_type} · {q.period_start} → {q.period_end}</span></div>
              <div className="h-2 bg-gray-100 rounded relative overflow-hidden" aria-label={tx("Attainment")}>
                <div className="absolute h-2 bg-indigo-200" style={{ width: bar(a.projected) }} />
                <div className="absolute h-2 bg-indigo-600" style={{ width: bar(a.actual) }} />
              </div>
              <div className="grid grid-cols-2 gap-x-3 text-xs">
                <span>{tx("Target")}</span><span className="text-right">{money(a.target, q.currency)}</span>
                <span>{tx("Actual (confirmed orders)")}</span><span className="text-right">{money(a.actual, q.currency)} {a.attainment_pct !== null && `(${a.attainment_pct.toFixed(0)}%)`}</span>
                <span>{tx("Commit / best case / pipeline")}</span><span className="text-right">{money(a.commit, "")} / {money(a.best_case, "")} / {money(a.pipeline, "")}</span>
                <span>{tx("Projected")}</span><span className="text-right">{money(a.projected, q.currency)} {a.projected_pct !== null && `(${a.projected_pct.toFixed(0)}%)`}</span>
                <span>{tx("Gap to target")}</span><span className={`text-right ${a.gap > 0 ? "text-red-600" : "text-green-700"}`}>{money(a.gap, q.currency)}</span>
              </div>
              {other > 0 && <p className="text-xs text-amber-700">{tx("Other currencies not counted here:")} {Object.entries(a.excluded_other_currency.orders).map(([c, v]) => money(v, c)).join(", ")}{a.excluded_other_currency.deals ? tx(" · {deals} deal(s)", { deals: a.excluded_other_currency.deals }) : ""}.</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
