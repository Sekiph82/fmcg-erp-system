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
      qc.invalidateQueries({ queryKey: ["email-threads"] });
      qc.invalidateQueries({ queryKey: ["email-accounts"] });
    },
  });

  const sendEmail = useMutation({
    mutationFn: () => emailApi.sendEmail({
      account_id: activeAccount!.id,
      to_emails: compose.to.split(",").map((e) => e.trim()).filter(Boolean),
      cc_emails: compose.cc ? compose.cc.split(",").map((e) => e.trim()).filter(Boolean) : [],
      subject: compose.subject,
      body_text: compose.body,
    }),
    onSuccess: () => {
      setComposeMode(false);
      setCompose({ to: "", subject: "", body: "", cc: "" });
      qc.invalidateQueries({ queryKey: ["email-threads"] });
    },
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
            <Button onClick={() => setComposeMode(true)} className="text-xs py-1">Compose</Button>
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
              <h2 className="font-semibold text-gray-800">New Email</h2>
              <button className="text-gray-400 hover:text-gray-700" onClick={() => setComposeMode(false)}>✕</button>
            </div>
            {!activeAccount && (
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
                onClick={() => activeAccount && compose.to && compose.subject && sendEmail.mutate()}
                disabled={!activeAccount || !compose.to || !compose.subject}
              >
                Send
              </Button>
              <Button variant="secondary" onClick={() => setComposeMode(false)}>Discard</Button>
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
                  </div>
                </div>
              ))}
            </div>

            {/* Reply bar */}
            <div className="border-t px-6 py-3">
              <button
                className="w-full text-left text-sm text-gray-400 bg-gray-50 rounded-lg px-4 py-3 hover:bg-gray-100"
                onClick={() => {
                  setComposeMode(true);
                  setCompose((c) => ({
                    ...c,
                    to: activeThread.participants?.filter((p) => p !== activeAccount?.email_address).join(", ") ?? "",
                    subject: activeThread.subject.startsWith("RE:") ? activeThread.subject : `RE: ${activeThread.subject}`,
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
      {showAddAccount && (
        <AddAccountModal
          onClose={() => setShowAddAccount(false)}
          onSave={() => { qc.invalidateQueries({ queryKey: ["email-accounts"] }); setShowAddAccount(false); }}
        />
      )}
    </div>
  );
}

function AddAccountModal({ onClose, onSave }: { onClose: () => void; onSave: () => void }) {
  const [form, setForm] = useState({ provider: "GMAIL" as EmailProvider, email_address: "", display_name: "" });
  const [saving, setSaving] = useState(false);
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  async function save() {
    if (!form.email_address.includes("@")) return;
    setSaving(true);
    try {
      const account = await emailApi.addAccount({ ...form, display_name: form.display_name || undefined });
      await emailApi.syncAccount(account.id);
      onSave();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 space-y-4">
        <h2 className="font-semibold text-lg">Connect Email Account</h2>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Provider</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.provider} onChange={(e) => set("provider", e.target.value)}>
              <option value="GMAIL">Gmail</option>
              <option value="OUTLOOK">Outlook / Microsoft 365</option>
              <option value="SMTP">SMTP (Generic)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Email Address</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.email_address} onChange={(e) => set("email_address", e.target.value)} placeholder="you@company.com" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Display Name (optional)</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.display_name} onChange={(e) => set("display_name", e.target.value)} placeholder="Sales Team" />
          </div>
          <p className="text-xs text-gray-400">Demo mode: account connects immediately and syncs sample emails.</p>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={saving} onClick={save} disabled={!form.email_address.includes("@")}>Connect & Sync</Button>
        </div>
      </div>
    </div>
  );
}
