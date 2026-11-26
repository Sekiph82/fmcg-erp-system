"use client";

// M49.S01.T003: shared and delegated mailboxes. A selector switches between the shared mailboxes you are a member of
// (their mail is kept apart from your personal inbox); send-as / send-on-behalf follow your grant and the provider's
// own permission check. Administrators (integrations.edit) register mailboxes and manage members here too.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { EntityPicker } from "@/components/EntityPicker";
import { tx, lx } from "@/lib/i18n/core";

interface Mailbox {
  id: string; provider: string; address: string; display_name: string | null; kind: string; status: string; member: boolean;
  last_sync_at: string | null; last_error: string | null; send_modes: string[];
  my_access?: { can_read: boolean; can_send: boolean; send_mode: string };
}
interface Msg { id: string; from_email: string; from_name?: string | null; subject: string; body_text?: string | null; received_at: string; is_inbound: boolean; has_attachments: boolean; attachments?: { name: string }[] | null }
interface Thread { id: string; subject: string; snippet?: string | null; message_count: number; last_message_at?: string | null; participants?: string[] | null; messages: Msg[] }
interface Member { user_id: string; email: string; name: string | null; can_send: boolean; send_mode: string; active: boolean }

const MODE: Record<string, string> = lx(() => ({ send_as: tx("Send as the mailbox"), on_behalf: tx("Send on behalf of the mailbox") }));
const STATUS_STYLE: Record<string, string> = { ACTIVE: "bg-green-100 text-green-700", ACCESS_LOST: "bg-red-100 text-red-700", REVOKED: "bg-gray-100 text-gray-500" };
function errorText(e: unknown, fallback = tx("The request failed.")) {
  const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => (x as { msg?: string }).msg).join("; ");
  return fallback;
}

export function SharedMailboxPanel() {
  const [boxes, setBoxes] = useState<Mailbox[]>([]);
  const [sel, setSel] = useState<string>("");
  const [threads, setThreads] = useState<Thread[]>([]);
  const [open, setOpen] = useState<Thread | null>(null);
  const [compose, setCompose] = useState<{ to: string; subject: string; body: string } | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [grant, setGrant] = useState({ user_id: "", can_send: false, send_mode: "send_as" });
  const [reg, setReg] = useState({ provider: "microsoft", address: "", display_name: "", kind: "shared" });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [showAdmin, setShowAdmin] = useState(false);
  const [adminId, setAdminId] = useState("");

  const box = boxes.find((b) => b.id === sel) ?? null;
  const adminBox = boxes.find((b) => b.id === adminId) ?? null;

  const loadBoxes = useCallback(async () => {
    try {
      const r = await apiClient.get<Mailbox[]>("/api/v1/shared-mailboxes");
      setBoxes(r.data);
      setSel((cur) => (r.data.some((b) => b.id === cur && b.member) ? cur : r.data.find((b) => b.member)?.id ?? ""));
    } catch { setBoxes([]); }
  }, []);
  useEffect(() => { loadBoxes(); }, [loadBoxes]);

  const loadThreads = useCallback(async (id: string) => {
    if (!id) { setThreads([]); return; }
    try { setThreads((await apiClient.get<Thread[]>(`/api/v1/shared-mailboxes/${id}/threads`)).data); }
    catch (e) { setThreads([]); setMsg({ ok: false, text: errorText(e) }); }
  }, []);
  useEffect(() => { setOpen(null); setCompose(null); loadThreads(sel); }, [sel, loadThreads]);

  const loadMembers = useCallback(async (id: string) => {
    try { setMembers((await apiClient.get<Member[]>(`/api/v1/shared-mailboxes/${id}/members`)).data); } catch { setMembers([]); }
  }, []);

  const run = async (fn: () => Promise<string>) => {
    setBusy(true); setMsg(null);
    try { setMsg({ ok: true, text: await fn() }); } catch (e) { setMsg({ ok: false, text: errorText(e) }); }
    finally { setBusy(false); await loadBoxes(); if (sel) await loadThreads(sel); }
  };

  const mode = box?.my_access?.send_mode ?? "send_as";
  const canSend = !!box?.my_access?.can_send && box.status === "ACTIVE";
  const sendReason = !box ? "" : box.status !== "ACTIVE" ? tx("This mailbox is not active.") : !box.my_access?.can_send ? tx("You have read-only access to this mailbox.") : "";

  return (
    <div className="border rounded-lg bg-white p-3 space-y-2" data-testid="shared-mailbox-panel">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="text-sm font-semibold text-gray-800">{tx("Shared and delegated mailboxes")}</div>
        <div className="flex items-center gap-2 text-xs">
          <label>{tx("Mailbox")}{" "}
            <select className="border rounded px-2 py-1" value={sel} onChange={(e) => setSel(e.target.value)} aria-label={tx("Mailbox selector")}>
              <option value="">{tx("Personal inbox (below)")}</option>
              {boxes.filter((b) => b.member).map((b) => <option key={b.id} value={b.id}>{b.display_name || b.address} ({b.address})</option>)}
            </select></label>
          <button className="text-indigo-600 hover:underline" onClick={() => setShowAdmin((v) => !v)}>{showAdmin ? tx("Hide administration") : tx("Administration")}</button>
        </div>
      </div>
      {msg && <p role={msg.ok ? "status" : "alert"} className={`text-xs rounded px-2 py-1 ${msg.ok ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-700"}`}>{msg.text}</p>}
      {!boxes.some((b) => b.member) && !showAdmin && <p className="text-xs text-gray-500">{tx("You are not a member of a shared mailbox. An administrator adds you under Administration.")}</p>}

      {box && box.member && (
        <div className="border rounded p-2 space-y-2 text-xs">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div><span className="font-medium">{box.address}</span> <span className={`px-1.5 py-0.5 rounded ${STATUS_STYLE[box.status] ?? ""}`}>{box.status}</span>
              <span className="text-gray-500"> · {box.kind} · {box.provider} {tx("· synced")} {box.last_sync_at ? new Date(box.last_sync_at).toLocaleString() : tx("never")}</span>
              {box.last_error && <div className="text-red-600">{box.last_error}</div>}</div>
            <div className="flex gap-2">
              <button className="rounded border px-2 py-1 disabled:opacity-50" disabled={busy || box.status !== "ACTIVE"}
                onClick={() => run(async () => { const r = await apiClient.post<{ imported: number }>(`/api/v1/shared-mailboxes/${box.id}/sync`); return tx("Imported {imported} new message(s).", { imported: r.data.imported }); })}>{tx("Sync now")}</button>
              <button className="rounded bg-blue-600 text-white px-2 py-1 disabled:opacity-50" disabled={!canSend || busy} title={sendReason}
                onClick={() => { setOpen(null); setCompose({ to: "", subject: "", body: "" }); }}>{tx("New message")}</button>
            </div>
          </div>
          {sendReason && <div className="text-gray-500">{sendReason}</div>}
          {canSend && <div className="text-gray-600">{tx("Sending:")} <b>{MODE[mode]}</b> {tx("with your own sign-in; the provider checks your permission on this mailbox.")}</div>}

          {compose && (
            <div className="border rounded p-2 space-y-1 bg-gray-50">
              <div className="text-gray-700">{tx("From:")} {box.address} {mode === "on_behalf" ? tx("(sent on behalf, your name shows as sender)") : ""}</div>
              <input className="w-full border rounded px-2 py-1" placeholder={tx("To (comma separated)")} value={compose.to} onChange={(e) => setCompose({ ...compose, to: e.target.value })} disabled={!!open} />
              <input className="w-full border rounded px-2 py-1" placeholder={tx("Subject")} value={compose.subject} onChange={(e) => setCompose({ ...compose, subject: e.target.value })} />
              <textarea className="w-full border rounded px-2 py-1" rows={4} placeholder={tx("Message")} value={compose.body} onChange={(e) => setCompose({ ...compose, body: e.target.value })} />
              <div className="flex gap-2">
                <button className="rounded bg-blue-600 text-white px-3 py-1 disabled:opacity-50" disabled={busy || !compose.to || !compose.subject || !compose.body}
                  onClick={() => run(async () => {
                    await apiClient.post(`/api/v1/shared-mailboxes/${box.id}/send`, {
                      to_emails: compose.to.split(",").map((x) => x.trim()).filter(Boolean), subject: compose.subject, body_text: compose.body,
                      reply_to_thread_id: open?.id ?? null });
                    setCompose(null);
                    return `Sent from ${box.address}.`;
                  })}>{tx("Send")}</button>
                <button className="rounded border px-3 py-1" onClick={() => setCompose(null)}>{tx("Discard")}</button>
              </div>
            </div>)}

          <div className="grid md:grid-cols-2 gap-2">
            <div className="border rounded max-h-64 overflow-auto">
              {threads.length === 0 && <div className="p-2 text-gray-500">{tx("No messages yet. Use Sync now.")}</div>}
              {threads.map((t) => (
                <button key={t.id} className={`w-full text-left px-2 py-1.5 border-b hover:bg-gray-50 ${open?.id === t.id ? "bg-indigo-50" : ""}`}
                  onClick={() => { setOpen(t); setCompose(null); }}>
                  <div className="font-medium truncate">{t.subject}</div>
                  <div className="text-gray-500 truncate">{t.message_count} {tx("message(s) ·")} {t.snippet}</div>
                </button>))}
            </div>
            <div className="border rounded max-h-64 overflow-auto p-2 space-y-2">
              {!open && <div className="text-gray-500">{tx("Open a thread.")}</div>}
              {open && (
                <>
                  <div className="flex justify-between"><b>{open.subject}</b>
                    <button className="text-indigo-600 hover:underline disabled:opacity-50 disabled:no-underline" disabled={!canSend} title={sendReason}
                      onClick={() => {
                        const last = [...open.messages].reverse().find((m) => m.is_inbound) ?? open.messages[open.messages.length - 1];
                        setCompose({ to: last?.from_email ?? "", subject: open.subject.startsWith("Re:") ? open.subject : `Re: ${open.subject}`, body: "" });
                      }}>{tx("Reply as")} {box.address}</button></div>
                  {open.messages.map((m) => (
                    <div key={m.id} className={`rounded p-1.5 ${m.is_inbound ? "bg-gray-50" : "bg-blue-50"}`}>
                      <div className="text-gray-500">{m.from_name || m.from_email} · {new Date(m.received_at).toLocaleString()}</div>
                      <div className="whitespace-pre-wrap">{m.body_text}</div>
                      {m.has_attachments && <div className="text-gray-600">{tx("Attachments:")} {(m.attachments ?? []).map((a) => a.name).join(", ")}</div>}
                    </div>))}
                </>)}
            </div>
          </div>
        </div>)}

      {showAdmin && (
        <div className="border rounded p-2 space-y-2 text-xs">
          <div className="font-medium">{tx("Register a mailbox")}</div>
          <p className="text-gray-500">{tx("You must already be allowed to open it at the provider (Exchange Full Access / Send As, or Workspace delegation); the provider is asked before anything is saved.")}</p>
          <div className="flex gap-2 flex-wrap items-end">
            <select className="border rounded px-2 py-1" value={reg.provider} onChange={(e) => setReg({ ...reg, provider: e.target.value })}><option value="microsoft">{tx("Microsoft 365")}</option><option value="google">{tx("Google Workspace")}</option></select>
            <input className="border rounded px-2 py-1" placeholder="shared-mailbox@example.com" value={reg.address} onChange={(e) => setReg({ ...reg, address: e.target.value })} />
            <input className="border rounded px-2 py-1" placeholder={tx("Display name")} value={reg.display_name} onChange={(e) => setReg({ ...reg, display_name: e.target.value })} />
            <select className="border rounded px-2 py-1" value={reg.kind} onChange={(e) => setReg({ ...reg, kind: e.target.value })}><option value="shared">{tx("Shared")}</option><option value="delegated">{tx("Delegated")}</option></select>
            <button className="rounded bg-blue-600 text-white px-3 py-1 disabled:opacity-50" disabled={busy || !reg.address}
              onClick={() => run(async () => { await apiClient.post("/api/v1/shared-mailboxes", { ...reg, display_name: reg.display_name || null }); setReg({ ...reg, address: "", display_name: "" }); return tx("Mailbox registered."); })}>{tx("Register")}</button>
          </div>
          {boxes.length > 0 && (
            <>
              <div className="font-medium pt-1">{tx("Mailboxes")}</div>
              {boxes.map((b) => (
                <div key={b.id} className="flex items-center justify-between gap-2 flex-wrap border-t pt-1">
                  <span>{b.address} <span className={`px-1.5 py-0.5 rounded ${STATUS_STYLE[b.status] ?? ""}`}>{b.status}</span>{b.last_error && <span className="text-red-600"> {b.last_error}</span>}</span>
                  <span className="flex gap-3">
                    <button className="text-indigo-600 hover:underline" onClick={() => { setAdminId(b.id); setMembers([]); loadMembers(b.id); }}>{tx("Members")}</button>
                    {b.status !== "REVOKED" && <button className="text-red-600 hover:underline" onClick={() => { if (confirm(tx("Close {address}? Nobody can read or send from it until it is registered again; stored mail is kept.", { address: b.address }))) run(async () => { await apiClient.post(`/api/v1/shared-mailboxes/${b.id}/revoke`); return tx("Mailbox closed."); }); }}>{tx("Close mailbox")}</button>}
                  </span>
                </div>))}
            </>)}
          {adminBox && (
            <div className="border rounded p-2 space-y-1">
              <div className="font-medium">{tx("Members of")} {adminBox.address}</div>
              {members.map((m) => (
                <div key={m.user_id} className="flex items-center justify-between gap-2">
                  <span className={m.active ? "" : "line-through text-gray-400"}>{m.name || m.email} · {m.can_send ? MODE[m.send_mode] : tx("read only")}</span>
                  {m.active && <button className="text-red-600 hover:underline" onClick={() => run(async () => { await apiClient.delete(`/api/v1/shared-mailboxes/${adminBox.id}/members/${m.user_id}`); await loadMembers(adminBox.id); return `${m.email} no longer has access.`; })}>{tx("Revoke")}</button>}
                </div>))}
              <div className="flex gap-2 flex-wrap items-center pt-1">
                <div className="min-w-[14rem]"><EntityPicker kind="user" value={grant.user_id} onChange={(id) => setGrant({ ...grant, user_id: id })} placeholder={tx("Choose a user")} /></div>
                <label className="flex items-center gap-1"><input type="checkbox" checked={grant.can_send} onChange={(e) => setGrant({ ...grant, can_send: e.target.checked })} />{tx("May send")}</label>
                <select className="border rounded px-2 py-1" value={grant.send_mode} onChange={(e) => setGrant({ ...grant, send_mode: e.target.value })} disabled={!grant.can_send}>
                  {adminBox.send_modes.map((m) => <option key={m} value={m}>{MODE[m]}</option>)}</select>
                <button className="rounded bg-blue-600 text-white px-3 py-1 disabled:opacity-50" disabled={busy || !grant.user_id}
                  onClick={() => run(async () => { await apiClient.put(`/api/v1/shared-mailboxes/${adminBox.id}/members`, grant); await loadMembers(adminBox.id); return tx("Access granted."); })}>{tx("Grant")}</button>
              </div>
            </div>)}
        </div>)}
    </div>
  );
}
