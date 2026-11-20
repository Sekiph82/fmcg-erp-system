"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { crmApi, type InboxItem } from "@/lib/crm_pipeline";
import { useAuth } from "@/context/AuthContext";

function errorText(e: unknown) {
  const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  return typeof detail === "string" ? detail : "Request failed.";
}

const CHANNEL_LABEL: Record<string, string> = { EMAIL: "E-mail", WHATSAPP: "WhatsApp", TICKET: "Ticket", CHAT: "Website chat" };
const VIEWS = [["all", "All open"], ["mine", "Mine"], ["unassigned", "Unassigned"], ["unread", "Unread"]] as const;

export default function CRMInboxPage() {
  const { user, hasAnyPermission } = useAuth();
  const canEdit = hasAnyPermission(["crm.edit", "crm.edit_all", "crm.edit_own_scope", "crm.edit_own_region"]);
  const [items, setItems] = useState<InboxItem[]>([]);
  const [counts, setCounts] = useState({ open: 0, unread: 0 });
  const [view, setView] = useState("all");
  const [channel, setChannel] = useState("");
  const [closed, setClosed] = useState(false);
  const [people, setPeople] = useState<{ id: string; name: string }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await crmApi.getInbox({ view, channel: channel || undefined, status: closed ? "CLOSED" : undefined });
      setItems(r.items);
      setCounts({ open: r.open, unread: r.unread });
      setError(null);
    } catch (e) { setError(errorText(e)); } finally { setLoading(false); }
  }, [view, channel, closed]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (canEdit) crmApi.getInboxAssignees().then(setPeople).catch(() => setPeople([])); }, [canEdit]);

  async function act(fn: () => Promise<unknown>) {
    setError(null);
    try { await fn(); await load(); } catch (e) { setError(errorText(e)); }
  }
  const nameOf = (id: string | null) => (id ? people.find((p) => p.id === id)?.name ?? (id === user?.id ? "Me" : "Assigned") : "—");
  const input = "text-sm border rounded-lg px-2 py-1.5";

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Conversations Inbox</h1>
        <p className="text-sm text-gray-500">
          Customer e-mails, WhatsApp chats and support tickets in one list. You see your own mailbox, the shared WhatsApp
          number with CRM access, tickets with quality access, and anything assigned to you. {counts.open} open · {counts.unread} unread.
        </p>
      </div>
      {error && <p role="alert" className="rounded-lg p-3 text-sm bg-red-50 border border-red-200 text-red-700">{error}</p>}

      <div className="flex flex-wrap gap-2 items-center">
        {VIEWS.map(([k, label]) => (
          <button key={k} onClick={() => setView(k)} aria-pressed={view === k}
            className={`px-3 py-1.5 text-sm rounded-lg border ${view === k ? "bg-blue-600 text-white border-blue-600" : "bg-white"}`}>{label}</button>
        ))}
        <select aria-label="Channel" value={channel} onChange={(e) => setChannel(e.target.value)} className={input}>
          <option value="">All channels</option>
          {Object.entries(CHANNEL_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <label className="text-sm flex items-center gap-1"><input type="checkbox" checked={closed} onChange={(e) => setClosed(e.target.checked)} /> Closed</label>
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-x-auto">
        {loading ? <p className="p-4 text-sm text-gray-400">Loading…</p> : items.length === 0 ? (
          <p className="p-4 text-sm text-gray-400">No conversations here.</p>
        ) : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-gray-500"><th className="p-2">Channel</th><th>Conversation</th><th>Last message</th><th>Reply due</th><th>Assignee</th><th>Status</th><th /></tr></thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id} className={`border-t ${c.unread ? "font-semibold" : ""}`}>
                  <td className="p-2 whitespace-nowrap">{CHANNEL_LABEL[c.channel]}</td>
                  <td className="min-w-[14rem]">
                    <Link href={c.link} onClick={() => crmApi.markInboxRead(c.id).catch(() => undefined)} className="text-blue-700 hover:underline">{c.subject}</Link>
                    {c.contact && <div className="text-xs text-gray-500 font-normal">{c.contact}</div>}
                  </td>
                  <td className="whitespace-nowrap">{c.last_message_at ? new Date(c.last_message_at).toLocaleString() : "—"}</td>
                  <td className={`whitespace-nowrap ${c.sla_overdue ? "text-red-700" : ""}`}>
                    {c.sla_due_at ? `${c.sla_overdue ? "Overdue · " : ""}${new Date(c.sla_due_at).toLocaleString()}` : "—"}
                  </td>
                  <td>
                    {canEdit ? (
                      <select aria-label={`Assignee for ${c.subject}`} value={c.assignee_id ?? ""} className={input}
                        onChange={(e) => act(() => crmApi.updateInbox(c.id, { assignee_id: e.target.value }))}>
                        <option value="">Unassigned</option>
                        {people.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                      </select>
                    ) : nameOf(c.assignee_id)}
                  </td>
                  <td>
                    {canEdit && c.channel !== "TICKET" && c.channel !== "CHAT" ? (
                      <select aria-label={`Status for ${c.subject}`} value={c.status} className={input}
                        onChange={(e) => act(() => crmApi.updateInbox(c.id, { status: e.target.value }))}>
                        {["OPEN", "PENDING", "CLOSED"].map((s) => <option key={s} value={s}>{s}</option>)}
                      </select>
                    ) : c.status}
                  </td>
                  <td className="pr-2 whitespace-nowrap">
                    {c.unread && <button className="text-xs underline font-normal" onClick={() => act(() => crmApi.markInboxRead(c.id))}>Mark read</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
