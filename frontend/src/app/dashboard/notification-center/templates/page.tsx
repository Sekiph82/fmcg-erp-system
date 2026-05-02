"use client";
import { useEffect, useState } from "react";
import {
  notificationsApi, NCTemplate, NotificationType, NotificationChannel,
  TYPE_COLOR, CHANNEL_LABEL, NOTIFICATION_TYPES, CHANNELS,
} from "@/lib/notifications_center";

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<NCTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [preview, setPreview] = useState<NCTemplate | null>(null);
  const [sendVars, setSendVars] = useState<Record<string, string>>({});
  const [sendUserId, setSendUserId] = useState("");
  const [form, setForm] = useState({
    template_code: "", template_name: "",
    notification_type: "info" as NotificationType,
    channel: "in_app" as NotificationChannel,
    title_template: "", message_template: "",
    language: "en", module: "",
  });

  const load = () => notificationsApi.listTemplates().then(setTemplates).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const submit = async () => {
    await notificationsApi.createTemplate({ ...form, module: form.module || undefined });
    setShowForm(false);
    load();
  };

  const seed = async () => {
    const r = await notificationsApi.seedTemplates();
    alert(`Seeded ${r.created} templates.`);
    load();
  };

  const sendFromTemplate = async (tpl: NCTemplate) => {
    if (!sendUserId) { alert("User ID required"); return; }
    await notificationsApi.sendFromTemplate({
      template_code: tpl.template_code,
      user_id: sendUserId,
      variables: sendVars,
    });
    alert("Notification sent!");
    setPreview(null);
    setSendVars({});
    setSendUserId("");
  };

  // Extract {{variable}} placeholders
  const extractVars = (tpl: NCTemplate): string[] => {
    const matches = Array.from((tpl.title_template + " " + tpl.message_template).matchAll(/\{\{(\w+)\}\}/g));
    return Array.from(new Set(matches.map(m => m[1])));
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Notification Templates</h1>
        <div className="flex gap-2">
          <button onClick={seed} className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50">
            Seed Defaults
          </button>
          <button onClick={() => setShowForm(true)}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            + New Template
          </button>
        </div>
      </div>

      {showForm && (
        <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
          <h2 className="font-semibold text-gray-800">New Template</h2>
          <div className="grid grid-cols-2 gap-3">
            {(["template_code","template_name","module"] as const).map(f => (
              <div key={f}><label className="text-xs text-gray-500 capitalize">{f.replace(/_/g," ")}</label>
                <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={form[f]}
                  onChange={(e) => setForm({ ...form, [f]: e.target.value })} /></div>
            ))}
            <div><label className="text-xs text-gray-500">Type</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.notification_type}
                onChange={(e) => setForm({ ...form, notification_type: e.target.value as NotificationType })}>
                {NOTIFICATION_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g," ")}</option>)}
              </select></div>
            <div><label className="text-xs text-gray-500">Channel</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.channel}
                onChange={(e) => setForm({ ...form, channel: e.target.value as NotificationChannel })}>
                {CHANNELS.map(c => <option key={c} value={c}>{CHANNEL_LABEL[c]}</option>)}
              </select></div>
            <div className="col-span-2"><label className="text-xs text-gray-500">Title Template (use &#123;&#123;variable&#125;&#125;)</label>
              <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.title_template}
                onChange={(e) => setForm({ ...form, title_template: e.target.value })} /></div>
            <div className="col-span-2"><label className="text-xs text-gray-500">Message Template</label>
              <textarea className="w-full border rounded px-2 py-1 text-sm mt-1 font-mono" rows={3} value={form.message_template}
                onChange={(e) => setForm({ ...form, message_template: e.target.value })} /></div>
          </div>
          <div className="flex gap-2">
            <button onClick={submit} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">Save</button>
            <button onClick={() => setShowForm(false)} className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {loading ? <p className="text-gray-500 text-sm">Loading…</p> : (
        <div className="grid gap-3">
          {templates.map(t => (
            <div key={t.template_id} className="bg-white border rounded-lg p-4 shadow-sm">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs text-gray-400">{t.template_code}</span>
                    <span className="font-semibold text-gray-800">{t.template_name}</span>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${TYPE_COLOR[t.notification_type]}`}>
                      {t.notification_type.replace(/_/g," ")}
                    </span>
                    <span className="rounded border px-2 py-0.5 text-xs text-gray-500">{CHANNEL_LABEL[t.channel]}</span>
                    {t.module && <span className="text-xs text-gray-400">Module: {t.module}</span>}
                    {!t.active_flag && <span className="rounded-full bg-gray-100 text-gray-500 px-2 py-0.5 text-xs">Inactive</span>}
                  </div>
                  <p className="text-sm text-gray-600 mt-1 font-medium">{t.title_template}</p>
                  <p className="text-xs text-gray-500 mt-0.5 font-mono">{t.message_template}</p>
                </div>
                <button onClick={() => { setPreview(t); setSendVars({}); setSendUserId(""); }}
                  className="ml-3 text-xs text-blue-600 hover:underline shrink-0">Send</button>
              </div>
            </div>
          ))}
          {templates.length === 0 && <p className="text-gray-400 text-sm text-center py-8">No templates. Seed defaults or create one.</p>}
        </div>
      )}

      {preview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-sm p-6 space-y-3">
            <div className="flex justify-between">
              <h2 className="font-bold text-gray-900">Send: {preview.template_name}</h2>
              <button onClick={() => setPreview(null)} className="text-gray-400 hover:text-gray-700">✕</button>
            </div>
            <div><label className="text-xs text-gray-500">User ID *</label>
              <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={sendUserId}
                onChange={(e) => setSendUserId(e.target.value)} /></div>
            {extractVars(preview).map(v => (
              <div key={v}><label className="text-xs text-gray-500">{v}</label>
                <input className="w-full border rounded px-2 py-1 text-sm mt-1"
                  placeholder={`Value for {{${v}}}`}
                  value={sendVars[v] ?? ""}
                  onChange={(e) => setSendVars({ ...sendVars, [v]: e.target.value })} /></div>
            ))}
            <div className="flex gap-2">
              <button onClick={() => sendFromTemplate(preview)}
                className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">Send</button>
              <button onClick={() => setPreview(null)}
                className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
