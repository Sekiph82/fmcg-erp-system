"use client";
import { useCallback, useEffect, useState } from "react";
import {
  crmApi, fmtCurrency, type CRMStage, type CRMTerritory, type ForecastDetail, type ForecastFilters, type ForecastSnapshot,
} from "@/lib/crm_pipeline";

function errorText(e: unknown) {
  const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "detail" in detail) return String((detail as { detail: unknown }).detail);
  return "Could not load the forecast.";
}

export default function ForecastPage() {
  const [filters, setFilters] = useState<ForecastFilters>({ months_ahead: 6 });
  const [detail, setDetail] = useState<ForecastDetail | null>(null);
  const [stages, setStages] = useState<CRMStage[]>([]);
  const [territories, setTerritories] = useState<CRMTerritory[]>([]);
  const [snapshots, setSnapshots] = useState<ForecastSnapshot[]>([]);
  const [viewing, setViewing] = useState<ForecastSnapshot | null>(null);
  const [label, setLabel] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const clean = Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== "" && v != null));
      const [d, snaps] = await Promise.all([crmApi.getForecastDetail(clean), crmApi.listForecastSnapshots()]);
      setDetail(d);
      setSnapshots(snaps);
    } catch (e) {
      setError(errorText(e));
    }
    setLoading(false);
  }, [filters]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    crmApi.getStages(true).then(setStages).catch(() => setStages([]));
    crmApi.getTerritories(true).then(setTerritories).catch(() => setTerritories([]));
  }, []);

  async function saveSnapshot() {
    try {
      const clean = Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== "" && v != null));
      await crmApi.createForecastSnapshot({ ...clean, label: label || undefined });
      setLabel("");
      setSnapshots(await crmApi.listForecastSnapshots());
    } catch (e) {
      setError(errorText(e));
    }
  }

  const shown = viewing ?? detail;
  const currencies = shown?.currencies ?? [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Revenue Forecast</h1>
          <p className="text-sm text-gray-500">Open opportunities by expected close month, weighted by probability. Currencies are never added together.</p>
        </div>
        <form aria-label="Forecast filters" className="flex flex-wrap items-end gap-2" onSubmit={(e) => e.preventDefault()}>
          <label className="text-xs text-gray-500">Horizon
            <select aria-label="Horizon" value={filters.months_ahead} onChange={(e) => setFilters({ ...filters, months_ahead: +e.target.value })}
              className="block text-sm border rounded-lg px-2 py-1.5">
              {[3, 6, 12].map((m) => <option key={m} value={m}>{m} months</option>)}
            </select>
          </label>
          <label className="text-xs text-gray-500">Stage
            <select aria-label="Stage" value={filters.stage_id ?? ""} onChange={(e) => setFilters({ ...filters, stage_id: e.target.value || undefined })}
              className="block text-sm border rounded-lg px-2 py-1.5">
              <option value="">All stages</option>
              {stages.map((s) => <option key={s.id} value={s.id}>{s.stage_name}</option>)}
            </select>
          </label>
          <label className="text-xs text-gray-500">Territory
            <select aria-label="Territory" value={filters.territory_id ?? ""} onChange={(e) => setFilters({ ...filters, territory_id: e.target.value || undefined })}
              className="block text-sm border rounded-lg px-2 py-1.5">
              <option value="">All territories</option>
              {territories.map((t) => <option key={t.id} value={t.id}>{t.territory_name}</option>)}
            </select>
          </label>
          <label className="text-xs text-gray-500">Owner (rep id)
            <input aria-label="Owner" value={filters.assigned_rep_id ?? ""} onChange={(e) => setFilters({ ...filters, assigned_rep_id: e.target.value || undefined })}
              className="block text-sm border rounded-lg px-2 py-1.5 w-32" />
          </label>
        </form>
      </div>

      {error && <p role="alert" className="rounded-lg p-3 text-sm bg-red-50 border border-red-200 text-red-700">{error}</p>}
      {viewing && (
        <p className="rounded-lg p-3 text-sm bg-amber-50 border border-amber-200 text-amber-800">
          Viewing snapshot {viewing.label ?? ""} taken {new Date(viewing.taken_at).toLocaleString()}.{" "}
          <button className="underline" onClick={() => setViewing(null)}>Back to live forecast</button>
        </p>
      )}

      <div className="bg-white rounded-xl border shadow-sm p-4 overflow-x-auto">
        <h2 className="font-semibold text-gray-800 mb-3">Monthly forecast</h2>
        {loading && !viewing ? (
          <div className="text-gray-400 py-4 text-center">Loading…</div>
        ) : !shown || currencies.length === 0 ? (
          <div className="text-gray-400 py-4 text-center">No open opportunities with an expected close date in this range.</div>
        ) : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-gray-500">
              <th className="py-1">Month</th><th>Currency</th><th className="text-right">Expected</th><th className="text-right">Weighted</th><th className="text-right">Deals</th>
            </tr></thead>
            <tbody>
              {shown.rows?.filter((r) => r.deal_count > 0).map((r) => (
                <tr key={`${r.month}-${r.currency}`} className="border-t">
                  <td className="py-1.5">{r.month}</td><td>{r.currency}</td>
                  <td className="text-right">{fmtCurrency(r.expected_revenue, r.currency)}</td>
                  <td className="text-right font-medium">{fmtCurrency(r.weighted_revenue, r.currency)}</td>
                  <td className="text-right">{r.deal_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border shadow-sm p-4">
          <h2 className="font-semibold text-gray-800 mb-3">By stage</h2>
          {(shown?.by_stage ?? []).length === 0 ? <p className="text-sm text-gray-400">No data.</p> : (
            <ul className="space-y-1 text-sm">
              {shown!.by_stage!.map((s) => (
                <li key={`${s.stage}-${s.currency}`} className="flex justify-between gap-2">
                  <span>{s.stage} · {s.deal_count} deals</span>
                  <span className="font-medium">{fmtCurrency(s.weighted_revenue, s.currency)}</span>
                </li>
              ))}
            </ul>
          )}
          {(shown?.overdue_open ?? []).map((o) => (
            <p key={o.currency} className="mt-3 text-xs text-amber-700">
              {o.deal_count} open deal(s) are past their close date ({fmtCurrency(o.expected_revenue, o.currency)}) and are not in the monthly rows.
            </p>
          ))}
        </div>
        <div className="bg-white rounded-xl border shadow-sm p-4">
          <h2 className="font-semibold text-gray-800 mb-3">Snapshots</h2>
          <div className="flex gap-2 mb-3">
            <input aria-label="Snapshot label" placeholder="Label (e.g. Q4 commit)" value={label} onChange={(e) => setLabel(e.target.value)}
              className="flex-1 text-sm border rounded-lg px-2 py-1.5" />
            <button onClick={saveSnapshot} disabled={!detail} className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg disabled:opacity-50">
              Save snapshot
            </button>
          </div>
          {snapshots.length === 0 ? <p className="text-sm text-gray-400">No snapshots yet.</p> : (
            <ul className="space-y-1 text-sm">
              {snapshots.map((s) => (
                <li key={s.id} className="flex justify-between gap-2">
                  <span>{s.label ?? "Untitled"} · {new Date(s.taken_at).toLocaleString()}</span>
                  <button className="text-indigo-600 underline" onClick={async () => setViewing(await crmApi.getForecastSnapshot(s.id))}>View</button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
