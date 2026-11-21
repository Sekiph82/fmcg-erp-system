"use client";
// Field supervisor: per-rep compliance (coverage, GPS, orders, collections, audit scores), outlet audits, moto fraud alerts + leaderboard.
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { fx, fpost, kes, type AuditRow, type ComplianceRow } from "@/lib/field";

interface Moto {
  alerts: { id: string; fraud_type: string; severity: string; risk_score: number; rider: string | null; description: string | null; created_at: string | null }[];
  leaderboard: { rank: number; rider: string | null; avg_score: number; total_sales: number; total_orders: number; avg_route_completion: number; avg_collection_rate: number; total_fraud_flags: number }[];
}
const pct = (v: number | null) => (v == null ? "—" : `${v}%`);
const tone = (v: number | null, good: number) => (v == null ? "" : v >= good ? "text-emerald-700" : v >= good / 2 ? "text-amber-700" : "text-red-700");

export default function FieldSupervisor() {
  const [days, setDays] = useState(7);
  const [rows, setRows] = useState<ComplianceRow[] | null>(null);
  const [audits, setAudits] = useState<AuditRow[]>([]);
  const [moto, setMoto] = useState<Moto | null>(null);
  const [shelf, setShelf] = useState<ShelfReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    setError(null);
    fx<{ reps: ComplianceRow[] }>(`/field/compliance?days=${days}`).then((r) => setRows(r.reps)).catch((e) => setError(e.message));
    fx<AuditRow[]>(`/field/audits?days=${days}`).then(setAudits).catch(() => setAudits([]));
    fx<Moto>(`/field/moto?days=${days}`).then(setMoto).catch(() => setMoto(null));
    fx<ShelfReport>(`/field/shelf-report?days=${days}`).then(setShelf).catch(() => setShelf(null));
  }, [days]);
  useEffect(load, [load]);
  async function review(id: string, status: string) {
    try { await fx(`/moto-sales/fraud/alerts/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }); load(); } catch (e) { setError((e as Error).message); }
  }

  return (
    <div className="p-4 sm:p-6 space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div><h1 className="text-xl font-bold text-gray-900">Field team</h1><p className="text-sm text-gray-500">Route coverage, visits with location, orders, collections and outlet audits per rep.</p></div>
        <div className="flex items-center gap-2 text-sm">
          <select aria-label="Period" value={days} onChange={(e) => setDays(Number(e.target.value))} className="border rounded-lg px-2 py-1.5">
            {[1, 7, 30].map((d) => <option key={d} value={d}>{d === 1 ? "Today" : `Last ${d} days`}</option>)}
          </select>
          <Link href="/dashboard/field" className="underline text-indigo-700">My field app</Link>
        </div>
      </div>
      {error && <p role="alert" className="rounded-lg p-3 text-sm bg-red-50 border border-red-200 text-red-700">{error}</p>}

      {shelf && (
        <section aria-label="Shelf checks" className="bg-white rounded-xl border p-3 space-y-2">
          <h2 className="font-semibold text-gray-900">Shelf checks</h2>
          {shelf.products.length === 0 ? <p className="text-sm text-gray-400">No shelf checks in this period.</p> : (
            <div className="overflow-x-auto"><table className="w-full text-sm">
              <thead><tr className="text-left text-xs text-gray-500"><th>Product</th><th>Outlets</th><th>Out of stock</th><th>Avg facings</th><th>Planogram</th><th>Shelf price</th></tr></thead>
              <tbody>{shelf.products.map((p) => <tr key={p.sku} className="border-t"><td>{p.product}</td><td>{p.outlets_checked}</td>
                <td className={p.outlets_out_of_stock ? "text-red-700 font-semibold" : ""}>{p.outlets_out_of_stock}</td><td>{p.avg_facings ?? "—"}</td>
                <td>{p.planogram_compliance_pct === null ? "—" : `${p.planogram_compliance_pct}%`}</td>
                <td>{p.min_price === null ? "—" : p.min_price === p.max_price ? kes(p.min_price) : `${kes(p.min_price)}–${kes(p.max_price!)}`}</td></tr>)}</tbody></table></div>)}
          {shelf.out_of_stock.length > 0 && (<div><h3 className="text-xs font-semibold text-gray-500 mt-2 mb-1">Out of stock found</h3>
            <ul className="text-sm divide-y">{shelf.out_of_stock.map((o) => <li key={o.check_id} className="py-1">{o.product} — {o.outlet} <span className="text-xs text-gray-500">({o.rep}, {o.date}{o.has_photo ? ", photo" : ""})</span></li>)}</ul></div>)}
        </section>
      )}

      <section aria-label="Rep compliance" className="bg-white rounded-xl border overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs text-gray-500 border-b"><th className="p-2">Rep</th><th>Outlets</th><th>Coverage</th><th>Visits</th><th>With GPS</th><th>Last visit</th><th>Orders</th><th>Collected</th><th>Audit score</th></tr></thead>
          <tbody>{(rows ?? []).map((r) => (
            <tr key={r.rep_id} className="border-b">
              <td className="p-2"><span className="font-medium">{r.rep}</span><span className="block text-xs text-gray-500">{r.code} · {r.vehicle.toLowerCase()}</span></td>
              <td>{r.route_stops}</td><td className={tone(r.coverage_pct, 80)}>{pct(r.coverage_pct)}</td><td>{r.visits}</td>
              <td className={tone(r.visits_with_gps_pct, 90)}>{pct(r.visits_with_gps_pct)}</td>
              <td className="text-xs">{r.last_visit_at ? new Date(r.last_visit_at).toLocaleString() : "—"}</td>
              <td>{r.orders} · {kes(r.order_value)}</td><td>{r.collections} · {kes(r.collected)}</td>
              <td className={tone(r.audit_score, 80)}>{r.audits ? `${r.audit_score}% (${r.audits})` : "—"}</td>
            </tr>))}
            {rows && rows.length === 0 && <tr><td colSpan={9} className="p-4 text-center text-gray-400">No active reps.</td></tr>}
          </tbody>
        </table>
      </section>

      <div className="grid lg:grid-cols-2 gap-5">
        <section aria-label="Outlet audits" className="bg-white rounded-xl border p-3">
          <h2 className="font-semibold mb-2">Outlet audits</h2>
          {audits.length === 0 ? <p className="text-sm text-gray-400">No audits in this period.</p> : audits.map((a) => (
            <div key={a.id} className="border-t py-2 text-sm flex justify-between gap-2">
              <span className="min-w-0"><span className="font-medium">{a.outlet}</span><span className="block text-xs text-gray-500">{a.date} · rep {a.rep ?? "—"} · {a.photos} photo(s)</span>
                {a.failed.length > 0 && <span className="block text-xs text-red-700">{a.failed.join(", ")}</span>}</span>
              <span className={`font-semibold ${tone(a.score, 80)}`}>{a.score}%</span>
            </div>))}
        </section>
        <section aria-label="Moto riders" className="bg-white rounded-xl border p-3 space-y-3">
          <h2 className="font-semibold">Moto / van riders</h2>
          {!moto ? <p className="text-sm text-gray-400">No rider data.</p> : (<>
            <div><h3 className="text-xs font-semibold text-gray-500 mb-1">Open fraud alerts ({moto.alerts.length})</h3>
              {moto.alerts.length === 0 ? <p className="text-sm text-gray-400">None.</p> : moto.alerts.map((a) => (
                <div key={a.id} className="border-t py-2 text-sm">
                  <p className="flex justify-between"><span>{a.rider ?? "Unknown rider"} · {a.fraud_type.replace(/_/g, " ").toLowerCase()}</span><span className={a.severity === "HIGH" || a.severity === "CRITICAL" ? "text-red-700" : "text-amber-700"}>{a.severity} · {a.risk_score}</span></p>
                  {a.description && <p className="text-xs text-gray-600">{a.description}</p>}
                  <div className="flex gap-3 mt-1 text-xs">{["CONFIRMED", "DISMISSED", "ESCALATED"].map((s) => <button key={s} onClick={() => review(a.id, s)} className="underline">{s.toLowerCase()}</button>)}</div>
                </div>))}</div>
            <div><h3 className="text-xs font-semibold text-gray-500 mb-1">Leaderboard</h3>
              {moto.leaderboard.length === 0 ? <p className="text-sm text-gray-400">No performance computed for this period.</p> : (
                <table className="w-full text-sm"><thead><tr className="text-left text-xs text-gray-500"><th>#</th><th>Rider</th><th>Score</th><th>Sales</th><th>Route</th><th>Collection</th></tr></thead>
                  <tbody>{moto.leaderboard.map((b) => <tr key={b.rank} className="border-t"><td>{b.rank}</td><td>{b.rider ?? "—"}</td><td>{b.avg_score}</td><td>{kes(b.total_sales)}</td><td>{b.avg_route_completion}%</td><td>{b.avg_collection_rate}%</td></tr>)}</tbody></table>)}
            </div>
            <button onClick={async () => { try { await fpost("/moto-sales/fraud/scan", {}); load(); } catch (e) { setError((e as Error).message); } }} className="text-xs underline text-indigo-700">Run fraud scan now</button>
          </>)}
        </section>
      </div>
    </div>
  );
}


interface ShelfReport {
  days: number;
  products: { product: string; sku: string; outlets_checked: number; outlets_out_of_stock: number; avg_facings: number | null;
    planogram_compliance_pct: number | null; min_price: number | null; max_price: number | null }[];
  out_of_stock: { product: string; outlet: string; rep: string; date: string; check_id: string; has_photo: boolean }[];
}
