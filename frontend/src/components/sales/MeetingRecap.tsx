"use client";
// M47.S01.T009 meeting prep brief (stored facts) and recap from a transcript; follow-up tasks only on approval.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type Item = { quote: string; owner?: string | null; speaker?: string | null; due_in_days?: number | null };
type Recap = { status: string; engine?: string; recap?: { decisions: Item[]; action_items: Item[] }; task_ids?: string[] };
type Brief = { open_deals: { id: string; name: string; expected_revenue: string; currency: string }[];
  last_orders: { order_no: string; date: string; net_total: string; currency: string; status: string }[];
  open_tickets: { ticket_no: string; subject: string; status: string }[]; hidden: string[]; note?: string };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };

export function MeetingRecap({ meetingId, canChange }: { meetingId: string; canChange: boolean }) {
  const [brief, setBrief] = useState<Brief | null>(null);
  const [recap, setRecap] = useState<Recap | null>(null);
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [pick, setPick] = useState<number[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const base = `/api/v1/sales-depth/meetings/${meetingId}`;
  const load = useCallback(() => {
    apiClient.get(`${base}/brief`).then((r) => setBrief(r.data)).catch(() => setBrief(null));
    apiClient.get(`${base}/recap`).then((r) => setRecap(r.data)).catch(() => setRecap(null));
  }, [base]);
  useEffect(() => { load(); }, [load]);
  const [consented, setConsented] = useState(false);
  const upload = () => {
    const f = new FormData();
    if (file) f.append("file", file); else f.append("text", text);
    f.append("participants_consented", consented ? "true" : "false");   // M47.S01.T003 consent before transcription/AI
    apiClient.post(`${base}/transcript`, f).then((r) => { setRecap(r.data); setPick([]); setMsg(null); }).catch((e) => setMsg(err(e)));
  };
  const approve = () => apiClient.post(`${base}/recap/approve`, { action_items: pick })
    .then((r) => { setRecap(r.data); setMsg(`Recap approved; ${r.data.task_ids.length} follow-up task(s) created.`); }).catch((e) => setMsg(err(e)));
  return (
    <div className="mt-3 border-t pt-3 grid md:grid-cols-2 gap-3 text-xs">
      <div>
        <b>Prep brief (stored facts only)</b>
        {!brief ? <p className="text-gray-500">No brief.</p> : <>
          {brief.note && <p className="text-gray-500">{brief.note}</p>}
          <p>Open deals: {brief.open_deals.map((d) => `${d.name} (${d.currency} ${d.expected_revenue})`).join("; ") || "none"}</p>
          <p>Last orders: {brief.last_orders.map((o) => `${o.order_no} ${o.date} ${o.currency} ${o.net_total}`).join("; ") || "none"}</p>
          <p>Open tickets: {brief.open_tickets.map((t) => `${t.ticket_no} ${t.subject}`).join("; ") || "none"}</p>
          {brief.hidden.length > 0 && <p className="text-gray-500">Not shown (no permission): {brief.hidden.join(", ")}</p>}
        </>}
      </div>
      <div className="space-y-1">
        <b>Recap</b>
        {recap?.recap && <>
          <p className="text-gray-500">{recap.status === "APPROVED" ? "Approved" : "Draft"} · {recap.engine === "ai" ? "AI (quotes checked)" : "rules"}</p>
          <p>Decisions: {recap.recap.decisions.map((d) => `“${d.quote}”`).join(" ") || "none found"}</p>
          <ul>{recap.recap.action_items.map((a, i) => (
            <li key={i}><label className="flex gap-1 items-start">
              {recap.status !== "APPROVED" && canChange && <input type="checkbox" checked={pick.includes(i)} onChange={(e) => setPick(e.target.checked ? [...pick, i] : pick.filter((x) => x !== i))} />}
              “{a.quote}”{a.owner ? ` — ${a.owner}` : ""}{a.due_in_days != null ? ` (in ${a.due_in_days} d)` : ""}</label></li>))}</ul>
          {recap.status !== "APPROVED" && canChange && <button className="border rounded px-2 py-1" onClick={approve}>Approve and create {pick.length} task(s)</button>}
        </>}
        {canChange && recap?.status !== "APPROVED" && <div className="space-y-1">
          <textarea className="border rounded w-full px-2 py-1" rows={3} placeholder="Paste the transcript…" value={text} onChange={(e) => setText(e.target.value)} />
          <input type="file" accept=".txt,.vtt,audio/*" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <label className="flex items-center gap-1"><input type="checkbox" checked={consented} onChange={(e) => setConsented(e.target.checked)} />All participants agreed to recording and transcription (needed for audio and AI)</label>
          <button className="border rounded px-2 py-1" onClick={upload}>Build recap</button>
        </div>}
        {msg && <p role="status">{msg}</p>}
      </div>
    </div>
  );
}
