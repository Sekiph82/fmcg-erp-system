"use client";
import { useCallback, useEffect, useState } from "react";
import { crmApi, fmtCurrency, type FunnelFilters, type FunnelReport } from "@/lib/crm_pipeline";

function errorText(e: unknown) {
  const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "detail" in detail) return String((detail as { detail: unknown }).detail);
  return "Could not load the funnel.";
}

function iso(d: Date) { return d.toISOString().slice(0, 10); }

export default function FunnelPage() {
  const today = new Date();
  const [filters, setFilters] = useState<FunnelFilters>({ date_from: iso(new Date(today.getFullYear(), today.getMonth() - 5, 1)), date_to: iso(today) });
  const [report, setReport] = useState<FunnelReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setReport(await crmApi.getFunnel(Object.fromEntries(Object.entries(filters).filter(([, v]) => v)) as FunnelFilters));
    } catch (e) {
      setError(errorText(e));
    }
    setLoading(false);
  }, [filters]);
  useEffect(() => { load(); }, [load]);

  const top = Math.max(...(report?.funnel ?? []).map((f) => f.reached), 1);

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Sales Funnel</h1>
          <p className="text-sm text-gray-500">Leads and opportunities created in the period: how far they got, how long open ones wait, who wins them.</p>
        </div>
        <form aria-label="Funnel filters" className="flex flex-wrap items-end gap-2" onSubmit={(e) => e.preventDefault()}>
          <label className="text-xs text-gray-500">From
            <input aria-label="From" type="date" value={filters.date_from ?? ""} onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} className="block text-sm border rounded-lg px-2 py-1.5" />
          </label>
          <label className="text-xs text-gray-500">To
            <input aria-label="To" type="date" value={filters.date_to ?? ""} onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} className="block text-sm border rounded-lg px-2 py-1.5" />
          </label>
          <label className="text-xs text-gray-500">Owner (rep id)
            <input aria-label="Owner" value={filters.assigned_rep_id ?? ""} onChange={(e) => setFilters({ ...filters, assigned_rep_id: e.target.value || undefined })} className="block text-sm border rounded-lg px-2 py-1.5 w-32" />
          </label>
        </form>
      </div>
      {error && <p role="alert" className="rounded-lg p-3 text-sm bg-red-50 border border-red-200 text-red-700">{error}</p>}
      {loading ? <div className="text-gray-400 py-4 text-center">Loading…</div> : report && (
        <>
          <div className="bg-white rounded-xl border shadow-sm p-4">
            <h2 className="font-semibold text-gray-800 mb-3">Stage conversion · {report.records} records</h2>
            {report.funnel.length === 0 ? <p className="text-sm text-gray-400">No active pipeline stages configured.</p> : (
              <ul className="space-y-2">
                {report.funnel.map((f) => (
                  <li key={f.stage_id} className="text-sm">
                    <div className="flex justify-between"><span>{f.stage}</span>
                      <span>{f.reached}{f.conversion_from_previous_pct != null && <span className="text-xs text-gray-500"> · {f.conversion_from_previous_pct}% from previous</span>}</span></div>
                    <div className="h-2 bg-gray-100 rounded"><div className="h-2 bg-indigo-500 rounded" style={{ width: `${(f.reached / top) * 100}%` }} /></div>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="bg-white rounded-xl border shadow-sm p-4 overflow-x-auto">
              <h2 className="font-semibold text-gray-800 mb-3">Open records by stage age</h2>
              {report.aging.length === 0 ? <p className="text-sm text-gray-400">No open records in a stage.</p> : (
                <table className="w-full text-sm"><thead><tr className="text-left text-xs text-gray-500"><th>Stage</th><th className="text-right">Open</th><th className="text-right">Avg days</th><th className="text-right">Max</th><th className="text-right">&gt;30 d</th></tr></thead>
                  <tbody>{report.aging.map((a) => <tr key={a.stage} className="border-t"><td className="py-1.5">{a.stage}</td><td className="text-right">{a.open}</td><td className="text-right">{a.avg_days}</td><td className="text-right">{a.max_days}</td><td className="text-right">{a.over_30_days}</td></tr>)}</tbody></table>
              )}
            </div>
            <div className="bg-white rounded-xl border shadow-sm p-4">
              <h2 className="font-semibold text-gray-800 mb-3">Loss reasons</h2>
              {report.loss_reasons.length === 0 ? <p className="text-sm text-gray-400">No lost records in the period.</p> : (
                <ul className="text-sm space-y-1">{report.loss_reasons.map((l) => <li key={l.reason} className="flex justify-between"><span>{l.reason}</span><span>{l.count}</span></li>)}</ul>
              )}
            </div>
          </div>
          <div className="bg-white rounded-xl border shadow-sm p-4 overflow-x-auto">
            <h2 className="font-semibold text-gray-800 mb-3">Representative performance</h2>
            {report.reps.length === 0 ? <p className="text-sm text-gray-400">No records in the period.</p> : (
              <table className="w-full text-sm"><thead><tr className="text-left text-xs text-gray-500"><th>Owner</th><th className="text-right">Total</th><th className="text-right">Open</th><th className="text-right">Won</th><th className="text-right">Lost</th><th className="text-right">Win rate</th><th className="text-right">Won revenue</th><th className="text-right">Avg cycle (d)</th></tr></thead>
                <tbody>{report.reps.map((r) => <tr key={r.assigned_rep_id} className="border-t"><td className="py-1.5">{r.assigned_rep_id}</td><td className="text-right">{r.total}</td><td className="text-right">{r.open}</td><td className="text-right">{r.won}</td><td className="text-right">{r.lost}</td><td className="text-right">{r.win_rate_pct != null ? `${r.win_rate_pct}%` : "—"}</td><td className="text-right">{Object.entries(r.won_revenue_by_currency).map(([c, a]) => fmtCurrency(a, c)).join(" + ") || "—"}</td><td className="text-right">{r.avg_cycle_days ?? "—"}</td></tr>)}</tbody></table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
