"use client";
// M45.S01.T020 data warehouse export: targets (folder, S3-compatible, PostgreSQL), incremental jobs and run history.
// M48.S01.T007/T008: Snowflake and BigQuery connection wizard, write-only credentials, test connection, approval,
// dry-run plan, sync now and SIMULATED/LIVE run history.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type Target = { id: string; name: string; kind: string; config: Record<string, unknown>; configured: boolean; status: string | null; created_by: string | null; secret_set_by: string | null; hosts: string[] | null };
type O = { datasets: string[]; formats: Record<string, string>; kinds: Record<string, string>;
  targets: Target[];
  jobs: { id: string; target_id: string; dataset: string; format: string; every_minutes: number | null; watermark: string | null }[];
  runs: { id: string; job_id: string; status: string; rows: number; deleted: number; error: string | null; mode: string | null; schema_change: { added: string[]; removed: string[] } | null; started_at: string }[] };
type Plan = { pending_rows: number; batch_rows: number; column_types: Record<string, string>; plan: Record<string, unknown>[]; configured: boolean };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };
const inp = "border rounded px-2 py-1 text-xs";
const CLOUD = ["SNOWFLAKE", "BIGQUERY"];
const FIELDS: Record<string, { key: string; label: string; ph?: string }[]> = {
  SNOWFLAKE: [{ key: "account", label: "Account identifier", ph: "myorg-myaccount" }, { key: "user", label: "Loader user", ph: "ERP_LOADER" },
    { key: "role", label: "Role (least privilege)", ph: "ERP_LOADER" }, { key: "warehouse", label: "Warehouse", ph: "LOAD_WH" },
    { key: "database", label: "Database", ph: "POVU_DW" }, { key: "schema", label: "Schema", ph: "ERP" },
    { key: "base_url", label: "API URL override (optional)", ph: "https://<account>.snowflakecomputing.com" }],
  BIGQUERY: [{ key: "project", label: "Project id", ph: "povu-dw" }, { key: "dataset", label: "Dataset", ph: "erp_export" },
    { key: "location", label: "Location", ph: "US" }, { key: "max_bytes_billed", label: "Cost cap (bytes per statement)", ph: "1000000000" },
    { key: "base_url", label: "API URL override (optional)", ph: "https://bigquery.googleapis.com" },
    { key: "token_url", label: "Token URL override (optional)", ph: "https://oauth2.googleapis.com/token" }],
};

export default function WarehouseExportsPage() {
  const [o, setO] = useState<O | null>(null);
  const [t, setT] = useState({ name: "", kind: "S3", endpoint_url: "", bucket: "", prefix: "", access_key: "", dir: "", schema: "erp_export", secret: "" });
  const [cloud, setCloud] = useState<Record<string, string>>({});
  const [allowDeletes, setAllowDeletes] = useState(true);
  const [passphrase, setPassphrase] = useState("");
  const [j, setJ] = useState({ target_id: "", dataset: "customers", file_format: "csv", every_minutes: "" });
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [plan, setPlan] = useState<Record<string, Plan>>({});
  const [replace, setReplace] = useState<{ id: string; secret: string; passphrase: string } | null>(null);
  const load = useCallback(() => apiClient.get("/api/v1/warehouse-exports").then((r) => setO(r.data)).catch((e) => setMsg(err(e))), []);
  useEffect(() => { load(); }, [load]);
  const act = async (key: string, f: () => Promise<string | void>) => {
    setBusy(key);
    try { const m = await f(); if (m) setMsg(m); load(); } catch (e) { setMsg(err(e)); } finally { setBusy(null); }
  };
  const isCloud = CLOUD.includes(t.kind);
  const addTarget = () => act("add", async () => {
    let config: Record<string, unknown>;
    if (isCloud) {
      config = Object.fromEntries(Object.entries(cloud).filter(([k, v]) => v && FIELDS[t.kind].some((f) => f.key === k)).map(([k, v]) => [k, k === "max_bytes_billed" ? +v : v]));
      config.allow_deletes = allowDeletes;
    } else config = t.kind === "S3" ? { endpoint_url: t.endpoint_url, bucket: t.bucket, prefix: t.prefix, access_key: t.access_key } : t.kind === "LOCAL_DIR" ? { dir: t.dir } : { schema: t.schema };
    const r = await apiClient.post("/api/v1/warehouse-exports/targets", { name: t.name, kind: t.kind, config, secret: t.secret || null, passphrase: passphrase || null });
    setT({ ...t, secret: "" }); setPassphrase("");
    return `Target added${r.data.public_key_fp ? ` — register this public key fingerprint on the Snowflake user: ${r.data.public_key_fp}` : ""}${r.data.client_email ? ` — service account ${r.data.client_email}` : ""}${isCloud && !t.secret ? " (not configured until a credential is saved)" : ""}.`;
  });
  const addJob = () => act("job", async () => { await apiClient.post("/api/v1/warehouse-exports/jobs", { ...j, every_minutes: j.every_minutes ? +j.every_minutes : null }); return "Job added."; });
  const run = (id: string) => act(`run-${id}`, async () => { const r = await apiClient.post(`/api/v1/warehouse-exports/jobs/${id}/run`); return `Run ${r.data.status.toLowerCase()}${r.data.mode ? ` (${r.data.mode.toLowerCase()})` : ""}: ${r.data.rows} rows, ${r.data.deleted} deletes${r.data.error ? ` — ${r.data.error}` : ""}`; });
  const dry = (id: string) => act(`dry-${id}`, async () => { const r = await apiClient.post(`/api/v1/warehouse-exports/jobs/${id}/dry-run`); setPlan((p) => ({ ...p, [id]: r.data })); return `Dry run: ${r.data.pending_rows} rows pending; nothing was sent.`; });
  const test = (id: string) => act(`test-${id}`, async () => { const r = await apiClient.post(`/api/v1/warehouse-exports/targets/${id}/test`); return r.data.ok ? `Connection OK (${(r.data.mode ?? "").toLowerCase()}): ${Object.entries(r.data).filter(([k]) => !["ok", "mode"].includes(k)).map(([k, v]) => `${k} ${v}`).join(", ")}` : `Connection failed: ${r.data.error}`; });
  const approve = (id: string) => act(`approve-${id}`, async () => { const r = await apiClient.post(`/api/v1/warehouse-exports/targets/${id}/approve`); return `Target approved for live sync to ${(r.data.hosts ?? []).join(", ")} (still needs the owner's runtime switch).`; });
  const saveSecret = () => replace && act(`secret-${replace.id}`, async () => { const r = await apiClient.put(`/api/v1/warehouse-exports/targets/${replace.id}/secret`, { secret: replace.secret, passphrase: replace.passphrase || null }); setReplace(null); return `Credential saved${r.data.public_key_fp ? ` — fingerprint ${r.data.public_key_fp}` : ""}${r.data.client_email ? ` — ${r.data.client_email}` : ""}. Approval must be given again.`; });
  if (!o) return <p className="p-4 text-sm">{msg ?? "Loading…"}</p>;
  const tgt = (id: string) => o.targets.find((y) => y.id === id);
  return (
    <div className="p-4 space-y-3 text-sm max-w-4xl">
      <h2 className="text-lg font-semibold">Warehouse exports</h2>
      <p className="text-xs text-gray-500">Formats: {Object.entries(o.formats).map(([k, v]) => `${k} ${v.toLowerCase()}`).join(", ")}. Targets: {Object.keys(o.kinds).join(", ")}. Fields classified as sensitive are always masked. Snowflake/BigQuery sync stays simulated until the owner enables live sync and a second administrator approves the target.</p>
      {msg && <p role="status" className="text-xs border rounded p-2 bg-gray-50 break-words">{msg}</p>}
      <section className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold text-xs">Add target</h3>
        <div className="flex flex-wrap gap-2"><input aria-label="Target name" className={inp} placeholder="name" value={t.name} onChange={(e) => setT({ ...t, name: e.target.value })} />
          <select aria-label="Target kind" className={inp} value={t.kind} onChange={(e) => { setT({ ...t, kind: e.target.value, secret: "" }); setCloud({}); }}>{Object.keys(o.kinds).map((k) => <option key={k}>{k}</option>)}</select>
          {t.kind === "S3" && <>{(["endpoint_url", "bucket", "prefix", "access_key"] as const).map((k) => <input key={k} aria-label={k} className={inp} placeholder={k} value={t[k]} onChange={(e) => setT({ ...t, [k]: e.target.value })} />)}</>}
          {t.kind === "LOCAL_DIR" && <input aria-label="Folder" className={inp} placeholder="folder on the server" value={t.dir} onChange={(e) => setT({ ...t, dir: e.target.value })} />}
          {t.kind === "POSTGRES" && <input aria-label="Schema" className={inp} value={t.schema} onChange={(e) => setT({ ...t, schema: e.target.value })} />}
          {(t.kind === "S3" || t.kind === "POSTGRES") && <input aria-label="Secret" type="password" className={inp} placeholder={t.kind === "S3" ? "secret key" : "PostgreSQL connection URL"} value={t.secret} onChange={(e) => setT({ ...t, secret: e.target.value })} />}
        </div>
        {isCloud && <div className="grid sm:grid-cols-2 gap-2">
          {FIELDS[t.kind].map((f) => <label key={f.key} className="text-xs flex flex-col gap-0.5">{f.label}<input aria-label={f.label} className={inp} placeholder={f.ph} value={cloud[f.key] ?? ""} onChange={(e) => setCloud({ ...cloud, [f.key]: e.target.value })} /></label>)}
          <label className="text-xs flex items-center gap-1"><input type="checkbox" checked={allowDeletes} onChange={(e) => setAllowDeletes(e.target.checked)} /> Delete warehouse rows removed in the ERP</label>
          <label className="text-xs flex flex-col gap-0.5 sm:col-span-2">{t.kind === "SNOWFLAKE" ? "Private key (PEM, PKCS#8) — write-only, encrypted at rest" : "Service-account key JSON — write-only, encrypted at rest"}
            <textarea aria-label="Credential" className={`${inp} font-mono h-20`} autoComplete="off" spellCheck={false} value={t.secret} onChange={(e) => setT({ ...t, secret: e.target.value })} placeholder="optional now; the target stays NOT_CONFIGURED without it" /></label>
          {t.kind === "SNOWFLAKE" && <input aria-label="Key passphrase" type="password" className={inp} placeholder="key passphrase (if encrypted)" value={passphrase} onChange={(e) => setPassphrase(e.target.value)} />}
        </div>}
        <button className="border rounded px-2 disabled:opacity-50" disabled={!t.name || busy === "add"} title={!t.name ? "Give the target a name" : undefined} onClick={addTarget}>{busy === "add" ? "Adding…" : "Add"}</button></section>
      <section className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold text-xs">Targets</h3>
        <ul className="text-xs divide-y">{o.targets.map((x) => {
          const c = CLOUD.includes(x.kind);
          return <li key={x.id} className="py-1 space-y-1"><div className="flex flex-wrap justify-between gap-2">
            <span>{x.name} · {x.kind}{c && <> · <b>{x.status?.replace("_", " ").toLowerCase()}</b>{x.config.public_key_fp ? ` · key ${String(x.config.public_key_fp).slice(0, 20)}…` : ""}{x.config.client_email ? ` · ${x.config.client_email}` : ""}{x.config.approved_by ? ` · approved by ${x.config.approved_by}` : ""}{x.secret_set_by ? ` · credential set by ${x.secret_set_by}` : ""}</>}</span>
            {c && <span className="flex gap-2">
              <button className="underline disabled:opacity-50" disabled={busy === `test-${x.id}`} onClick={() => test(x.id)}>Test connection</button>
              <button className="underline" onClick={() => setReplace({ id: x.id, secret: "", passphrase: "" })}>{x.configured ? "Replace credential" : "Add credential"}</button>
              <button className="underline disabled:opacity-50" disabled={!x.configured || !!x.config.approved_by} title={!x.configured ? "Save a credential first" : x.config.approved_by ? "Already approved" : `Approve live sync to ${(x.hosts ?? []).join(", ")} — only an administrator who neither created this target nor set its credential`} onClick={() => approve(x.id)}>Approve</button>
            </span>}</div>
            {c && x.hosts && <p className={x.hosts.some((h) => h.startsWith("REFUSED")) ? "text-red-700" : "text-gray-600"}>Sends to: {x.hosts.join(" · ")}</p>}
            {replace?.id === x.id && <div className="flex flex-wrap gap-2"><textarea aria-label="New credential" className={`${inp} font-mono h-16 flex-1`} autoComplete="off" spellCheck={false} placeholder={x.kind === "SNOWFLAKE" ? "PEM private key" : "service-account JSON"} value={replace.secret} onChange={(e) => setReplace({ ...replace, secret: e.target.value })} />
              {x.kind === "SNOWFLAKE" && <input aria-label="New key passphrase" type="password" className={inp} placeholder="passphrase" value={replace.passphrase} onChange={(e) => setReplace({ ...replace, passphrase: e.target.value })} />}
              <button className="border rounded px-2 disabled:opacity-50" disabled={!replace.secret} onClick={saveSecret}>Save</button><button className="underline" onClick={() => setReplace(null)}>Cancel</button></div>}
          </li>; })}</ul></section>
      <section className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold text-xs">Jobs</h3>
        <div className="flex flex-wrap gap-2"><select aria-label="Job target" className={inp} value={j.target_id} onChange={(e) => setJ({ ...j, target_id: e.target.value })}><option value="">target…</option>{o.targets.map((x) => <option key={x.id} value={x.id}>{x.name} ({x.kind})</option>)}</select>
          <select aria-label="Dataset" className={inp} value={j.dataset} onChange={(e) => setJ({ ...j, dataset: e.target.value })}>{o.datasets.map((d) => <option key={d}>{d}</option>)}</select>
          <select aria-label="Format" className={inp} value={j.file_format} onChange={(e) => setJ({ ...j, file_format: e.target.value })}><option>csv</option><option>jsonl</option></select>
          <input aria-label="Every minutes" className={`${inp} w-24`} placeholder="every min" value={j.every_minutes} onChange={(e) => setJ({ ...j, every_minutes: e.target.value })} />
          <button className="border rounded px-2 disabled:opacity-50" disabled={!j.target_id} title={!j.target_id ? "Choose a target" : undefined} onClick={addJob}>Add job</button></div>
        <ul className="text-xs divide-y">{o.jobs.map((x) => { const tg = tgt(x.target_id); const c = tg && CLOUD.includes(tg.kind); const p = plan[x.id];
          return <li key={x.id} className="py-1 space-y-1"><div className="flex justify-between gap-2"><span>{x.dataset} → {tg?.name} · {c ? tg?.kind.toLowerCase() : x.format}{x.every_minutes ? ` · every ${x.every_minutes} min` : ""} · exported up to {x.watermark ? new Date(x.watermark).toLocaleString() : "—"}</span>
            <span className="flex gap-2">{c && <button className="underline disabled:opacity-50" disabled={busy === `dry-${x.id}`} onClick={() => dry(x.id)}>Dry run</button>}
              <button className="underline disabled:opacity-50" disabled={busy === `run-${x.id}` || (c && !tg?.configured)} title={c && !tg?.configured ? "NOT_CONFIGURED: save the target's credential first" : undefined} onClick={() => run(x.id)}>{busy === `run-${x.id}` ? "Syncing…" : c ? "Sync now" : "Run now"}</button></span></div>
            {p && <div className="border rounded p-2 bg-gray-50 space-y-1"><p>{p.pending_rows} rows pending, first batch {p.batch_rows}. Column types: {Object.entries(p.column_types).map(([k, v]) => `${k} ${v}`).join(", ")}</p>
              <ol className="list-decimal pl-5 space-y-0.5 font-mono break-all">{p.plan.map((s, i) => <li key={i}>{String(s.request)} {s.statement ? String(s.statement) : s.body ? JSON.stringify(s.body) : ""}{s.upload ? ` [${(s.upload as { rows: number }).rows} rows]` : ""}</li>)}</ol>
              <button className="underline" onClick={() => setPlan((q) => { const n = { ...q }; delete n[x.id]; return n; })}>Hide plan</button></div>}
          </li>; })}</ul></section>
      <section className="border rounded p-3 bg-white"><h3 className="font-semibold text-xs">Recent runs</h3>
        <ul className="text-xs divide-y">{o.runs.map((r) => <li key={r.id} className={`py-1 ${r.status === "FAILED" ? "text-red-700" : ""}`}>{new Date(r.started_at).toLocaleString()} · {r.status.toLowerCase()}{r.mode ? ` · ${r.mode.toLowerCase()}` : ""} · {r.rows} rows · {r.deleted} deletes{r.schema_change ? ` · new columns ${r.schema_change.added.join(", ")}` : ""}{r.error ? ` · ${r.error}` : ""}</li>)}</ul></section>
    </div>
  );
}
