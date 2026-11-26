"use client";
// Conversation insights (M36.S05.T004): objections, questions, themes and next steps quoted from consented calls and
// staff-handled chats; managers review with a coaching note. No made-up scores — only quoted findings.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

interface Finding { kind: string; label: string; quote: string; offset: number }
interface Insight { id: string; source_type: string; source_id: string; findings: Finding[]; counts: Record<string, number>; engine: string; status: string; coaching_note: string | null; analysed_at: string | null }
const KIND: Record<string, string> = { objection: "Objection", theme: "Theme", question: "Question", next_step: "Next step" };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail; return typeof d === "string" ? d : "Request failed."; };

export default function ConversationInsights() {
  const [items, setItems] = useState<Insight[]>([]);
  const [byType, setByType] = useState<Record<string, number>>({});
  const [status, setStatus] = useState("PENDING_REVIEW");
  const [open, setOpen] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const load = useCallback(() => apiClient.get<{ items: Insight[]; objections_by_type: Record<string, number> }>("/api/v1/conversation-intel", { params: { status: status || undefined } })
    .then((r) => { setItems(r.data.items); setByType(r.data.objections_by_type); }).catch((e) => setMsg({ ok: false, text: err(e) })), [status]);
  useEffect(() => { load(); }, [load]);
  const review = async (id: string, s: "REVIEWED" | "REJECTED") => {
    try { await apiClient.post(`/api/v1/conversation-intel/${id}/review`, { status: s, coaching_note: note || null }); setNote(""); setMsg({ ok: true, text: tx("Review saved.") }); load(); }
    catch (e) { setMsg({ ok: false, text: err(e) }); }
  };
  return (
    <div className="p-4 sm:p-6 space-y-4">
      <div><h1 className="text-xl font-bold text-gray-900">{tx("Conversation insights")}</h1>
        <p className="text-xs text-gray-500">{tx("Only calls with recording consent and chats handled by a person. Every finding is a quote from the conversation.")}</p></div>
      {msg && <p role="status" className={`text-sm rounded px-3 py-2 ${msg.ok ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-700"}`}>{msg.text}</p>}
      <div className="flex flex-wrap gap-2 items-center text-sm">
        <select aria-label={tx("Status")} value={status} onChange={(e) => setStatus(e.target.value)} className="border rounded px-2 py-1.5">
          <option value="PENDING_REVIEW">{tx("Waiting for review")}</option><option value="REVIEWED">{tx("Reviewed")}</option><option value="REJECTED">{tx("Rejected")}</option><option value="">{tx("All")}</option></select>
        {Object.entries(byType).map(([k, n]) => <span key={k} className="rounded-full bg-amber-50 text-amber-800 px-2 py-0.5 text-xs">{k}: {n}</span>)}
      </div>
      {items.length === 0 ? <p className="text-sm text-gray-500 bg-white border rounded-xl p-4">{tx("Nothing here yet. Analyse a consented call from the Calls list.")}</p> : items.map((i) => (
        <div key={i.id} className="bg-white border rounded-xl">
          <button onClick={() => setOpen(open === i.id ? null : i.id)} aria-expanded={open === i.id} className="w-full text-left p-3 flex justify-between gap-2 text-sm">
            <span>{i.source_type === "call" ? tx("Call") : tx("Chat")} · {i.analysed_at ? new Date(i.analysed_at).toLocaleString() : ""}
              <span className="block text-xs text-gray-500">{Object.entries(i.counts).map(([k, n]) => `${n} ${KIND[k]?.toLowerCase() ?? k}${n === 1 ? "" : "s"}`).join(" · ")} · {i.engine}</span></span>
            <span className="text-xs">{i.status.replace("_", " ").toLowerCase()}</span>
          </button>
          {open === i.id && (
            <div className="px-3 pb-3 space-y-2 text-sm">
              <ul className="space-y-1">{i.findings.map((f, n) => <li key={n}><span className="text-xs font-semibold text-gray-600">{KIND[f.kind] ?? f.kind} · {f.label}</span><blockquote className="border-l-2 pl-2 text-gray-800">“{f.quote}”</blockquote></li>)}</ul>
              {i.coaching_note && <p className="text-xs text-emerald-800">{tx("Coaching:")} {i.coaching_note}</p>}
              {i.status === "PENDING_REVIEW" && (<>
                <textarea aria-label={tx("Coaching note")} placeholder={tx("Coaching note for the rep (optional)")} rows={2} value={note} onChange={(e) => setNote(e.target.value)} className="w-full border rounded px-2 py-1.5" />
                <div className="flex gap-2"><button onClick={() => review(i.id, "REVIEWED")} className="rounded bg-emerald-600 text-white px-3 py-1.5 text-xs">{tx("Reviewed")}</button>
                  <button onClick={() => review(i.id, "REJECTED")} className="rounded border px-3 py-1.5 text-xs">{tx("Not useful")}</button></div>
              </>)}
            </div>)}
        </div>))}
    </div>
  );
}
