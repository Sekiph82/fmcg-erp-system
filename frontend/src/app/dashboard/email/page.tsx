"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  emailApi, EmailAccount, EmailThread, EmailProvider,
  PROVIDER_COLOR, fmtEmailDate,
} from "@/lib/email";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

const MODULE_LABEL: Record<string, string> = {
  procurement: "Purchase",
  finance:     "Finance",
  sales:       "Sales",
  quality:     "Quality",
  customer:    "Customer",
  supplier:    "Supplier",
};

function ProviderIcon({ provider }: { provider: EmailProvider }) {
  const icons = { GMAIL: "G", OUTLOOK: "O", SMTP: "✉" };
  return (
    <span className={`text-xs font-bold px-2 py-0.5 rounded ${PROVIDER_COLOR[provider]}`}>
      {icons[provider]}
    </span>
  );
}

export default function EmailPage() {
  const qc = useQueryClient();
  const [activeAccount, setActiveAccount] = useState<EmailAccount | null>(null);
  const [activeThread, setActiveThread] = useState<EmailThread | null>(null);
  const [filterUnread, setFilterUnread] = useState(false);
  const [composeMode, setComposeMode] = useState(false);
  const [showAddAccount, setShowAddAccount] = useState(false);
  const [compose, setCompose] = useState({ to: "", subject: "", body: "", cc: "" });
  const [replyTo, setReplyTo] = useState<EmailThread | null>(null);
  const [connectFor, setConnectFor] = useState<EmailAccount | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: accounts = [] } = useQuery({
    queryKey: ["email-accounts"],
    queryFn: () => emailApi.listAccounts(),
  });

  const { data: threads = [], isLoading: threadsLoading } = useQuery({
    queryKey: ["email-threads", activeAccount?.id, filterUnread],
    queryFn: () => emailApi.listThreads({
      account_id: activeAccount?.id,
      unread_only: filterUnread || undefined,
    }),
    refetchInterval: 30_000,
  });

  const { data: threadDetail } = useQuery({
    queryKey: ["email-thread", activeThread?.id],
    queryFn: () => emailApi.getThread(activeThread!.id),
    enabled: !!activeThread,
  });

  const syncAccount = useMutation({
    mutationFn: (id: string) => emailApi.syncAccount(id),
    onSuccess: () => {
      setError(null);
      qc.invalidateQueries({ queryKey: ["email-threads"] });
      qc.invalidateQueries({ queryKey: ["email-accounts"] });
    },
    onError: (e) => { setError(errorText(e)); qc.invalidateQueries({ queryKey: ["email-accounts"] }); },
  });
  const sendAccount = replyTo ? accounts.find((a) => a.id === replyTo.account_id) ?? null : activeAccount;

  const sendEmail = useMutation({
    mutationFn: () => emailApi.sendEmail({
      account_id: sendAccount!.id,
      thread_id: replyTo?.id,
      to_emails: compose.to.split(",").map((e) => e.trim()).filter(Boolean),
      cc_emails: compose.cc ? compose.cc.split(",").map((e) => e.trim()).filter(Boolean) : [],
      subject: compose.subject,
      body_text: compose.body,
    }),
    onSuccess: () => {
      setComposeMode(false);
      setReplyTo(null);
      setError(null);
      setCompose({ to: "", subject: "", body: "", cc: "" });
      qc.invalidateQueries({ queryKey: ["email-threads"] });
      qc.invalidateQueries({ queryKey: ["email-thread"] });
    },
    onError: (e) => setError(errorText(e)),
  });

  const unreadCount = threads.filter((t) => !t.is_read).length;

  return (
    <div className="h-[calc(100vh-120px)] flex rounded-xl border bg-white overflow-hidden">
      {/* Left: Accounts + Thread list */}
      <div className="w-80 border-r flex flex-col shrink-0">
        {/* Accounts bar */}
        <div className="px-4 py-3 border-b">
          <div className="flex items-center justify-between mb-2">
            <span className="font-semibold text-gray-800">Email</span>
            <button className="text-xs text-indigo-600 hover:underline" onClick={() => setShowAddAccount(true)}>+ Account</button>
          </div>
          <div className="flex gap-2 flex-wrap">
            <button
              className={`text-xs px-2 py-1 rounded border ${!activeAccount ? "bg-indigo-600 text-white border-indigo-600" : "text-gray-600 border-gray-200"}`}
              onClick={() => setActiveAccount(null)}
            >
              All ({accounts.length})
            </button>
            {accounts.map((a) => (
              <button
                key={a.id}
                className={`text-xs px-2 py-1 rounded border flex items-center gap-1 ${activeAccount?.id === a.id ? "bg-indigo-600 text-white border-indigo-600" : "text-gray-600 border-gray-200"}`}
                onClick={() => setActiveAccount(a)}
              >
                <ProviderIcon provider={a.provider} />
                <span className="truncate max-w-[80px]">{a.email_address.split("@")[0]}</span>
              </button>
            ))}
          </div>
          {activeAccount && (
            <div className="mt-2 text-xs space-y-1">
              {activeAccount.connected ? (
                <p className="text-emerald-700">Connected · {activeAccount.imap_host}{activeAccount.last_sync_at ? ` · synced ${fmtEmailDate(activeAccount.last_sync_at)}` : ""}</p>
              ) : (
                <p className="text-amber-700">Not connected: cannot send or receive.</p>
              )}
              {activeAccount.sync_error && <p className="text-red-700">{activeAccount.sync_error}</p>}
              <div className="flex gap-3">
                <button className="text-indigo-600 hover:underline" onClick={() => setConnectFor(activeAccount)}>
                  {activeAccount.connected ? "Change password" : "Connect"}
                </button>
                <button className="text-gray-500 hover:underline" onClick={async () => {
                  if (!confirm(`Disconnect ${activeAccount.email_address}? The stored password is erased; mail history stays.`)) return;
                  await emailApi.removeAccount(activeAccount.id);
                  setActiveAccount(null);
                  qc.invalidateQueries({ queryKey: ["email-accounts"] });
                }}>Disconnect</button>
              </div>
            </div>
          )}
          {error && <p role="alert" className="mt-2 text-xs text-red-700">{error}</p>}
        </div>

        {/* Actions bar */}
        <div className="px-4 py-2 border-b flex items-center gap-2">
          <button
            className={`text-xs px-2 py-1 rounded ${filterUnread ? "bg-amber-100 text-amber-700" : "text-gray-500 hover:bg-gray-100"}`}
            onClick={() => setFilterUnread(!filterUnread)}
          >
            {filterUnread ? `Unread (${unreadCount})` : `All (${threads.length})`}
          </button>
          <div className="ml-auto flex gap-1">
            {activeAccount && (
              <button
                className="text-xs text-gray-500 hover:text-indigo-600"
                onClick={() => syncAccount.mutate(activeAccount.id)}
                title="Sync inbox"
              >
                ↻ Sync
              </button>
            )}
            <Button onClick={() => { setReplyTo(null); setComposeMode(true); }} className="text-xs py-1">Compose</Button>
          </div>
        </div>

        {/* Thread list */}
        <div className="flex-1 overflow-y-auto">
          {threadsLoading ? (
            <p className="px-4 py-6 text-xs text-gray-400 text-center">Loading…</p>
          ) : threads.length === 0 ? (
            <div className="px-4 py-8 text-center">
              <p className="text-sm text-gray-400">No emails yet</p>
              {activeAccount && (
                <button
                  className="mt-2 text-xs text-indigo-600 hover:underline"
                  onClick={() => syncAccount.mutate(activeAccount.id)}
                >
                  Sync inbox to populate
                </button>
              )}
            </div>
          ) : (
            threads.map((t) => (
              <button
                key={t.id}
                className={`w-full text-left px-4 py-3 border-b hover:bg-gray-50 ${activeThread?.id === t.id ? "bg-indigo-50" : ""} ${!t.is_read ? "bg-blue-50/30" : ""}`}
                onClick={() => setActiveThread(t)}
              >
                <div className="flex items-start justify-between gap-1">
                  <span className={`text-sm truncate ${!t.is_read ? "font-semibold text-gray-900" : "text-gray-700"}`}>
                    {t.subject}
                  </span>
                  <span className="text-xs text-gray-400 shrink-0">{fmtEmailDate(t.last_message_at)}</span>
                </div>
                <p className="text-xs text-gray-500 truncate mt-0.5">{t.snippet}</p>
                <div className="flex items-center gap-2 mt-1">
                  {!t.is_read && <span className="w-2 h-2 rounded-full bg-blue-500 shrink-0" />}
                  {t.linked_module && (
                    <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                      {MODULE_LABEL[t.linked_module] ?? t.linked_module}
                      {t.linked_object_ref && ` · ${t.linked_object_ref}`}
                    </span>
                  )}
                  <span className="text-xs text-gray-400">{t.message_count} msg</span>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Right: Thread detail or compose */}
      <div className="flex-1 flex flex-col min-w-0">
        {composeMode ? (
          <div className="flex-1 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-gray-800">{replyTo ? "Reply" : "New Email"}{sendAccount ? ` · from ${sendAccount.email_address}` : ""}</h2>
              <button className="text-gray-400 hover:text-gray-700" onClick={() => { setComposeMode(false); setReplyTo(null); }}>✕</button>
            </div>
            {!sendAccount && (
              <p className="text-sm text-amber-600">Select an account from the left sidebar first</p>
            )}
            <div className="space-y-3">
              {[
                { label: "To", field: "to" as const, placeholder: "recipient@example.com, another@example.com" },
                { label: "CC", field: "cc" as const, placeholder: "cc@example.com (optional)" },
                { label: "Subject", field: "subject" as const, placeholder: "Email subject…" },
              ].map(({ label, field, placeholder }) => (
                <div key={field} className="flex items-center gap-3">
                  <label className="w-16 text-sm text-gray-500 shrink-0">{label}</label>
                  <input
                    className="flex-1 border-b py-1.5 text-sm focus:outline-none focus:border-indigo-400"
                    value={compose[field]}
                    onChange={(e) => setCompose((f) => ({ ...f, [field]: e.target.value }))}
                    placeholder={placeholder}
                  />
                </div>
              ))}
              <textarea
                className="w-full border rounded px-3 py-2 text-sm mt-2 h-48 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-300"
                placeholder="Write your email…"
                value={compose.body}
                onChange={(e) => setCompose((f) => ({ ...f, body: e.target.value }))}
              />
            </div>
            <div className="flex gap-2">
              <Button
                loading={sendEmail.isPending}
                onClick={() => sendAccount && compose.to && compose.subject && sendEmail.mutate()}
                disabled={!sendAccount || !compose.to || !compose.subject}
              >
                Send
              </Button>
              <Button variant="secondary" onClick={() => { setComposeMode(false); setReplyTo(null); }}>Discard</Button>
            </div>
          </div>
        ) : !activeThread ? (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <p className="text-2xl mb-2">✉</p>
              <p className="text-sm">Select a thread to read</p>
              {accounts.length === 0 && (
                <button
                  className="mt-3 text-sm text-indigo-600 hover:underline"
                  onClick={() => setShowAddAccount(true)}
                >
                  + Connect email account
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col min-h-0">
            {/* Thread header */}
            <div className="px-6 py-4 border-b">
              <h2 className="font-semibold text-gray-900 text-lg">{threadDetail?.subject ?? activeThread.subject}</h2>
              <div className="flex items-center gap-3 mt-1 flex-wrap">
                {(threadDetail?.participants ?? activeThread.participants ?? []).map((p) => (
                  <span key={p} className="text-xs text-gray-500">{p}</span>
                ))}
                {activeThread.linked_module && (
                  <span className={`text-xs px-2 py-0.5 rounded font-medium bg-indigo-100 text-indigo-700`}>
                    🔗 {MODULE_LABEL[activeThread.linked_module] ?? activeThread.linked_module}
                    {activeThread.linked_object_ref && ` · ${activeThread.linked_object_ref}`}
                  </span>
                )}
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
              {(threadDetail?.messages ?? []).map((msg) => (
                <div key={msg.id} className={`flex gap-4 ${!msg.is_inbound ? "flex-row-reverse" : ""}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0 ${msg.is_inbound ? "bg-gray-400" : "bg-indigo-600"}`}>
                    {msg.from_name?.[0]?.toUpperCase() ?? msg.from_email[0].toUpperCase()}
                  </div>
                  <div className={`max-w-[70%] ${!msg.is_inbound ? "items-end" : ""} flex flex-col gap-1`}>
                    <div className="flex items-baseline gap-2">
                      <span className="text-sm font-medium text-gray-800">{msg.from_name ?? msg.from_email}</span>
                      <span className="text-xs text-gray-400">{fmtEmailDate(msg.received_at)}</span>
                      {!msg.is_inbound && <span className="text-xs text-indigo-500">Sent</span>}
                    </div>
                    <div className={`rounded-xl px-4 py-3 text-sm whitespace-pre-wrap ${msg.is_inbound ? "bg-gray-100 text-gray-800" : "bg-indigo-600 text-white"}`}>
                      {msg.body_text}
                    </div>
                    {(msg.attachments ?? []).map((a) => (
                      <span key={a.name} className="text-xs text-gray-500">📎 {a.name} · {Math.max(1, Math.round(a.size / 1024))} KB</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* Reply bar */}
            <div className="border-t px-6 py-3">
              <button
                className="w-full text-left text-sm text-gray-400 bg-gray-50 rounded-lg px-4 py-3 hover:bg-gray-100"
                onClick={() => {
                  setReplyTo(activeThread);
                  setComposeMode(true);
                  setCompose((c) => ({
                    ...c,
                    // reply to whoever wrote last (not reply-all to everyone ever copied on the thread)
                    to: [...(threadDetail?.messages ?? [])].reverse().find((m) => m.is_inbound)?.from_email
                      ?? activeThread.participants?.filter((p) => p !== accounts.find((a) => a.id === activeThread.account_id)?.email_address)[0] ?? "",
                    subject: /^re:/i.test(activeThread.subject) ? activeThread.subject : `Re: ${activeThread.subject}`,
                  }));
                }}
              >
                Reply to this thread…
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Add Account Modal */}
      {connectFor && (
        <ConnectModal
          account={connectFor}
          onClose={() => setConnectFor(null)}
          onSave={() => { qc.invalidateQueries({ queryKey: ["email-accounts"] }); setConnectFor(null); setActiveAccount(null); }}
        />
      )}
      {showAddAccount && (
        <AddAccountModal
          onClose={() => setShowAddAccount(false)}
          onSave={() => { qc.invalidateQueries({ queryKey: ["email-accounts"] }); setShowAddAccount(false); }}
        />
      )}
    </div>
  );
}

function errorText(e: unknown) {
  const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  return typeof detail === "string" ? detail : "Request failed.";
}

const FIELD = "w-full border rounded px-3 py-2 text-sm";
const EMPTY_SERVER = { password: "", imap_host: "", imap_port: "", smtp_host: "", smtp_port: "", username: "" };

function serverPayload(form: Record<string, string>) {
  const num = (v: string) => (v ? Number(v) : undefined);
  return {
    password: form.password || undefined, imap_host: form.imap_host || undefined, imap_port: num(form.imap_port),
    smtp_host: form.smtp_host || undefined, smtp_port: num(form.smtp_port), username: form.username || undefined,
  };
}

function ServerFields({ form, set, provider }: { form: Record<string, string>; set: (k: string, v: string) => void; provider: EmailProvider }) {
  const hint = provider === "GMAIL" ? "Google account → Security → App passwords (needs 2-step verification)."
    : provider === "OUTLOOK" ? "Microsoft account → Security → App password, or ask IT to allow IMAP/SMTP."
    : "The password your mail host gives for IMAP/SMTP.";
  const servers = [["imap_host", "IMAP server"], ["imap_port", "IMAP port (993)"], ["smtp_host", "SMTP server"],
    ["smtp_port", "SMTP port (465 or 587)"], ["username", "Login, if not the address"]] as const;
  return (
    <>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">App password</label>
        <input type="password" autoComplete="new-password" className={FIELD} value={form.password} onChange={(e) => set("password", e.target.value)} />
        <p className="text-xs text-gray-400 mt-1">{hint} Stored encrypted; the login is tested before saving.</p>
      </div>
      {provider === "SMTP" && (
        <div className="grid grid-cols-2 gap-2">
          {servers.map(([k, label]) => (
            <input key={k} aria-label={label} placeholder={label} className={FIELD} value={form[k]} onChange={(e) => set(k, e.target.value)} />
          ))}
        </div>
      )}
    </>
  );
}

function AddAccountModal({ onClose, onSave }: { onClose: () => void; onSave: () => void }) {
  const [form, setForm] = useState<Record<string, string>>({ provider: "GMAIL", email_address: "", display_name: "", ...EMPTY_SERVER });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  async function save() {
    if (!form.email_address.includes("@")) return;
    setSaving(true);
    setErr(null);
    try {
      const account = await emailApi.addAccount({
        provider: form.provider as EmailProvider, email_address: form.email_address,
        display_name: form.display_name || undefined, ...serverPayload(form),
      });
      if (account.connected) await emailApi.syncAccount(account.id).catch(() => undefined);
      onSave();
    } catch (e) {
      setErr(errorText(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4 max-h-full overflow-y-auto">
        <h2 className="font-semibold text-lg">Connect Email Account</h2>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Provider</label>
            <select className={FIELD} value={form.provider} onChange={(e) => set("provider", e.target.value)}>
              <option value="GMAIL">Gmail / Google Workspace</option>
              <option value="OUTLOOK">Outlook / Microsoft 365</option>
              <option value="SMTP">Other (IMAP/SMTP)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Email Address</label>
            <input className={FIELD} value={form.email_address} onChange={(e) => set("email_address", e.target.value)} placeholder="sales@povu.co.ke" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Display Name (optional)</label>
            <input className={FIELD} value={form.display_name} onChange={(e) => set("display_name", e.target.value)} placeholder="POVU Sales" />
          </div>
          <ServerFields form={form} set={set} provider={form.provider as EmailProvider} />
          {err && <p role="alert" className="text-sm text-red-700">{err}</p>}
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={saving} onClick={save} disabled={!form.email_address.includes("@")}>Connect &amp; Sync</Button>
        </div>
      </div>
    </div>
  );
}

function ConnectModal({ account, onClose, onSave }: { account: EmailAccount; onClose: () => void; onSave: () => void }) {
  const [form, setForm] = useState<Record<string, string>>({
    ...EMPTY_SERVER, imap_host: account.imap_host ?? "", imap_port: account.imap_port ? String(account.imap_port) : "",
    smtp_host: account.smtp_host ?? "", smtp_port: account.smtp_port ? String(account.smtp_port) : "", username: account.username ?? "",
  });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  async function save() {
    setSaving(true);
    setErr(null);
    try {
      await emailApi.connectAccount(account.id, serverPayload(form));
      await emailApi.syncAccount(account.id).catch(() => undefined);
      onSave();
    } catch (e) {
      setErr(errorText(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4 max-h-full overflow-y-auto">
        <h2 className="font-semibold text-lg">Connect {account.email_address}</h2>
        <ServerFields form={form} set={set} provider={account.provider} />
        {err && <p role="alert" className="text-sm text-red-700">{err}</p>}
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={saving} onClick={save} disabled={!form.password}>Connect</Button>
        </div>
      </div>
    </div>
  );
}
