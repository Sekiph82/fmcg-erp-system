"use client";
// M45.S01.T011 no-code data sync: visual field mapping with typed transformations, dry-run diff, run, rollback,
// replay, webhook/scheduled syncs, and the data-quality overview with trend and formatting recommendations.
// M50.S01.T009: every ERP object (dependency order), staged order proposals needing a second person, read-only stock/invoices,
// conflicts, reconciliation, Parquet input.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

type Map = { target: string; source: string; transforms: string[] };
type Sync = { id: string; name: string; direction: string; source_kind: string; target: string; key_field: string; mapping: Map[]; conflict_rule: string; delete_mode: string; version: number };
type Run = { id: string; version: number; dry_run: boolean; trigger: string; status: string; counts: Record<string, number>; diff: { key: string; action: string; changes?: Record<string, [unknown, unknown]> }[]; errors: { row?: number; error: string }[]; started_at: string };
type Ov = { targets: Record<string, { key: string; fields: Record<string, string>; required: string[]; mode?: string; depends?: string[]; why?: string | null; adapter?: string | null }>; order?: string[]; transforms: string[]; syncs: Sync[]; runs: Run[] };
type Q = { now: Record<string, { total: number; missing_email: number; missing_phone: number; invalid_email: number; possible_duplicates: number; score: number | null; recommendations: { id: string; field: string; value: string; suggest: string }[] }>; trend: { day: string; entity: string; score: number | null }[] };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : tx("Something went wrong."); };
const inp = "border rounded px-2 py-1 text-xs";

export default function DataSyncPage() {
  const [o, setO] = useState<Ov | null>(null);
  const [q, setQ] = useState<Q | null>(null);
  const [form, setForm] = useState({ name: "", source_kind: "UPLOAD", source_url: "", target: "customers", conflict_rule: "source_wins", delete_mode: "ignore", direction: "IN", custom_type: "", custom_key: "", assoc_from: "contact" });
  const [maps, setMaps] = useState<Map[]>([{ target: "code", source: "code", transforms: ["trim", "upper"] }, { target: "name", source: "name", transforms: ["trim"] }]);
  const [cur, setCur] = useState<Sync | null>(null);
  const [data, setData] = useState("");
  const [fmt, setFmt] = useState<"csv" | "json" | "parquet">("csv");
  const [result, setResult] = useState<Run | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => {
    apiClient.get("/api/v1/data-sync").then((r) => setO(r.data)).catch((e) => setMsg(err(e)));
    apiClient.get("/api/v1/data-sync/quality").then((r) => setQ(r.data)).catch(() => setQ(null));
  }, []);
  useEffect(() => { load(); }, [load]);
  const tgt = o?.targets[form.target];
  const options = form.target === "custom_objects" ? { custom_type: form.custom_type } : form.target === "associations" ? { from: form.assoc_from } : {};
  const { custom_type: _ct, custom_key: _ck, assoc_from: _af, ...formBody } = form;
  const create = () => apiClient.post("/api/v1/data-sync", { ...formBody, direction: tgt?.mode === "read_only" ? "OUT" : form.direction, source_url: form.source_url || null, key_field: tgt?.adapter === "co" ? form.custom_key : o!.targets[form.target].key, mapping: maps, options })
    .then((r) => { setMsg(r.data.webhook_token ? tx("Created. Webhook {webhook_url} — token (shown once): {webhook_token}", { webhook_url: r.data.webhook_url, webhook_token: r.data.webhook_token }) : tx("Sync created.")); load(); }).catch((e) => setMsg(err(e)));
  const run = (dry: boolean) => cur && apiClient.post(`/api/v1/data-sync/${cur.id}/run`, { dry_run: dry, data: data || null, format: fmt })
    .then((r) => { setResult(r.data); if (!dry) load(); }).catch((e) => setMsg(err(e)));
  const setMap = (i: number, p: Partial<Map>) => setMaps(maps.map((m, j) => (j === i ? { ...m, ...p } : m)));
  if (!o) return <p className="p-4 text-sm">{msg ?? tx("Loading…")}</p>;
  const fields = Object.keys(o.targets[form.target].fields);
  return (
    <div className="p-4 space-y-4 text-sm">
      <h2 className="text-lg font-semibold">{tx("Data sync & quality")}</h2>
      {msg && <p role="status" className="text-xs break-all">{msg}</p>}
      {q && <section className="grid md:grid-cols-2 gap-2">{Object.entries(q.now).map(([k, v]) => <div key={k} className="border rounded p-3 bg-white text-xs space-y-1">
        <div className="flex justify-between"><b>{k.replace("_", " ")}</b><span className="text-lg font-semibold">{v.score ?? "—"}</span></div>
        <div>{v.total} {tx("records ·")} {v.missing_email} {tx("without e-mail ·")} {v.missing_phone} {tx("without phone ·")} {v.invalid_email} {tx("bad e-mails ·")} {v.possible_duplicates} {tx("possible duplicates")}</div>
        {v.recommendations.length > 0 && <div className="text-gray-600">{tx("Format:")} {v.recommendations.slice(0, 3).map((r) => `${r.value} → ${r.suggest}`).join("; ")}{v.recommendations.length > 3 ? " …" : ""}</div>}
        <div className="text-gray-500">{tx("Trend:")} {q.trend.filter((t) => t.entity === k).slice(-7).map((t) => t.score ?? "—").join(" → ") || tx("first snapshot tonight")}</div></div>)}</section>}
      <section className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold">{tx("New sync")}</h3>
        <div className="flex flex-wrap gap-2">
          <input aria-label={tx("Sync name")} className={inp} placeholder={tx("name")} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <select aria-label={tx("Source")} className={inp} value={form.source_kind} onChange={(e) => setForm({ ...form, source_kind: e.target.value })}><option value="UPLOAD">{tx("file upload")}</option><option value="HTTP_JSON">{tx("JSON endpoint")}</option><option value="WEBHOOK">{tx("webhook")}</option></select>
          {form.source_kind === "HTTP_JSON" && <input aria-label={tx("Endpoint URL")} className={inp} placeholder="https://…" value={form.source_url} onChange={(e) => setForm({ ...form, source_url: e.target.value })} />}
          <select aria-label={tx("Direction")} className={inp} value={tgt?.mode === "read_only" ? "OUT" : form.direction} disabled={tgt?.mode === "read_only"} onChange={(e) => setForm({ ...form, direction: e.target.value })}><option value="IN">{tx("into the ERP")}</option><option value="OUT">{tx("out of the ERP (export)")}</option></select>
          <select aria-label={tx("Target")} className={inp} value={form.target} onChange={(e) => { const m = o.targets[e.target.value]; setForm({ ...form, target: e.target.value, direction: m?.mode === "read_only" ? "OUT" : form.direction }); }}>{(o.order ?? Object.keys(o.targets)).map((t) => <option key={t} value={t}>{t}{o.targets[t].mode && o.targets[t].mode !== "write" ? ` (${o.targets[t].mode === "read_only" ? "read-only" : "needs approval"})` : ""}</option>)}</select>
          {form.target === "custom_objects" && <><input aria-label={tx("Custom object type key")} className={inp} placeholder={tx("object type key")} value={form.custom_type} onChange={(e) => setForm({ ...form, custom_type: e.target.value })} />
            <input aria-label={tx("Key field")} className={inp} placeholder={tx("key field (the type's display field)")} value={form.custom_key} onChange={(e) => setForm({ ...form, custom_key: e.target.value })} /></>}
          {form.target === "associations" && <input aria-label={tx("Associations from")} className={inp} placeholder={tx("contact or custom:<type>")} value={form.assoc_from} onChange={(e) => setForm({ ...form, assoc_from: e.target.value })} />}
          <select aria-label={tx("Conflict rule")} className={inp} value={form.conflict_rule} onChange={(e) => setForm({ ...form, conflict_rule: e.target.value })}><option value="source_wins">{tx("source wins")}</option><option value="target_wins">{tx("ERP wins (fill empty)")}</option><option value="skip">{tx("skip existing")}</option></select>
          <select aria-label={tx("Deletes")} className={inp} value={form.delete_mode} onChange={(e) => setForm({ ...form, delete_mode: e.target.value })}><option value="ignore">{tx("ignore deletes")}</option><option value="deactivate">{tx("deactivate deleted")}</option></select></div>
        <table className="text-xs"><thead><tr><th className="text-left">{tx("ERP field")}</th><th className="text-left">{tx("Source column")}</th><th className="text-left">{tx("Transformations")}</th></tr></thead>
          <tbody>{maps.map((m, i) => <tr key={i}><td><select aria-label={tx("ERP field")} className={inp} value={m.target} onChange={(e) => setMap(i, { target: e.target.value })}>{fields.map((f) => <option key={f}>{f}</option>)}</select></td>
            <td><input aria-label={tx("Source column")} className={inp} value={m.source} onChange={(e) => setMap(i, { source: e.target.value })} /></td>
            <td><input aria-label={tx("Transformations")} className={`${inp} w-72`} placeholder={tx("trim, upper, phone_ke, default:KES")} value={m.transforms.join(", ")} onChange={(e) => setMap(i, { transforms: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) })} /></td></tr>)}</tbody></table>
        <p className="text-xs text-gray-500">{tx("Allowed:")} {o.transforms.join(", ")}{tx(". Required for")} {form.target}: {o.targets[form.target].required.join(", ")}{tx("; matched by")} {o.targets[form.target].key}.{tgt?.depends?.length ? tx(" Sync first: {depends}.", { depends: tgt.depends.join(", ") }) : ""}</p>
        {tgt?.mode === "read_only" && <p role="note" className="text-xs text-amber-700">{tgt.why} {tx("Only export (read) syncs can be defined.")}</p>}
        {tgt?.mode === "propose" && <p role="note" className="text-xs text-amber-700">{tx("Inbound rows are only staged as proposals (one row per line, grouped by")} {tgt.key}{tx("); a different person with the create right approves each one and it becomes a DRAFT document.")}</p>}
        <div className="flex gap-2"><button className="border rounded px-2 text-xs" onClick={() => setMaps([...maps, { target: fields[0], source: "", transforms: [] }])}>{tx("+ Field")}</button>
          <button className="bg-indigo-600 text-white rounded px-3 py-1 text-xs" onClick={create}>{tx("Create sync")}</button></div></section>
      <section className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold">{tx("Run")}</h3>
        <div className="flex flex-wrap gap-2">{o.syncs.map((s) => <button key={s.id} className={`border rounded px-2 text-xs ${cur?.id === s.id ? "bg-indigo-50" : ""}`} onClick={() => { setCur(s); setResult(null); }}>{s.name} {tx("v")}{s.version} ({s.source_kind.toLowerCase()} → {s.target})</button>)}</div>
        {cur && <><textarea aria-label={tx("Data to sync")} className={`${inp} w-full font-mono`} rows={5} placeholder={cur.source_kind === "HTTP_JSON" ? tx("leave empty to pull from the endpoint") : tx("paste CSV or JSON")} value={data} onChange={(e) => setData(e.target.value)} />
          <div className="flex gap-2 items-center"><select aria-label={tx("Format")} className={inp} value={fmt} onChange={(e) => setFmt(e.target.value as "csv" | "json" | "parquet")}><option value="csv">{tx("csv")}</option><option value="json">{tx("json")}</option><option value="parquet">parquet</option></select>
            {fmt === "parquet" && <input aria-label={tx("Parquet file")} type="file" accept=".parquet" className="text-xs" onChange={(e) => { const f = e.target.files?.[0]; if (!f) return; const rd = new FileReader(); rd.onload = () => setData(String(rd.result).split(",")[1] ?? ""); rd.readAsDataURL(f); }} />}
            <button className="border rounded px-3 py-1 text-xs" onClick={() => run(true)}>{tx("Dry run")}</button><button className="bg-indigo-600 text-white rounded px-3 py-1 text-xs" onClick={() => run(false)}>{tx("Run")}</button></div></>}
        {result && <div className="text-xs space-y-1"><p><b>{result.dry_run ? tx("Dry run") : tx("Run")}</b>: {Object.entries(result.counts).map(([k, v]) => `${v} ${k}`).join(" · ")}</p>
          <ul>{result.diff.slice(0, 20).map((d, i) => <li key={i}>{d.action} {d.key}{d.changes ? `: ${Object.entries(d.changes).map(([f, c]) => `${f} ${String(c[0] ?? "∅")} → ${String(c[1])}`).join(", ")}` : ""}</li>)}</ul>
          {result.errors.map((e, i) => <p key={i} className="text-red-600">{tx("row")} {e.row}: {e.error}</p>)}</div>}
      </section>
      <M50Panels msg={setMsg} reload={load} />
      <section className="border rounded p-3 bg-white"><h3 className="font-semibold">{tx("History")}</h3>
        <ul className="text-xs divide-y">{o.runs.map((r) => <li key={r.id} className="py-1 flex flex-wrap justify-between gap-2"><span>{new Date(r.started_at).toLocaleString()} {tx("· v")}{r.version} · {r.trigger.toLowerCase()} · {r.status.toLowerCase()} · {Object.entries(r.counts).map(([k, v]) => `${v} ${k}`).join(", ")}</span>
          {r.status === "DONE" && !r.dry_run && <span className="flex gap-2"><button className="underline" onClick={() => apiClient.post(`/api/v1/data-sync/runs/${r.id}/rollback`).then(() => { setMsg(tx("Rolled back.")); load(); }).catch((e) => setMsg(err(e)))}>{tx("Roll back")}</button>
            <button className="underline" onClick={() => apiClient.post(`/api/v1/data-sync/runs/${r.id}/replay`).then(() => { setMsg(tx("Replayed.")); load(); }).catch((e) => setMsg(err(e)))}>{tx("Replay")}</button></span>}</li>)}</ul></section>
    </div>
  );
}


// ── M50.S01.T009: proposals, conflicts, reconciliation ──────────────────────────────────────────────────────────
type Prop = { id: string; target: string; key: string; status: string; payload_hash: string; proposed_by: string | null; decided_by: string | null; error: string | null; applied_ref: string | null; payload: { head: Record<string, unknown>; lines: unknown[] } };
type Conf = { id: string; target: string; key: string; field: string; source_value: string | null; erp_value: string | null };
function M50Panels({ msg, reload }: { msg: (m: string) => void; reload: () => void }) {
  const [props, setProps] = useState<Prop[]>([]);
  const [confs, setConfs] = useState<Conf[]>([]);
  const [rec, setRec] = useState<Record<string, unknown> | null>(null);
  const load = useCallback(() => {
    apiClient.get("/api/v1/data-sync/proposals").then((r) => setProps(r.data)).catch(() => setProps([]));
    apiClient.get("/api/v1/data-sync/conflicts").then((r) => setConfs(r.data)).catch(() => setConfs([]));
  }, []);
  useEffect(() => { load(); }, [load]);
  const act = (p: Promise<unknown>, ok: string) => p.then(() => { msg(ok); load(); reload(); }).catch((e) => msg(err(e)));
  return (
    <section className="border rounded p-3 bg-white space-y-3" aria-label={tx("Approvals, conflicts and reconciliation")}>
      <h3 className="font-semibold">{tx("Order proposals (a second person approves)")}</h3>
      {props.length === 0 ? <p className="text-xs text-gray-500">{tx("Nothing is waiting.")}</p> : <ul className="text-xs divide-y">{props.map((p) => <li key={p.id} className="py-1 flex flex-wrap justify-between gap-2">
        <span>{p.target.replace("_", " ")} <b>{p.key}</b> · {p.payload.lines.length} {tx("line(s) ·")} {p.status.toLowerCase()} {tx("· proposed by")} {p.proposed_by ?? "?"}{p.error ? ` · ${p.error}` : ""}{p.applied_ref ? tx(" · draft created") : ""}</span>
        {p.status === "PENDING" && <span className="flex gap-2"><button className="underline" onClick={() => act(apiClient.post(`/api/v1/data-sync/proposals/${p.id}/approve`, { payload_hash: p.payload_hash }), tx("Approved: draft created."))}>{tx("Approve")}</button>
          <button className="underline" onClick={() => act(apiClient.post(`/api/v1/data-sync/proposals/${p.id}/reject`), "Rejected.")}>{tx("Reject")}</button></span>}</li>)}</ul>}
      <h3 className="font-semibold">{tx("Open conflicts (the ERP value was kept)")}</h3>
      {confs.length === 0 ? <p className="text-xs text-gray-500">{tx("None.")}</p> : <ul className="text-xs divide-y">{confs.map((c) => <li key={c.id} className="py-1 flex flex-wrap justify-between gap-2">
        <span>{c.target} <b>{c.key}</b> · {c.field}{tx(": ERP “")}{c.erp_value ?? "∅"}{tx("” vs source “")}{c.source_value ?? "∅"}”</span>
        <span className="flex gap-2"><button className="underline" onClick={() => act(apiClient.post(`/api/v1/data-sync/conflicts/${c.id}/resolve`, { resolution: "SOURCE" }), tx("Source value applied."))}>{tx("Use source")}</button>
          <button className="underline" onClick={() => act(apiClient.post(`/api/v1/data-sync/conflicts/${c.id}/resolve`, { resolution: "ERP" }), tx("Kept the ERP value."))}>{tx("Keep ERP")}</button></span></li>)}</ul>}
      <h3 className="font-semibold">{tx("Reconcile (read-only checks)")}</h3>
      <div className="flex gap-2"><button className="border rounded px-3 py-1 text-xs" onClick={() => apiClient.get("/api/v1/data-sync/reconcile/stock").then((r) => setRec({ stock: r.data })).catch((e) => msg(err(e)))}>{tx("Stock vs movement ledger")}</button>
        <button className="border rounded px-3 py-1 text-xs" onClick={() => apiClient.get("/api/v1/data-sync/reconcile/invoices").then((r) => setRec({ invoices: r.data })).catch((e) => msg(err(e)))}>{tx("Invoices vs general ledger")}</button></div>
      {rec && <pre className="text-xs bg-gray-50 p-2 overflow-auto max-h-48">{JSON.stringify(rec, null, 1)}</pre>}
    </section>
  );
}
