"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  waApi, WAConfig, WAConfigUpdate, WAMessage, WATemplate,
  WADirection, STATUS_COLOR, STATUS_ICON,
} from "@/lib/whatsapp";
import { Button } from "@/components/ui/Button";

function fmtTime(iso: string) {
  return new Date(iso).toLocaleString("en-KE", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

function StatusBadge({ status }: { status: WAMessage["status"] }) {
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded ${STATUS_COLOR[status]}`}>
      {STATUS_ICON[status]} {status}
    </span>
  );
}

function MessageBubble({ msg }: { msg: WAMessage }) {
  const isOut = msg.direction === "OUTBOUND";
  return (
    <div className={`flex ${isOut ? "justify-end" : "justify-start"} mb-2`}>
      <div className={`max-w-[70%] rounded-xl px-4 py-2.5 ${isOut ? "bg-green-500 text-white" : "bg-white border text-gray-800"}`}>
        {!isOut && msg.contact_name && (
          <p className="text-xs font-semibold text-green-700 mb-1">{msg.contact_name}</p>
        )}
        {msg.template_name && (
          <p className={`text-xs mb-1 ${isOut ? "text-green-100" : "text-gray-400"}`}>
            📋 Template: {msg.template_name}
          </p>
        )}
        <p className="text-sm whitespace-pre-wrap">{msg.body ?? "(no body)"}</p>
        <div className={`flex items-center gap-2 mt-1 ${isOut ? "justify-end" : ""}`}>
          <span className={`text-xs ${isOut ? "text-green-100" : "text-gray-400"}`}>{fmtTime(msg.created_at)}</span>
          {isOut && <span className={`text-xs font-bold ${msg.status === "READ" ? "text-blue-200" : "text-green-200"}`}>{STATUS_ICON[msg.status]}</span>}
        </div>
        {msg.linked_object_ref && (
          <span className={`inline-block mt-1 text-xs px-1.5 py-0.5 rounded ${isOut ? "bg-green-600 text-green-100" : "bg-gray-100 text-gray-500"}`}>
            🔗 {msg.linked_module} · {msg.linked_object_ref}
          </span>
        )}
      </div>
    </div>
  );
}

export default function WhatsAppPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"conversations" | "templates" | "config">("conversations");
  const [activeConfig, setActiveConfig] = useState<WAConfig | null>(null);
  const [filterPhone, setFilterPhone] = useState("");
  const [composePhone, setComposePhone] = useState("");
  const [composeBody, setComposeBody] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<WATemplate | null>(null);
  const [templateVars, setTemplateVars] = useState<string[]>([]);
  const [showSend, setShowSend] = useState(false);
  const [showNewConfig, setShowNewConfig] = useState(false);
  const [newConfigForm, setNewConfigForm] = useState({ display_name: "", business_phone_no: "", provider: "META" });
  const [editingConfig, setEditingConfig] = useState<WAConfig | null>(null);
  const [editForm, setEditForm] = useState<WAConfigUpdate>({});

  const { data: configs = [] } = useQuery({
    queryKey: ["wa-configs"],
    queryFn: () => waApi.listConfigs(),
  });

  const { data: messages = [], isLoading: msgsLoading } = useQuery({
    queryKey: ["wa-messages", activeConfig?.id, filterPhone],
    queryFn: () => waApi.listMessages({
      config_id: activeConfig?.id,
      phone: filterPhone || undefined,
      limit: 100,
    }),
    refetchInterval: 15_000,
    enabled: tab === "conversations",
  });

  const { data: templates = [] } = useQuery({
    queryKey: ["wa-templates"],
    queryFn: () => waApi.listTemplates(),
    enabled: tab === "templates",
  });

  const sendText = useMutation({
    mutationFn: () => waApi.sendText({
      config_id: activeConfig!.id,
      phone: composePhone,
      body: composeBody,
    }),
    onSuccess: () => {
      setComposePhone(""); setComposeBody(""); setShowSend(false);
      qc.invalidateQueries({ queryKey: ["wa-messages"] });
    },
  });

  const sendTemplate = useMutation({
    mutationFn: () => waApi.sendTemplate({
      config_id: activeConfig!.id,
      phone: composePhone,
      template_name: selectedTemplate!.template_name,
      variables: templateVars,
    }),
    onSuccess: () => {
      setComposePhone(""); setSelectedTemplate(null); setTemplateVars([]); setShowSend(false);
      qc.invalidateQueries({ queryKey: ["wa-messages"] });
    },
  });

  const seedTemplates = useMutation({
    mutationFn: () => waApi.seedDemoTemplates(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["wa-templates"] }),
  });

  const addConfig = useMutation({
    mutationFn: () => waApi.addConfig({ ...newConfigForm, is_demo_mode: true }),
    onSuccess: (c) => {
      qc.invalidateQueries({ queryKey: ["wa-configs"] });
      setActiveConfig(c);
      setShowNewConfig(false);
      setNewConfigForm({ display_name: "", business_phone_no: "", provider: "META" });
    },
  });

  const updateConfig = useMutation({
    mutationFn: () => waApi.updateConfig(editingConfig!.id, editForm),
    onSuccess: (c) => {
      qc.invalidateQueries({ queryKey: ["wa-configs"] });
      if (activeConfig?.id === c.id) setActiveConfig(c);
      setEditingConfig(null);
      setEditForm({});
    },
  });

  // Group messages by phone for conversation view
  const phones = Array.from(new Set(messages.map((m) => m.phone)));
  const activeConvo = filterPhone ? messages.filter((m) => m.phone === filterPhone) : [];

  const unread = messages.filter((m) => m.direction === "INBOUND" && m.status !== "READ").length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">WhatsApp Business</h1>
          <p className="text-sm text-gray-500 mt-1">Send order confirmations, invoices, alerts via WhatsApp</p>
        </div>
        <div className="flex gap-2">
          {activeConfig && (
            <Button onClick={() => setShowSend(true)}>+ Send Message</Button>
          )}
          <Button variant="secondary" onClick={() => setShowNewConfig(true)}>+ Account</Button>
        </div>
      </div>

      {/* Config selector */}
      {configs.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {configs.map((c) => (
            <button
              key={c.id}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm ${activeConfig?.id === c.id ? "bg-green-600 text-white border-green-600" : "bg-white text-gray-700 border-gray-200"}`}
              onClick={() => setActiveConfig(c)}
            >
              <span className="text-lg">📱</span>
              <div className="text-left">
                <p className="font-medium leading-none">{c.display_name}</p>
                <p className={`text-xs ${activeConfig?.id === c.id ? "text-green-100" : "text-gray-400"}`}>
                  {c.business_phone_no ?? c.provider} {c.is_demo_mode && "· Demo"}
                </p>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Summary KPIs */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Total Messages",   value: messages.length,                                      color: "text-gray-700" },
          { label: "Sent Today",       value: messages.filter((m) => m.direction === "OUTBOUND" && new Date(m.created_at).toDateString() === new Date().toDateString()).length, color: "text-green-700" },
          { label: "Inbound",          value: messages.filter((m) => m.direction === "INBOUND").length, color: "text-blue-700" },
          { label: "Unread",           value: unread, color: unread > 0 ? "text-red-600" : "text-gray-500" },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-lg border p-4 text-center">
            <p className="text-xs text-gray-500 mb-1">{k.label}</p>
            <p className={`text-2xl font-bold ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {([
          { key: "conversations", label: "Conversations" },
          { key: "templates",    label: `Templates (${templates.length})` },
          { key: "config",       label: "Config" },
        ] as const).map((t) => (
          <button
            key={t.key}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab === t.key ? "border-green-600 text-green-700" : "border-transparent text-gray-500"}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* CONVERSATIONS */}
      {tab === "conversations" && (
        <div className="grid grid-cols-3 gap-6 h-[500px]">
          {/* Contact list */}
          <div className="bg-white border rounded-lg overflow-y-auto">
            <div className="px-4 py-3 border-b font-semibold text-sm text-gray-700">Contacts ({phones.length})</div>
            {phones.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-gray-400">No messages yet</p>
            ) : (
              phones.map((phone) => {
                const lastMsg = messages.filter((m) => m.phone === phone).at(-1);
                const hasUnread = messages.some((m) => m.phone === phone && m.direction === "INBOUND");
                return (
                  <button
                    key={phone}
                    className={`w-full text-left px-4 py-3 border-b hover:bg-gray-50 ${filterPhone === phone ? "bg-green-50" : ""}`}
                    onClick={() => setFilterPhone(filterPhone === phone ? "" : phone)}
                  >
                    <div className="flex items-center gap-2">
                      <div className="w-9 h-9 rounded-full bg-green-500 text-white flex items-center justify-center text-sm font-bold shrink-0">
                        {lastMsg?.contact_name?.[0]?.toUpperCase() ?? phone[3]}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-medium truncate ${hasUnread ? "text-gray-900" : "text-gray-700"}`}>
                          {lastMsg?.contact_name ?? phone}
                        </p>
                        <p className="text-xs text-gray-400 truncate">{lastMsg?.body?.slice(0, 40)}</p>
                      </div>
                      {hasUnread && <span className="w-2 h-2 rounded-full bg-green-500 shrink-0" />}
                    </div>
                  </button>
                );
              })
            )}
          </div>

          {/* Message thread */}
          <div className="col-span-2 bg-gray-50 border rounded-lg flex flex-col">
            {!filterPhone ? (
              <div className="flex-1 flex items-center justify-center text-gray-400">
                <p className="text-sm">Select a contact to view conversation</p>
              </div>
            ) : (
              <>
                <div className="px-4 py-3 bg-green-600 text-white rounded-t-lg flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-green-400 flex items-center justify-center text-white font-bold">
                    {activeConvo[0]?.contact_name?.[0]?.toUpperCase() ?? filterPhone[3]}
                  </div>
                  <div>
                    <p className="font-medium">{activeConvo[0]?.contact_name ?? filterPhone}</p>
                    <p className="text-xs text-green-100">{filterPhone}</p>
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto p-4">
                  {activeConvo.map((m) => <MessageBubble key={m.id} msg={m} />)}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* TEMPLATES */}
      {tab === "templates" && (
        <div className="bg-white rounded-lg border">
          <div className="px-5 py-3 border-b flex items-center justify-between">
            <h2 className="font-semibold text-gray-800">Message Templates</h2>
            <Button
              variant="secondary"
              onClick={() => seedTemplates.mutate()}
              loading={seedTemplates.isPending}
            >
              Seed Demo Templates
            </Button>
          </div>
          {templates.length === 0 ? (
            <p className="px-5 py-8 text-center text-gray-400">No templates — click &quot;Seed Demo Templates&quot; to add FMCG defaults</p>
          ) : (
            <div className="divide-y">
              {templates.map((t) => (
                <div key={t.id} className="px-5 py-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-gray-800">{t.display_name}</span>
                        <span className="font-mono text-xs text-gray-400">{t.template_name}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${t.category === "UTILITY" ? "bg-blue-100 text-blue-700" : t.category === "MARKETING" ? "bg-purple-100 text-purple-700" : "bg-gray-100 text-gray-600"}`}>
                          {t.category}
                        </span>
                        {t.module_context && <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">{t.module_context}</span>}
                      </div>
                      {t.header_text && <p className="text-xs font-semibold text-gray-600 mb-1">{t.header_text}</p>}
                      <p className="text-sm text-gray-700 bg-gray-50 rounded p-2 font-mono">{t.body_template}</p>
                      {t.footer_text && <p className="text-xs text-gray-400 mt-1">{t.footer_text}</p>}
                      {t.variable_count > 0 && (
                        <p className="text-xs text-gray-400 mt-1">{t.variable_count} variable{t.variable_count > 1 ? "s" : ""} required</p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* CONFIG tab */}
      {tab === "config" && (
        <div className="bg-white rounded-lg border">
          <div className="px-5 py-3 border-b font-semibold text-gray-800">WhatsApp Accounts</div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-4 py-2 text-left">Name</th>
                <th className="px-4 py-2 text-left">Phone</th>
                <th className="px-4 py-2 text-left">Provider</th>
                <th className="px-4 py-2 text-center">Mode</th>
                <th className="px-4 py-2 text-center">Status</th>
                <th className="px-4 py-2 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {configs.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{c.display_name}</td>
                  <td className="px-4 py-3 text-gray-600 font-mono text-xs">{c.business_phone_no ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-500">{c.provider}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs px-2 py-0.5 rounded ${c.is_demo_mode ? "bg-amber-100 text-amber-700" : "bg-green-100 text-green-700"}`}>
                      {c.is_demo_mode ? "Demo" : "Live"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs px-2 py-0.5 rounded ${c.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {c.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      className="text-xs text-blue-600 hover:underline"
                      onClick={() => { setEditingConfig(c); setEditForm({ is_demo_mode: c.is_demo_mode }); }}
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
              {configs.length === 0 && (
                <tr><td colSpan={6} className="px-5 py-8 text-center text-gray-400">No accounts — add one above</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Send modal */}
      {showSend && activeConfig && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
            <h2 className="font-semibold text-lg">Send WhatsApp Message</h2>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Phone (E.164)</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={composePhone} onChange={(e) => setComposePhone(e.target.value)} placeholder="+254712345678" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Template (optional)</label>
              <select className="w-full border rounded px-3 py-2 text-sm" value={selectedTemplate?.template_name ?? ""} onChange={(e) => {
                const t = templates.find((t) => t.template_name === e.target.value) ?? null;
                setSelectedTemplate(t);
                setTemplateVars(t ? Array(t.variable_count).fill("") : []);
              }}>
                <option value="">— Free text —</option>
                {templates.map((t) => <option key={t.id} value={t.template_name}>{t.display_name}</option>)}
              </select>
            </div>
            {selectedTemplate ? (
              <>
                <div className="bg-gray-50 rounded p-3 text-sm font-mono text-gray-600">{selectedTemplate.body_template}</div>
                {templateVars.map((v, i) => (
                  <div key={i}>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Variable {`{{${i + 1}}}`}</label>
                    <input className="w-full border rounded px-3 py-2 text-sm" value={v} onChange={(e) => setTemplateVars((vs) => vs.map((vv, j) => j === i ? e.target.value : vv))} />
                  </div>
                ))}
              </>
            ) : (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Message</label>
                <textarea className="w-full border rounded px-3 py-2 text-sm" rows={3} value={composeBody} onChange={(e) => setComposeBody(e.target.value)} />
              </div>
            )}
            <div className="flex gap-2 justify-end">
              <Button variant="secondary" onClick={() => setShowSend(false)}>Cancel</Button>
              <Button
                loading={sendText.isPending || sendTemplate.isPending}
                onClick={() => selectedTemplate ? sendTemplate.mutate() : sendText.mutate()}
                disabled={!composePhone || (!composeBody && !selectedTemplate)}
              >
                Send
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Edit config modal */}
      {editingConfig && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-lg">Edit WhatsApp Account</h2>
              <span className={`text-xs px-2 py-0.5 rounded font-medium ${editForm.is_demo_mode === false ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}>
                {editForm.is_demo_mode === false ? "Live Mode" : "Demo Mode"}
              </span>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Phone Number ID <span className="text-gray-400">(Meta Phone Number ID)</span></label>
                <input
                  className="w-full border rounded px-3 py-2 text-sm font-mono"
                  placeholder="e.g. 123456789012345"
                  value={editForm.business_phone_id ?? ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, business_phone_id: e.target.value || undefined }))}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Business Phone Number</label>
                <input
                  className="w-full border rounded px-3 py-2 text-sm"
                  placeholder="+254700000000"
                  value={editForm.business_phone_no ?? ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, business_phone_no: e.target.value || undefined }))}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Access Token <span className="text-gray-400">(System User token)</span></label>
                <input
                  type="password"
                  className="w-full border rounded px-3 py-2 text-sm font-mono"
                  placeholder="Enter token to update (leave blank to keep current)"
                  value={editForm.api_token ?? ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, api_token: e.target.value || undefined }))}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Webhook Verify Token</label>
                <input
                  type="password"
                  className="w-full border rounded px-3 py-2 text-sm font-mono"
                  placeholder="Enter verify token to update"
                  value={editForm.webhook_verify_token ?? ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, webhook_verify_token: e.target.value || undefined }))}
                />
              </div>
              <div className="flex items-center gap-3 pt-1">
                <label className="text-sm font-medium text-gray-700">Mode:</label>
                <button
                  type="button"
                  className={`px-3 py-1.5 rounded text-xs font-medium border ${editForm.is_demo_mode !== false ? "bg-amber-50 border-amber-300 text-amber-700" : "bg-white border-gray-200 text-gray-500"}`}
                  onClick={() => setEditForm((f) => ({ ...f, is_demo_mode: true }))}
                >
                  Demo (simulated)
                </button>
                <button
                  type="button"
                  className={`px-3 py-1.5 rounded text-xs font-medium border ${editForm.is_demo_mode === false ? "bg-green-50 border-green-400 text-green-700" : "bg-white border-gray-200 text-gray-500"}`}
                  onClick={() => setEditForm((f) => ({ ...f, is_demo_mode: false }))}
                >
                  Live (calls Meta API)
                </button>
              </div>
              {editForm.is_demo_mode === false && (
                <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
                  Live mode will call the real Meta Cloud API. Ensure Phone Number ID and Access Token are set above.
                </p>
              )}
            </div>
            <div className="flex gap-2 justify-end">
              <Button variant="secondary" onClick={() => { setEditingConfig(null); setEditForm({}); }}>Cancel</Button>
              <Button loading={updateConfig.isPending} onClick={() => updateConfig.mutate()}>Save</Button>
            </div>
          </div>
        </div>
      )}

      {/* Add config modal */}
      {showNewConfig && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 space-y-4">
            <h2 className="font-semibold text-lg">Add WhatsApp Account</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Display Name</label>
                <input className="w-full border rounded px-3 py-2 text-sm" value={newConfigForm.display_name} onChange={(e) => setNewConfigForm((f) => ({ ...f, display_name: e.target.value }))} placeholder="Sales Team WA" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Business Phone</label>
                <input className="w-full border rounded px-3 py-2 text-sm" value={newConfigForm.business_phone_no} onChange={(e) => setNewConfigForm((f) => ({ ...f, business_phone_no: e.target.value }))} placeholder="+254700000000" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Provider</label>
                <select className="w-full border rounded px-3 py-2 text-sm" value={newConfigForm.provider} onChange={(e) => setNewConfigForm((f) => ({ ...f, provider: e.target.value }))}>
                  <option value="META">Meta (WhatsApp Cloud API)</option>
                  <option value="TWILIO">Twilio</option>
                  <option value="AFRICASTALKING">Africa&apos;s Talking</option>
                </select>
              </div>
              <p className="text-xs text-gray-400">Starts in Demo mode — messages simulated locally.</p>
            </div>
            <div className="flex gap-2 justify-end">
              <Button variant="secondary" onClick={() => setShowNewConfig(false)}>Cancel</Button>
              <Button loading={addConfig.isPending} onClick={() => addConfig.mutate()} disabled={!newConfigForm.display_name.trim()}>Connect</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
