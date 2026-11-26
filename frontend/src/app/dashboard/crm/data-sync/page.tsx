"use client";
// M45.S01.T011 no-code data sync: visual field mapping with typed transformations, dry-run diff, run, rollback,
// replay, webhook/scheduled syncs, and the data-quality overview with trend and formatting recommendations.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type Map = { target: string; source: string; transforms: string[] };
type Sync = { id: string; name: string; direction: string; source_kind: string; target: string; key_field: string; mapping: Map[]; conflict_rule: string; delete_mode: string; version: number };
type Run = { id: string; version: number; dry_run: boolean; trigger: string; status: string; counts: Record<string, number>; diff: { key: string; action: string; changes?: Record<string, [unknown, unknown]> }[]; errors: { row?: number; error: string }[]; started_at: string };
type Ov = { targets: Record<string, { key: string; fields: Record<string, string>; required: string[] }>; transforms: string[]; syncs: Sync[]; runs: Run[] };
type Q = { now: Record<string, { total: number; missing_email: number; missing_phone: number; invalid_email: number; possible_duplicates: number; score: number | null; recommendations: { id: string; field: string; value: string; suggest: string }[] }>; trend: { day: string; entity: string; score: number | null }[] };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };
const inp = "border rounded px-2 py-1 text-xs";

export default function DataSyncPage() {
  const [o, setO] = useState<Ov | null>(null);
  const [q, setQ] = useState<Q | null>(null);
  const [form, setForm] = useState({ name: "", source_kind: "UPLOAD", source_url: "", target: "customers", conflict_rule: "source_wins", delete_mode: "ignore" });
  const [maps, setMaps] = useState<Map[]>([{ target: "code", source: "code", transforms: ["trim", "upper"] }, { target: "name", source: "name", transforms: ["trim"] }]);
  const [cur, setCur] = useState<Sync | null>(null);
  const [data, setData] = useState("");
  const [fmt, setFmt] = useState<"csv" | "json">("csv");
  const [result, setResult] = useState<Run | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => {
    apiClient.get("/api/v1/data-sync").then((r) => setO(r.data)).catch((e) => setMsg(err(e)));
    apiClient.get("/api/v1/data-sync/quality").then((r) => setQ(r.data)).catch(() => setQ(null));
  }, []);
  useEffect(() => { load(); }, [load]);
  const create = () => apiClient.post("/api/v1/data-sync", { ...form, source_url: form.source_url || null, key_field: o!.targets[form.target].key, mapping: maps })
    .then((r) => { setMsg(r.data.webhook_token ? `Created. Webhook ${r.data.webhook_url} — token (shown once): ${r.data.webhook_token}` : "Sync created."); load(); }).catch((e) => setMsg(err(e)));
  const run = (dry: boolean) => cur && apiClient.post(`/api/v1/data-sync/${cur.id}/run`, { dry_run: dry, data: data || null, format: fmt })
    .then((r) => { setResult(r.data); if (!dry) load(); }).catch((e) => setMsg(err(e)));
  const setMap = (i: number, p: Partial<Map>) => setMaps(maps.map((m, j) => (j === i ? { ...m, ...p } : m)));
  if (!o) return <p className="p-4 text-sm">{msg ?? "Loading…"}</p>;
  const fields = Object.keys(o.targets[form.target].fields);
  return (
    <div className="p-4 space-y-4 text-sm">
      <h2 className="text-lg font-semibold">Data sync &amp; quality</h2>
      {msg && <p role="status" className="text-xs break-all">{msg}</p>}
      {q && <section className="grid md:grid-cols-2 gap-2">{Object.entries(q.now).map(([k, v]) => <div key={k} className="border rounded p-3 bg-white text-xs space-y-1">
        <div className="flex justify-between"><b>{k.replace("_", " ")}</b><span className="text-lg font-semibold">{v.score ?? "—"}</span></div>
        <div>{v.total} records · {v.missing_email} without e-mail · {v.missing_phone} without phone · {v.invalid_email} bad e-mails · {v.possible_duplicates} possible duplicates</div>
        {v.recommendations.length > 0 && <div className="text-gray-600">Format: {v.recommendations.slice(0, 3).map((r) => `${r.value} → ${r.suggest}`).join("; ")}{v.recommendations.length > 3 ? " …" : ""}</div>}
        <div className="text-gray-500">Trend: {q.trend.filter((t) => t.entity === k).slice(-7).map((t) => t.score ?? "—").join(" → ") || "first snapshot tonight"}</div></div>)}</section>}
      <section className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold">New sync</h3>
        <div className="flex flex-wrap gap-2">
          <input aria-label="Sync name" className={inp} placeholder="name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <select aria-label="Source" className={inp} value={form.source_kind} onChange={(e) => setForm({ ...form, source_kind: e.target.value })}><option value="UPLOAD">file upload</option><option value="HTTP_JSON">JSON endpoint</option><option value="WEBHOOK">webhook</option></select>
          {form.source_kind === "HTTP_JSON" && <input aria-label="Endpoint URL" className={inp} placeholder="https://…" value={form.source_url} onChange={(e) => setForm({ ...form, source_url: e.target.value })} />}
          <select aria-label="Target" className={inp} value={form.target} onChange={(e) => setForm({ ...form, target: e.target.value })}>{Object.keys(o.targets).map((t) => <option key={t}>{t}</option>)}</select>
          <select aria-label="Conflict rule" className={inp} value={form.conflict_rule} onChange={(e) => setForm({ ...form, conflict_rule: e.target.value })}><option value="source_wins">source wins</option><option value="target_wins">ERP wins (fill empty)</option><option value="skip">skip existing</option></select>
          <select aria-label="Deletes" className={inp} value={form.delete_mode} onChange={(e) => setForm({ ...form, delete_mode: e.target.value })}><option value="ignore">ignore deletes</option><option value="deactivate">deactivate deleted</option></select></div>
        <table className="text-xs"><thead><tr><th className="text-left">ERP field</th><th className="text-left">Source column</th><th className="text-left">Transformations</th></tr></thead>
          <tbody>{maps.map((m, i) => <tr key={i}><td><select aria-label="ERP field" className={inp} value={m.target} onChange={(e) => setMap(i, { target: e.target.value })}>{fields.map((f) => <option key={f}>{f}</option>)}</select></td>
            <td><input aria-label="Source column" className={inp} value={m.source} onChange={(e) => setMap(i, { source: e.target.value })} /></td>
            <td><input aria-label="Transformations" className={`${inp} w-72`} placeholder="trim, upper, phone_ke, default:KES" value={m.transforms.join(", ")} onChange={(e) => setMap(i, { transforms: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) })} /></td></tr>)}</tbody></table>
        <p className="text-xs text-gray-500">Allowed: {o.transforms.join(", ")}. Required for {form.target}: {o.targets[form.target].required.join(", ")}; matched by {o.targets[form.target].key}.</p>
        <div className="flex gap-2"><button className="border rounded px-2 text-xs" onClick={() => setMaps([...maps, { target: fields[0], source: "", transforms: [] }])}>+ Field</button>
          <button className="bg-indigo-600 text-white rounded px-3 py-1 text-xs" onClick={create}>Create sync</button></div></section>
      <section className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold">Run</h3>
        <div className="flex flex-wrap gap-2">{o.syncs.map((s) => <button key={s.id} className={`border rounded px-2 text-xs ${cur?.id === s.id ? "bg-indigo-50" : ""}`} onClick={() => { setCur(s); setResult(null); }}>{s.name} v{s.version} ({s.source_kind.toLowerCase()} → {s.target})</button>)}</div>
        {cur && <><textarea aria-label="Data to sync" className={`${inp} w-full font-mono`} rows={5} placeholder={cur.source_kind === "HTTP_JSON" ? "leave empty to pull from the endpoint" : "paste CSV or JSON"} value={data} onChange={(e) => setData(e.target.value)} />
          <div className="flex gap-2 items-center"><select aria-label="Format" className={inp} value={fmt} onChange={(e) => setFmt(e.target.value as "csv" | "json")}><option>csv</option><option>json</option></select>
            <button className="border rounded px-3 py-1 text-xs" onClick={() => run(true)}>Dry run</button><button className="bg-indigo-600 text-white rounded px-3 py-1 text-xs" onClick={() => run(false)}>Run</button></div></>}
        {result && <div className="text-xs space-y-1"><p><b>{result.dry_run ? "Dry run" : "Run"}</b>: {Object.entries(result.counts).map(([k, v]) => `${v} ${k}`).join(" · ")}</p>
          <ul>{result.diff.slice(0, 20).map((d, i) => <li key={i}>{d.action} {d.key}{d.changes ? `: ${Object.entries(d.changes).map(([f, c]) => `${f} ${String(c[0] ?? "∅")} → ${String(c[1])}`).join(", ")}` : ""}</li>)}</ul>
          {result.errors.map((e, i) => <p key={i} className="text-red-600">row {e.row}: {e.error}</p>)}</div>}
      </section>
      <section className="border rounded p-3 bg-white"><h3 className="font-semibold">History</h3>
        <ul className="text-xs divide-y">{o.runs.map((r) => <li key={r.id} className="py-1 flex flex-wrap justify-between gap-2"><span>{new Date(r.started_at).toLocaleString()} · v{r.version} · {r.trigger.toLowerCase()} · {r.status.toLowerCase()} · {Object.entries(r.counts).map(([k, v]) => `${v} ${k}`).join(", ")}</span>
          {r.status === "DONE" && !r.dry_run && <span className="flex gap-2"><button className="underline" onClick={() => apiClient.post(`/api/v1/data-sync/runs/${r.id}/rollback`).then(() => { setMsg("Rolled back."); load(); }).catch((e) => setMsg(err(e)))}>Roll back</button>
            <button className="underline" onClick={() => apiClient.post(`/api/v1/data-sync/runs/${r.id}/replay`).then(() => { setMsg("Replayed."); load(); }).catch((e) => setMsg(err(e)))}>Replay</button></span>}</li>)}</ul></section>
    </div>
  );
}
