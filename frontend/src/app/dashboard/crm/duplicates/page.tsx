"use client";
// M45.S01.T010 bulk duplicate review: candidates with reasons, merge preview, merge, dismiss, history with undo.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type Pair = { a_id: string; b_id: string; a: string; b: string; score: number; reasons: string[] };
type Preview = { survivor: string; merged: string; moves: { table: string; column: string; rows: number }[]; fills: Record<string, string>; consent: { email: string; before: string | null; after: string } | null; merged_record: string };
type Merge = { id: string; entity: string; merged_by: string; merged_at: string; reason: string | null; moved: { table: string; rows: number }[]; undone_by: string | null };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };

export default function DuplicatesPage() {
  const [entity, setEntity] = useState<"customer" | "contact">("customer");
  const [pairs, setPairs] = useState<Pair[] | null>(null);
  const [pick, setPick] = useState<{ pair: Pair; keep: "a" | "b"; preview: Preview | null } | null>(null);
  const [reason, setReason] = useState("");
  const [hist, setHist] = useState<Merge[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => {
    setPairs(null);
    apiClient.get("/api/v1/dedupe/candidates", { params: { entity } }).then((r) => setPairs(r.data)).catch((e) => { setPairs([]); setMsg(err(e)); });
    apiClient.get("/api/v1/dedupe/merges").then((r) => setHist(r.data)).catch(() => setHist([]));
  }, [entity]);
  useEffect(() => { load(); }, [load]);
  const ids = (p: Pair, keep: "a" | "b") => ({ entity, survivor_id: keep === "a" ? p.a_id : p.b_id, merged_id: keep === "a" ? p.b_id : p.a_id });
  const preview = (pair: Pair, keep: "a" | "b") => apiClient.post("/api/v1/dedupe/preview", ids(pair, keep)).then((r) => setPick({ pair, keep, preview: r.data })).catch((e) => setMsg(err(e)));
  const merge = () => pick && apiClient.post("/api/v1/dedupe/merge", { ...ids(pick.pair, pick.keep), reason }).then(() => { setMsg("Merged. You can undo it below."); setPick(null); setReason(""); load(); }).catch((e) => setMsg(err(e)));
  const dismiss = (p: Pair) => apiClient.post("/api/v1/dedupe/dismiss", ids(p, "a")).then(load).catch((e) => setMsg(err(e)));
  const undo = (id: string) => apiClient.post(`/api/v1/dedupe/merges/${id}/undo`).then(() => { setMsg("Merge undone."); load(); }).catch((e) => setMsg(err(e)));

  return (
    <div className="p-4 space-y-4 text-sm">
      <div className="flex flex-wrap gap-2 items-center justify-between">
        <h2 className="text-lg font-semibold">Duplicates</h2>
        <select aria-label="Record type" className="border rounded px-2 py-1" value={entity} onChange={(e) => setEntity(e.target.value as "customer" | "contact")}>
          <option value="customer">Customers</option><option value="contact">Contacts</option></select>
      </div>
      {msg && <p role="status" className="text-xs">{msg}</p>}
      {pairs === null ? <p className="text-gray-500">Looking for duplicates…</p> : pairs.length === 0 ? <p className="text-gray-500">No likely duplicates.</p> :
        <ul className="divide-y bg-white border rounded">{pairs.map((p) => <li key={p.a_id + p.b_id} className="p-2 text-xs space-y-1">
          <div className="flex flex-wrap justify-between gap-2"><span><b>{p.a}</b> ↔ <b>{p.b}</b></span><span>{Math.round(p.score * 100)}% · {p.reasons.join(", ")}</span></div>
          <div className="flex flex-wrap gap-3"><button className="underline" onClick={() => preview(p, "a")}>Keep first…</button><button className="underline" onClick={() => preview(p, "b")}>Keep second…</button>
            <button className="underline text-gray-500" onClick={() => dismiss(p)}>Not duplicates</button></div></li>)}</ul>}
      {pick?.preview && <section className="border rounded p-3 bg-amber-50 space-y-2 text-xs">
        <h3 className="font-semibold text-sm">Merge {pick.preview.merged} into {pick.preview.survivor}</h3>
        <p>Moves to the kept record: {pick.preview.moves.length === 0 ? "nothing" : pick.preview.moves.map((m) => `${m.table} (${m.rows})`).join(", ")}.</p>
        {Object.keys(pick.preview.fills).length > 0 && <p>Fills empty fields: {Object.entries(pick.preview.fills).map(([k, v]) => `${k} = ${v}`).join(", ")}.</p>}
        {pick.preview.consent && <p>E-mail consent for {pick.preview.consent.email}: {pick.preview.consent.before ?? "none"} → <b>{pick.preview.consent.after}</b> (the stricter one wins).</p>}
        <p>The other record is {pick.preview.merged_record}. Everything is logged and can be undone.</p>
        <input aria-label="Reason" className="border rounded px-2 py-1 w-full" placeholder="Reason (optional)" value={reason} onChange={(e) => setReason(e.target.value)} />
        <div className="flex gap-2"><button className="bg-indigo-600 text-white rounded px-3 py-1" onClick={merge}>Merge</button><button className="border rounded px-3 py-1" onClick={() => setPick(null)}>Cancel</button></div>
      </section>}
      <section className="space-y-1"><h3 className="font-semibold">Merge history</h3>
        <ul className="text-xs divide-y bg-white border rounded">{hist.map((m) => <li key={m.id} className="p-2 flex flex-wrap justify-between gap-2">
          <span>{m.entity} · {new Date(m.merged_at).toLocaleString()} by {m.merged_by}{m.reason ? ` · ${m.reason}` : ""} · moved {m.moved.map((x) => `${x.table} ${x.rows}`).join(", ") || "nothing"}</span>
          {m.undone_by ? <span className="text-gray-500">undone by {m.undone_by}</span> : <button className="underline" onClick={() => undo(m.id)}>Undo</button>}</li>)}</ul></section>
    </div>
  );
}
