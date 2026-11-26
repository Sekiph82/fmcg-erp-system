"use client";
// M44.S01.T013 Messenger / Instagram DM / custom channel thread from the unified inbox: messages and reply.
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { apiClient } from "@/lib/api";
import { tx, lx } from "@/lib/i18n/core";

interface Msg { id: string; direction: "IN" | "OUT"; sender: string | null; body: string; status: string; at: string }
interface Thread { id: string; channel: string; subject: string; status: string; messages: Msg[] }
const LABEL: Record<string, string> = lx(() => ({ MESSENGER: tx("Messenger"), INSTAGRAM: tx("Instagram DM"), CUSTOM: tx("Custom channel") }));
const STATUS: Record<string, string> = { QUEUED: "waiting for the channel to fetch it", DELIVERED: "fetched by the channel", FAILED: "failed" };

export default function ChannelThreadPage() {
  const { id } = useParams<{ id: string }>();
  const [t, setT] = useState<Thread | null>(null);
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => apiClient.get<Thread>(`/api/v1/crm-channels/conversations/${id}`).then((r) => setT(r.data))
    .catch(() => setError(tx("Conversation not found or not visible to you."))), [id]);
  useEffect(() => { load(); const i = setInterval(load, 10000); return () => clearInterval(i); }, [load]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setError(null);
    try {
      await apiClient.post(`/api/v1/crm-channels/conversations/${id}/reply`, { text: text.trim() });
      setText("");
      await load();
    } catch (err) {
      const d = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
      setError(typeof d === "string" ? d : tx("Sending failed."));
    }
  }
  if (!t) return <div className="p-6 text-sm text-gray-500">{error ?? tx("Loading…")}</div>;
  return (
    <div className="p-4 sm:p-6 space-y-4 max-w-3xl">
      <div>
        <Link href="/dashboard/crm?tab=inbox" className="text-xs text-indigo-600">{tx("← Inbox")}</Link>
        <h1 className="text-xl font-bold text-gray-900 break-words">{t.subject}</h1>
        <p className="text-sm text-gray-500">{LABEL[t.channel] ?? t.channel} · {t.status.toLowerCase()}
          {t.channel !== "CUSTOM" && tx(" · replies are possible within 24 hours of the customer's last message (Meta rule)")}</p>
      </div>
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      <div className="bg-white rounded-xl border p-3 space-y-2 max-h-[60vh] overflow-y-auto">
        {t.messages.map((m) => (
          <div key={m.id} className={`text-sm rounded-lg p-2 w-fit max-w-[85%] whitespace-pre-wrap break-words ${m.direction === "IN" ? "bg-gray-100" : "bg-indigo-50 ml-auto"}`}>
            <span className="block text-xs text-gray-500">{m.direction === "IN" ? (m.sender || tx("Customer")) : tx("Our team")} · {new Date(m.at).toLocaleString()}
              {STATUS[m.status] && ` · ${STATUS[m.status]}`}</span>
            {m.body}
          </div>
        ))}
        {!t.messages.length && <p className="text-sm text-gray-500">{tx("No messages.")}</p>}
      </div>
      <form className="flex flex-wrap gap-2" onSubmit={send}>
        <input aria-label={tx("Reply")} value={text} maxLength={2000} onChange={(e) => setText(e.target.value)} placeholder={tx("Write a reply")}
          className="flex-1 min-w-[12rem] border rounded-lg px-3 py-2 text-sm" />
        <button className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm">{tx("Send")}</button>
      </form>
    </div>
  );
}
