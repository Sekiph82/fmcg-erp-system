"use client";
// M36.S03.T005 staff view of a website chat: transcript, reply, close.
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { crmApi, type ChatTranscript } from "@/lib/crm_pipeline";

export default function CRMChatPage() {
  const { id } = useParams<{ id: string }>();
  const [t, setT] = useState<ChatTranscript | null>(null);
  const [reply, setReply] = useState("");
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => crmApi.getChat(id).then(setT).catch(() => setError("Chat not found or not visible to you.")), [id]);
  useEffect(() => { load(); const i = setInterval(load, 5000); return () => clearInterval(i); }, [load]);

  async function act(fn: () => Promise<unknown>) {
    setError(null);
    try { await fn(); await load(); } catch (e) {
      const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
      setError(typeof d === "string" ? d : "Request failed.");
    }
  }
  if (!t) return <div className="p-6 text-sm text-gray-500">{error ?? "Loading…"}</div>;
  return (
    <div className="p-6 space-y-4 max-w-3xl">
      <div>
        <Link href="/dashboard/crm?tab=inbox" className="text-xs text-indigo-600">← Inbox</Link>
        <h1 className="text-xl font-bold text-gray-900">Website chat · {t.visitor_name || t.visitor_email || "visitor"}</h1>
        <p className="text-sm text-gray-500">
          {t.status === "CLOSED" ? "Closed" : t.status === "WAITING" ? "Waiting for our team" : "With the bot"}
          {t.visitor_email && ` · ${t.visitor_email}${t.consent_given ? " (agreed to be contacted)" : ""}`}
          {t.crm_record_id && <> · <Link className="underline" href={`/dashboard/crm/records/${t.crm_record_id}`}>lead</Link></>}
          {t.page_url && ` · from ${t.page_url}`}
        </p>
      </div>
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      <div className="bg-white rounded-xl border p-3 space-y-2 max-h-[60vh] overflow-y-auto">
        {t.messages.map((m) => (
          <div key={m.id} className={`text-sm rounded-lg p-2 w-fit max-w-[85%] whitespace-pre-wrap ${m.from === "visitor" ? "bg-gray-100" : m.from === "agent" ? "bg-indigo-50 ml-auto" : "bg-gray-50 text-gray-600"}`}>
            <span className="block text-xs text-gray-500">{m.from === "visitor" ? "Visitor" : m.from === "agent" ? "Our team" : "Bot"} · {new Date(m.at).toLocaleString()}</span>
            {m.body}
          </div>
        ))}
      </div>
      {t.status !== "CLOSED" && (
        <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); if (reply.trim()) act(() => crmApi.replyChat(id, reply.trim()).then(() => setReply(""))); }}>
          <input aria-label="Reply" value={reply} maxLength={2000} onChange={(e) => setReply(e.target.value)} placeholder="Write a reply" className="flex-1 min-w-[12rem] border rounded-lg px-3 py-2 text-sm" />
          <button className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm">Send</button>
          <button type="button" onClick={() => act(() => crmApi.closeChat(id))} className="px-4 py-2 rounded-lg border text-sm">Close chat</button>
        </form>
      )}
    </div>
  );
}
