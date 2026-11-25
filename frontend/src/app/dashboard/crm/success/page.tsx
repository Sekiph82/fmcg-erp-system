"use client";
// M45.S01.T004–T006 customer success workspace: health score, churn risk, buying intent, alerts and settings.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type Health = { score: number | null; label: string; components: Record<string, number | null>; missing: string[]; trend: { day: string; score: number | null }[] };
type Churn = { probability: number | null; method: string; reason?: string; confidence?: string; factors?: { feature: string; effect: string; weight: number }[] };
type Row = { id: string; name: string; owner_user_id: string | null; health: Health; churn: Churn };
type Alert = { id: string; kind: string; customer: string; customer_id: string; score: number; reasons: string[]; created_at: string };
type Intent = { score: number; threshold: number; hot: boolean; external_feed: string; explanation: { kind: string; at: string; detail: string; points: number }[] };
type Model = { trained_at: string; metrics: { auc: number | null; brier: number; n_train: number; n_valid: number; split_date: string; note: string; baseline_rule: { auc: number | null; brier: number }; calibration: { bin: string; n: number; predicted: number; observed: number }[] } } | null;

const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };
const color = (s: number | null) => s == null ? "text-gray-400" : s >= 70 ? "text-green-700" : s >= 50 ? "text-amber-700" : "text-red-700";

export default function CustomerSuccessPage() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<{ row: Row; intent: Intent } | null>(null);
  const [model, setModel] = useState<Model>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => {
    apiClient.get("/api/v1/customer-intel/customers", { params: { q: q || undefined } }).then((r) => setRows(r.data)).catch((e) => { setRows([]); setMsg(err(e)); });
    apiClient.get("/api/v1/customer-intel/alerts").then((r) => setAlerts(r.data)).catch(() => setAlerts([]));
    apiClient.get("/api/v1/customer-intel/churn/model").then((r) => setModel(r.data)).catch(() => setModel(null));
  }, [q]);
  useEffect(() => { load(); }, [load]);
  const show = (row: Row) => apiClient.get(`/api/v1/customer-intel/customers/${row.id}`).then((r) => setOpen({ row, intent: r.data.intent })).catch((e) => setMsg(err(e)));
  const train = () => apiClient.post("/api/v1/customer-intel/churn/train").then((r) => { setMsg(r.data.trained ? "Churn model trained." : `Not trained: ${r.data.reason}`); load(); }).catch((e) => setMsg(err(e)));
  const ack = (id: string) => apiClient.post(`/api/v1/customer-intel/alerts/${id}/ack`).then(load).catch((e) => setMsg(err(e)));

  return (
    <div className="p-4 space-y-4 text-sm">
      <div className="flex flex-wrap items-center gap-2 justify-between">
        <h2 className="text-lg font-semibold">Customer success</h2>
        <div className="flex gap-2"><input aria-label="Search customers" className="border rounded px-2 py-1" placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)} />
          <button className="border rounded px-3 py-1" onClick={train}>Train churn model</button></div>
      </div>
      {msg && <p role="status" className="text-xs">{msg}</p>}
      {alerts.length > 0 && <section className="border rounded p-3 bg-amber-50 space-y-1">
        <h3 className="font-semibold">Open alerts</h3>
        {alerts.map((a) => <div key={a.id} className="flex flex-wrap justify-between gap-2 text-xs"><span><b>{a.kind.toLowerCase()}</b> · {a.customer} · {a.reasons.slice(0, 2).join("; ")}</span>
          <button className="underline" onClick={() => ack(a.id)}>Done</button></div>)}
      </section>}
      <section className="border rounded p-3 bg-white text-xs space-y-1">
        <h3 className="font-semibold text-sm">Churn model</h3>
        {!model ? <p className="text-gray-500">No model trained yet: risk uses the ordering-rhythm rule (low confidence).</p> : <>
          <p>Trained {new Date(model.trained_at).toLocaleString()} · {model.metrics.n_train} training / {model.metrics.n_valid} validation snapshots (validation from {model.metrics.split_date})</p>
          <p>AUC {model.metrics.auc ?? "—"} (rule baseline {model.metrics.baseline_rule.auc ?? "—"}) · Brier {model.metrics.brier} (baseline {model.metrics.baseline_rule.brier})</p>
          <p className="text-gray-500">{model.metrics.note}</p></>}
      </section>
      <div className="overflow-x-auto"><table className="min-w-full text-xs bg-white border rounded">
        <thead><tr className="text-left bg-gray-50"><th className="p-2">Customer</th><th>Health</th><th>Missing data</th><th>Churn risk</th><th>Why</th></tr></thead>
        <tbody>{rows === null ? <tr><td className="p-2" colSpan={5}>Loading…</td></tr> : rows.length === 0 ? <tr><td className="p-2 text-gray-500" colSpan={5}>No customers you own.</td></tr> :
          rows.map((r) => <tr key={r.id} className="border-t cursor-pointer hover:bg-gray-50" onClick={() => show(r)}>
            <td className="p-2">{r.name}</td>
            <td className={color(r.health.score)}>{r.health.score ?? "—"} · {r.health.label}</td>
            <td className="text-gray-500">{r.health.missing.join(", ") || "—"}</td>
            <td>{r.churn.probability == null ? <span className="text-gray-400">{r.churn.reason ?? "—"}</span> : `${Math.round(r.churn.probability * 100)}% (${r.churn.method}, ${r.churn.confidence} confidence)`}</td>
            <td className="text-gray-500">{(r.churn.factors ?? []).map((f) => `${f.feature} ${f.effect}`).join("; ")}</td></tr>)}</tbody></table></div>
      {open && <section className="border rounded p-3 bg-white space-y-2">
        <div className="flex justify-between"><h3 className="font-semibold">{open.row.name}</h3><button aria-label="Close" onClick={() => setOpen(null)}>×</button></div>
        <div className="grid sm:grid-cols-3 gap-2 text-xs">{Object.entries(open.row.health.components).map(([k, v]) =>
          <div key={k} className="border rounded p-2"><div className="text-gray-500">{k}</div><div className={color(v)}>{v ?? "no data"}</div></div>)}</div>
        {open.row.health.trend.length > 0 && <p className="text-xs">Trend: {open.row.health.trend.map((t) => `${t.day.slice(5)} ${t.score ?? "—"}`).join(" → ")}</p>}
        <h4 className="font-semibold text-xs">Buying intent: {open.intent.score} {open.intent.hot ? "(hot)" : ""} <span className="text-gray-500">threshold {open.intent.threshold}; external intent feed {open.intent.external_feed.toLowerCase().replace("_", " ")}</span></h4>
        <ul className="text-xs max-h-48 overflow-auto">{open.intent.explanation.length === 0 ? <li className="text-gray-500">No first-party signals in the window.</li> :
          open.intent.explanation.map((s, i) => <li key={i}>+{s.points} · {s.kind} · {s.detail} · {new Date(s.at).toLocaleDateString()}</li>)}</ul>
      </section>}
    </div>
  );
}
