"use client";
// M43.S01.T013 sales workspace: today's queue, deals without a next step, deal summary, send-time hint,
// snippets, signatures and rep productivity.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { ContractImport, QuoteDraftFromDeal } from "@/components/sales/CPQPanel";
import { DealWin, TaskCalendarSync, VideoMessages } from "@/components/sales/SalesDepth";

interface Task { id: string; record_id: string; subject: string; queue: string | null; type: string; due: string | null; overdue: boolean; repeats: string | null }
interface Today { queues: string[]; tasks: Task[]; deals_without_next_step: { id: string; company_name: string }[] }
interface Prod { user_id: string; name: string; activities: number; calls: number; meetings: number; emails: number;
  won: Record<string, { deals: number; value: number }> }

const iso = (d: Date) => d.toISOString().slice(0, 10);

export default function CRMWorkspacePage() {
  const [queue, setQueue] = useState("");
  const [today, setToday] = useState<Today | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [hint, setHint] = useState<string | null>(null);
  const [snips, setSnips] = useState<{ id: string; name: string; body: string; shared: boolean }[]>([]);
  const [sigs, setSigs] = useState<{ id: string; name: string; is_default: boolean }[]>([]);
  const [snip, setSnip] = useState({ name: "", body: "" });
  const [sig, setSig] = useState({ name: "", body: "", is_default: true });
  const [prod, setProd] = useState<Prod[]>([]);
  const load = useCallback(() => {
    apiClient.get("/api/v1/crm-workspace/today", { params: { queue: queue || undefined } }).then((r) => setToday(r.data)).catch(() => setToday(null));
    apiClient.get("/api/v1/crm-workspace/snippets").then((r) => setSnips(r.data)).catch(() => setSnips([]));
    apiClient.get("/api/v1/crm-workspace/signatures").then((r) => setSigs(r.data)).catch(() => setSigs([]));
    const until = new Date(), since = new Date(Date.now() - 30 * 864e5);
    apiClient.get("/api/v1/crm-workspace/productivity", { params: { since: iso(since), until: iso(until) } }).then((r) => setProd(r.data)).catch(() => setProd([]));
  }, [queue]);
  useEffect(() => { load(); }, [load]);
  const sum = async (id: string) => { setSel(id); try { setSummary((await apiClient.get(`/api/v1/crm-workspace/records/${id}/summary`)).data.summary); } catch { setSummary(null); } };

  return (
    <div className="p-4 grid lg:grid-cols-3 gap-4 text-sm">
      <section className="lg:col-span-2 space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold">My work today</h2>
          <select aria-label="Queue" className="border rounded px-2 py-1 text-xs" value={queue} onChange={(e) => setQueue(e.target.value)}>
            <option value="">All queues</option>{today?.queues.map((q) => <option key={q}>{q}</option>)}</select>
        </div>
        <ul className="border rounded bg-white divide-y">
          {today?.tasks.map((t) => (
            <li key={t.id} className="px-3 py-2 flex flex-wrap justify-between gap-2">
              <button className="text-left" onClick={() => sum(t.record_id)}>
                <span className={t.overdue ? "text-red-600" : ""}>{t.subject}</span>
                <span className="text-xs text-gray-500"> · {t.type.toLowerCase()}{t.queue ? ` · ${t.queue}` : ""}{t.repeats ? ` · repeats ${t.repeats.toLowerCase()}` : ""}</span>
              </button>
              <span className="text-xs text-gray-500">{t.due ? new Date(t.due).toLocaleString() : "no due date"}</span>
            </li>))}
          {today && today.tasks.length === 0 && <li className="px-3 py-2 text-xs text-gray-500">Nothing due. </li>}
        </ul>
        {today && today.deals_without_next_step.length > 0 && (
          <div className="border border-amber-200 bg-amber-50 rounded p-2 text-xs">
            <b>Open deals with no next step:</b> {today.deals_without_next_step.map((d, i) => (
              <button key={d.id} className="underline ml-1" onClick={() => sum(d.id)}>{d.company_name}{i < today.deals_without_next_step.length - 1 ? "," : ""}</button>))}
          </div>)}
        {summary && <p className="border rounded bg-white p-2 text-xs"><b>Deal summary (from stored facts):</b> {summary}</p>}
        <div>
          <h3 className="font-semibold">Team activity, last 30 days</h3>
          <div className="overflow-x-auto"><table className="min-w-full text-xs"><thead><tr className="text-left text-gray-500"><th className="pr-3">Person</th><th>Tasks done</th><th>Calls</th><th>Meetings</th><th>E-mails</th><th>Won</th></tr></thead>
            <tbody>{prod.map((p) => <tr key={p.user_id} className="border-t"><td className="pr-3">{p.name}</td><td>{p.activities}</td><td>{p.calls}</td><td>{p.meetings}</td><td>{p.emails}</td>
              <td>{Object.entries(p.won).map(([c, w]) => `${w.deals} · ${c} ${w.value.toLocaleString()}`).join("; ") || "—"}</td></tr>)}</tbody></table></div>
        </div>
      </section>
      <section className="space-y-3">
        <TaskCalendarSync />
        <DealWin recordId={sel} />
        {sel && <QuoteDraftFromDeal recordId={sel} />}
        <VideoMessages recordId={sel} />
        <ContractImport />
        <div className="border rounded bg-white p-2 space-y-1">
          <div className="font-semibold text-xs">Best time to e-mail</div>
          <form className="flex gap-1" onSubmit={async (e) => { e.preventDefault(); try { setHint((await apiClient.get("/api/v1/crm-workspace/send-time", { params: { email } })).data.reason); } catch { setHint(null); } }}>
            <input type="email" required className="border rounded px-2 py-1 text-xs flex-1" placeholder="contact e-mail" value={email} onChange={(e) => setEmail(e.target.value)} />
            <button className="text-xs border rounded px-2">Check</button></form>
          {hint && <p className="text-xs text-gray-700">{hint}</p>}
        </div>
        <div className="border rounded bg-white p-2 space-y-1 text-xs">
          <div className="font-semibold">Snippets</div>
          {snips.map((s) => <button key={s.id} className="block text-left w-full hover:bg-gray-50" title="Copy" onClick={() => navigator.clipboard?.writeText(s.body)}>{s.name}{s.shared ? " (shared)" : ""}</button>)}
          <form className="space-y-1" onSubmit={async (e) => { e.preventDefault(); await apiClient.post("/api/v1/crm-workspace/snippets", snip).catch(() => null); setSnip({ name: "", body: "" }); load(); }}>
            <input required className="border rounded px-2 py-1 w-full" placeholder="Name" value={snip.name} onChange={(e) => setSnip({ ...snip, name: e.target.value })} />
            <textarea required className="border rounded px-2 py-1 w-full" rows={2} placeholder="Text" value={snip.body} onChange={(e) => setSnip({ ...snip, body: e.target.value })} />
            <button className="border rounded px-2">Add snippet</button></form>
        </div>
        <div className="border rounded bg-white p-2 space-y-1 text-xs">
          <div className="font-semibold">My signatures</div>
          {sigs.map((s) => <div key={s.id}>{s.name}{s.is_default ? " (default)" : ""}</div>)}
          <form className="space-y-1" onSubmit={async (e) => { e.preventDefault(); await apiClient.post("/api/v1/crm-workspace/signatures", sig).catch(() => null); setSig({ name: "", body: "", is_default: true }); load(); }}>
            <input required className="border rounded px-2 py-1 w-full" placeholder="Name" value={sig.name} onChange={(e) => setSig({ ...sig, name: e.target.value })} />
            <textarea required className="border rounded px-2 py-1 w-full" rows={2} placeholder="Signature text" value={sig.body} onChange={(e) => setSig({ ...sig, body: e.target.value })} />
            <label className="flex gap-1 items-center"><input type="checkbox" checked={sig.is_default} onChange={(e) => setSig({ ...sig, is_default: e.target.checked })} /> Default</label>
            <button className="border rounded px-2">Add signature</button></form>
        </div>
      </section>
    </div>
  );
}
