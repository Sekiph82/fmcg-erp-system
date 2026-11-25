"use client";
// M45.S01.T020 data warehouse export: targets (folder, S3-compatible, PostgreSQL), incremental jobs and run history.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type O = { datasets: string[]; formats: Record<string, string>; kinds: Record<string, string>;
  targets: { id: string; name: string; kind: string }[];
  jobs: { id: string; target_id: string; dataset: string; format: string; every_minutes: number | null; watermark: string | null }[];
  runs: { id: string; job_id: string; status: string; rows: number; deleted: number; error: string | null; schema_change: { added: string[]; removed: string[] } | null; started_at: string }[] };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };
const inp = "border rounded px-2 py-1 text-xs";

export default function WarehouseExportsPage() {
  const [o, setO] = useState<O | null>(null);
  const [t, setT] = useState({ name: "", kind: "S3", endpoint_url: "", bucket: "", prefix: "", access_key: "", dir: "", schema: "erp_export", secret: "" });
  const [j, setJ] = useState({ target_id: "", dataset: "customers", file_format: "csv", every_minutes: "" });
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => apiClient.get("/api/v1/warehouse-exports").then((r) => setO(r.data)).catch((e) => setMsg(err(e))), []);
  useEffect(() => { load(); }, [load]);
  const addTarget = () => {
    const config = t.kind === "S3" ? { endpoint_url: t.endpoint_url, bucket: t.bucket, prefix: t.prefix, access_key: t.access_key } : t.kind === "LOCAL_DIR" ? { dir: t.dir } : { schema: t.schema };
    apiClient.post("/api/v1/warehouse-exports/targets", { name: t.name, kind: t.kind, config, secret: t.secret || null }).then(() => { setMsg("Target added."); load(); }).catch((e) => setMsg(err(e)));
  };
  const addJob = () => apiClient.post("/api/v1/warehouse-exports/jobs", { ...j, every_minutes: j.every_minutes ? +j.every_minutes : null }).then(() => { setMsg("Job added."); load(); }).catch((e) => setMsg(err(e)));
  const run = (id: string) => apiClient.post(`/api/v1/warehouse-exports/jobs/${id}/run`).then((r) => { setMsg(`Run ${r.data.status.toLowerCase()}: ${r.data.rows} rows, ${r.data.deleted} deletes${r.data.error ? ` (${r.data.error})` : ""}`); load(); }).catch((e) => setMsg(err(e)));
  if (!o) return <p className="p-4 text-sm">{msg ?? "Loading…"}</p>;
  return (
    <div className="p-4 space-y-3 text-sm max-w-4xl">
      <h2 className="text-lg font-semibold">Warehouse exports</h2>
      <p className="text-xs text-gray-500">Formats: {Object.entries(o.formats).map(([k, v]) => `${k} ${v.toLowerCase()}`).join(", ")}. Targets: {Object.entries(o.kinds).map(([k, v]) => `${k} ${v.toLowerCase().replace("_", " ")}`).join(", ")}. Fields classified as sensitive are always masked.</p>
      {msg && <p role="status" className="text-xs">{msg}</p>}
      <section className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold text-xs">Add target</h3>
        <div className="flex flex-wrap gap-2"><input aria-label="Target name" className={inp} placeholder="name" value={t.name} onChange={(e) => setT({ ...t, name: e.target.value })} />
          <select aria-label="Target kind" className={inp} value={t.kind} onChange={(e) => setT({ ...t, kind: e.target.value })}>{Object.keys(o.kinds).map((k) => <option key={k}>{k}</option>)}</select>
          {t.kind === "S3" && <>{(["endpoint_url", "bucket", "prefix", "access_key"] as const).map((k) => <input key={k} aria-label={k} className={inp} placeholder={k} value={t[k]} onChange={(e) => setT({ ...t, [k]: e.target.value })} />)}</>}
          {t.kind === "LOCAL_DIR" && <input aria-label="Folder" className={inp} placeholder="folder on the server" value={t.dir} onChange={(e) => setT({ ...t, dir: e.target.value })} />}
          {t.kind === "POSTGRES" && <input aria-label="Schema" className={inp} value={t.schema} onChange={(e) => setT({ ...t, schema: e.target.value })} />}
          {(t.kind === "S3" || t.kind === "POSTGRES") && <input aria-label="Secret" type="password" className={inp} placeholder={t.kind === "S3" ? "secret key" : "PostgreSQL connection URL"} value={t.secret} onChange={(e) => setT({ ...t, secret: e.target.value })} />}
          <button className="border rounded px-2" onClick={addTarget}>Add</button></div></section>
      <section className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold text-xs">Jobs</h3>
        <div className="flex flex-wrap gap-2"><select aria-label="Job target" className={inp} value={j.target_id} onChange={(e) => setJ({ ...j, target_id: e.target.value })}><option value="">target…</option>{o.targets.map((x) => <option key={x.id} value={x.id}>{x.name} ({x.kind})</option>)}</select>
          <select aria-label="Dataset" className={inp} value={j.dataset} onChange={(e) => setJ({ ...j, dataset: e.target.value })}>{o.datasets.map((d) => <option key={d}>{d}</option>)}</select>
          <select aria-label="Format" className={inp} value={j.file_format} onChange={(e) => setJ({ ...j, file_format: e.target.value })}><option>csv</option><option>jsonl</option></select>
          <input aria-label="Every minutes" className={`${inp} w-24`} placeholder="every min" value={j.every_minutes} onChange={(e) => setJ({ ...j, every_minutes: e.target.value })} />
          <button className="border rounded px-2" onClick={addJob}>Add job</button></div>
        <ul className="text-xs divide-y">{o.jobs.map((x) => <li key={x.id} className="py-1 flex justify-between gap-2"><span>{x.dataset} → {o.targets.find((y) => y.id === x.target_id)?.name} · {x.format}{x.every_minutes ? ` · every ${x.every_minutes} min` : ""} · exported up to {x.watermark ? new Date(x.watermark).toLocaleString() : "—"}</span>
          <button className="underline" onClick={() => run(x.id)}>Run now</button></li>)}</ul></section>
      <section className="border rounded p-3 bg-white"><h3 className="font-semibold text-xs">Recent runs</h3>
        <ul className="text-xs divide-y">{o.runs.map((r) => <li key={r.id} className="py-1">{new Date(r.started_at).toLocaleString()} · {r.status.toLowerCase()} · {r.rows} rows · {r.deleted} deletes{r.schema_change ? ` · new columns ${r.schema_change.added.join(", ")}` : ""}{r.error ? ` · ${r.error}` : ""}</li>)}</ul></section>
    </div>
  );
}
