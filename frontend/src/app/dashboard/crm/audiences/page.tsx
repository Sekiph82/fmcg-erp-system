"use client";
// M44.S01.T010 dynamic audiences: rule builder, consent-aware membership, hashed export (off by default), local similarity.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type Cond = { field: string; op: string; value: string };
interface Audience { id: string; name: string; rules: { all: Cond[]; exclude: Cond[] }; require_consent: boolean;
  member_count: number; blocked_count: number; computed_at: string | null }
interface Similar { label: string; note?: string; candidates: { customer_id: string; name: string; score: number; reasons: string[] }[] }

const FIELDS = ["channel", "city", "country", "region", "segment", "customer_type", "lifecycle", "orders_90d", "days_since_last_order"];
const OPS: Record<string, string> = { eq: "is", ne: "is not", in: "is one of", not_in: "is none of", gte: "≥", lte: "≤", empty: "is empty", not_empty: "is set" };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Request failed."; };
const toApi = (c: Cond) => ({ field: c.field, op: c.op, value: c.op === "in" || c.op === "not_in" ? c.value.split(",").map((x) => x.trim()).filter(Boolean) : c.value });

function Rows({ label, rows, set }: { label: string; rows: Cond[]; set: (r: Cond[]) => void }) {
  const cls = "border rounded px-1 py-1 text-xs";
  const patch = (i: number, p: Partial<Cond>) => set(rows.map((r, j) => (j === i ? { ...r, ...p } : r)));
  return (
    <fieldset className="space-y-1"><legend className="text-xs font-semibold">{label}</legend>
      {rows.map((c, i) => (
        <div key={i} className="flex flex-wrap gap-1">
          <select aria-label="Field" className={cls} value={c.field} onChange={(e) => patch(i, { field: e.target.value })}>{FIELDS.map((f) => <option key={f}>{f}</option>)}</select>
          <select aria-label="Operator" className={cls} value={c.op} onChange={(e) => patch(i, { op: e.target.value })}>{Object.entries(OPS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
          {c.op !== "empty" && c.op !== "not_empty" && <input aria-label="Value" className={`${cls} flex-1 min-w-0`} placeholder={c.op.includes("in") ? "comma-separated" : "value"} value={c.value} onChange={(e) => patch(i, { value: e.target.value })} />}
          <button type="button" aria-label="Remove condition" className="text-red-600 text-xs" onClick={() => set(rows.filter((_, j) => j !== i))}>×</button>
        </div>))}
      <button type="button" className="text-xs underline" onClick={() => set([...rows, { field: "channel", op: "eq", value: "" }])}>+ condition</button>
    </fieldset>
  );
}

export default function AudiencesPage() {
  const [list, setList] = useState<Audience[]>([]);
  const [name, setName] = useState("");
  const [all, setAll] = useState<Cond[]>([{ field: "channel", op: "eq", value: "RETAIL" }]);
  const [exclude, setExclude] = useState<Cond[]>([]);
  const [consent, setConsent] = useState(true);
  const [pv, setPv] = useState<{ members: number; blocked: number; sample: string[] } | null>(null);
  const [sim, setSim] = useState<Similar | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => apiClient.get("/api/v1/audiences").then((r) => setList(r.data)).catch((e) => setMsg(err(e))), []);
  useEffect(() => { load(); }, [load]);
  const body = () => ({ name: name || "Preview", rules: { all: all.map(toApi), exclude: exclude.map(toApi) }, require_consent: consent });
  const run = async (fn: () => Promise<unknown>, ok?: string) => { setMsg(null); try { await fn(); if (ok) setMsg(ok); load(); } catch (e) { setMsg(err(e)); } };
  const download = async (a: Audience) => {
    const r = await apiClient.get(`/api/v1/audiences/${a.id}/export.csv`, { responseType: "blob" });
    const u = URL.createObjectURL(r.data);
    const l = document.createElement("a"); l.href = u; l.download = `audience-${a.name}.csv`; l.click(); URL.revokeObjectURL(u);
  };
  return (
    <div className="p-4 space-y-4 text-sm">
      <h2 className="text-lg font-semibold">Audiences</h2>
      <p className="text-xs text-gray-500">Rule-based lists recomputed from customer, CRM and order data. Only addresses with marketing consent become members; others are counted as blocked and never exported.</p>
      {msg && <p role="status" className="text-xs border rounded p-2 bg-gray-50">{msg}</p>}
      <form className="border rounded p-3 bg-white space-y-2" onSubmit={(e) => { e.preventDefault(); run(() => apiClient.post("/api/v1/audiences", body()), "Audience saved and computed."); }}>
        <input aria-label="Audience name" required placeholder="Audience name" className="border rounded px-2 py-1 w-full" value={name} onChange={(e) => setName(e.target.value)} />
        <Rows label="Include customers where ALL of these hold" rows={all} set={setAll} />
        <Rows label="Exclude customers where ANY of these hold" rows={exclude} set={setExclude} />
        <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} /> Members need marketing consent (recommended)</label>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="border rounded px-3 py-1 text-xs" onClick={() => run(async () => setPv((await apiClient.post("/api/v1/audiences/preview", body())).data))}>Preview</button>
          <button className="bg-indigo-600 text-white rounded px-3 py-1 text-xs">Save audience</button>
        </div>
        {pv && <p className="text-xs">{pv.members} members, {pv.blocked} matched but blocked (no consent or no e-mail).{pv.sample.length ? ` e.g. ${pv.sample.join(", ")}` : ""}</p>}
      </form>
      <div className="border rounded bg-white overflow-x-auto">
        <table className="min-w-full text-xs">
          <thead><tr className="text-left text-gray-500"><th className="p-2">Name</th><th>Members</th><th>Blocked</th><th>Computed</th><th /></tr></thead>
          <tbody>{list.map((a) => (
            <tr key={a.id} className="border-t"><td className="p-2">{a.name}</td><td>{a.member_count}</td><td>{a.blocked_count}</td>
              <td>{a.computed_at ? new Date(a.computed_at).toLocaleString() : "—"}</td>
              <td className="space-x-2 whitespace-nowrap pr-2 text-right">
                <button className="underline" onClick={() => run(() => apiClient.post(`/api/v1/audiences/${a.id}/recompute`), "Recomputed.")}>Recompute</button>
                <button className="underline" onClick={() => run(async () => setSim((await apiClient.get(`/api/v1/audiences/${a.id}/similar`)).data))}>Similar customers</button>
                <button className="underline" onClick={() => run(() => download(a))}>Hashed export</button>
                <button className="underline text-red-600" onClick={() => { if (confirm(`Delete audience ${a.name}?`)) run(() => apiClient.delete(`/api/v1/audiences/${a.id}`), "Deleted."); }}>Delete</button>
              </td></tr>))}</tbody>
        </table>
        {list.length === 0 && <p className="p-2 text-xs text-gray-500">No audiences yet.</p>}
      </div>
      {sim && <div className="border rounded p-3 bg-white space-y-1"><h3 className="font-semibold">Similar customers <span className="text-xs font-normal text-gray-500">({sim.label})</span></h3>
        {sim.note && <p className="text-xs text-gray-500">{sim.note}</p>}
        <ul className="text-xs space-y-1">{sim.candidates.map((c) => <li key={c.customer_id}><b>{c.name}</b> — {c.score} · {c.reasons.join("; ")}</li>)}</ul></div>}
    </div>
  );
}
