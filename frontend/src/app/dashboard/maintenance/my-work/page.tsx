"use client";
// Technician "My Jobs" (M40.S01.T002): the PM work orders and breakdowns assigned to me — start, log spare parts,
// add photos and complete with notes. Phone first.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { EntityPicker } from "@/components/EntityPicker";

interface WO { id: string; wo_no: string; status: string; scheduled_date: string; started_at: string | null; plan: string | null;
  checklist: string | null; asset: string; asset_no: string; photos: number }
interface BD { id: string; breakdown_no: string; status: string; severity: string; reason: string; since: string; asset: string; asset_no: string; photos: number }
type Job = { kind: "work-orders"; row: WO } | { kind: "breakdowns"; row: BD };

const err = (e: unknown) => {
  const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof d === "string" ? d : (d as { message?: string })?.message ?? "Something went wrong.";
};

export default function MyJobs() {
  const [data, setData] = useState<{ work_orders: WO[]; breakdowns: BD[] } | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const load = useCallback(() => apiClient.get("/api/v1/maintenance/my-work").then((r) => setData(r.data)).catch((e) => setMsg({ ok: false, text: err(e) })), []);
  useEffect(() => { load(); }, [load]);

  const jobs: Job[] = data ? [...data.breakdowns.map((row) => ({ kind: "breakdowns" as const, row })), ...data.work_orders.map((row) => ({ kind: "work-orders" as const, row }))] : [];
  return (
    <div className="p-4 sm:p-6 max-w-2xl mx-auto space-y-3">
      <div>
        <h1 className="text-xl font-bold text-gray-900">My Jobs</h1>
        <p className="text-xs text-gray-500">Breakdowns first, then planned maintenance assigned to you.</p>
      </div>
      {msg && <p role="status" className={`text-sm rounded px-3 py-2 ${msg.ok ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-700"}`}>{msg.text}</p>}
      {!data ? <p className="text-sm text-gray-500">Loading…</p> : jobs.length === 0 ? (
        <p className="text-sm text-gray-500 bg-white border rounded-xl p-4">No jobs assigned to you right now.</p>
      ) : jobs.map((j) => (
        <JobCard key={j.row.id} job={j} open={open === j.row.id} onToggle={() => setOpen(open === j.row.id ? null : j.row.id)}
          onDone={(text) => { setMsg({ ok: true, text }); load(); }} onFail={(text) => setMsg({ ok: false, text })} />
      ))}
    </div>
  );
}

function JobCard({ job, open, onToggle, onDone, onFail }: { job: Job; open: boolean; onToggle: () => void; onDone: (t: string) => void; onFail: (t: string) => void }) {
  const r = job.row;
  const isBd = job.kind === "breakdowns";
  const base = `/api/v1/maintenance/my-work/${job.kind}/${r.id}`;
  const started = isBd ? r.status === "IN_REPAIR" : r.status === "IN_PROGRESS";
  const [notes, setNotes] = useState("");
  const [cause, setCause] = useState("");
  const [spare, setSpare] = useState({ id: "", qty: "1" });
  const [busy, setBusy] = useState(false);
  const run = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true);
    try { await fn(); onDone(ok); } catch (e) { onFail(err(e)); } finally { setBusy(false); }
  };
  const title = isBd ? (r as BD).breakdown_no : (r as WO).wo_no;
  return (
    <div className={`bg-white border rounded-xl ${isBd ? "border-red-200" : ""}`}>
      <button onClick={onToggle} aria-expanded={open} className="w-full text-left p-3 flex justify-between gap-2">
        <span className="min-w-0">
          <span className="block font-medium text-gray-900">{isBd ? "Breakdown" : (r as WO).plan ?? "Planned maintenance"} — {r.asset}</span>
          <span className="block text-xs text-gray-500">{title} · {r.asset_no} · {isBd ? `${(r as BD).severity.toLowerCase()} · since ${new Date((r as BD).since).toLocaleString()}` : `due ${(r as WO).scheduled_date}`}</span>
        </span>
        <span className={`shrink-0 text-xs rounded-full px-2 py-0.5 h-fit ${started ? "bg-amber-100 text-amber-800" : "bg-gray-100 text-gray-700"}`}>{r.status.replace("_", " ").toLowerCase()}</span>
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-3 text-sm">
          {isBd ? <p className="text-gray-700">{(r as BD).reason}</p> : (r as WO).checklist && (
            <ul className="list-disc pl-5 text-gray-700">{(r as WO).checklist!.split("\n").filter(Boolean).map((c, i) => <li key={i}>{c}</li>)}</ul>
          )}
          {!started ? (
            <button disabled={busy} onClick={() => run(() => apiClient.post(`${base}/start`), `${title} started.`)}
              className="w-full py-2.5 rounded-lg bg-blue-600 text-white disabled:opacity-50">Start job</button>
          ) : (<>
            <div className="grid grid-cols-[1fr_5rem_auto] gap-2 items-end">
              <div><label className="block text-xs text-gray-500 mb-1">Spare part used</label>
                <EntityPicker kind="spare_part" label="Spare part" value={spare.id} onChange={(id) => setSpare({ ...spare, id })} /></div>
              <div><label className="block text-xs text-gray-500 mb-1">Qty</label>
                <input aria-label="Quantity" type="number" min="0.0001" step="any" value={spare.qty} onChange={(e) => setSpare({ ...spare, qty: e.target.value })} className="w-full border rounded px-2 py-2 text-sm" /></div>
              <button disabled={busy || !spare.id} onClick={() => run(() => apiClient.post(`${base}/spares`, { spare_part_id: spare.id, quantity: spare.qty }).then(() => setSpare({ id: "", qty: "1" })), "Spare part recorded.")}
                className="py-2 px-3 rounded-lg border text-sm disabled:opacity-50">Add</button>
            </div>
            <label className="block text-xs text-gray-500">Photo ({r.photos}/10)
              <input type="file" accept="image/jpeg,image/png" capture="environment" disabled={busy} className="block mt-1 text-sm"
                onChange={(e) => { const f = e.target.files?.[0]; if (!f) return; const fd = new FormData(); fd.append("file", f);
                  run(() => apiClient.post(`${base}/photo`, fd), "Photo added."); e.target.value = ""; }} />
            </label>
            {isBd ? (<>
              <textarea aria-label="Root cause" placeholder="Root cause" value={cause} onChange={(e) => setCause(e.target.value)} rows={2} className="w-full border rounded-lg px-3 py-2" />
              <textarea aria-label="What was done" placeholder="What was done to fix it" value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} className="w-full border rounded-lg px-3 py-2" />
              <button disabled={busy || cause.trim().length < 3 || notes.trim().length < 3}
                onClick={() => run(() => apiClient.post(`${base}/resolve`, { root_cause: cause, corrective_action: notes }), `${title} resolved.`)}
                className="w-full py-2.5 rounded-lg bg-emerald-600 text-white disabled:opacity-50">Machine fixed — close breakdown</button>
            </>) : (<>
              <textarea aria-label="Completion notes" placeholder="What was done, readings, anything to follow up" value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} className="w-full border rounded-lg px-3 py-2" />
              <button disabled={busy || notes.trim().length < 3} onClick={() => run(() => apiClient.post(`${base}/complete`, { notes }), `${title} completed.`)}
                className="w-full py-2.5 rounded-lg bg-emerald-600 text-white disabled:opacity-50">Complete job</button>
            </>)}
          </>)}
        </div>
      )}
    </div>
  );
}
