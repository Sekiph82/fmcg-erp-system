"use client";
import { useState, useEffect } from "react";
import { dunningApi, DunningTemplate, DunningActionType } from "@/lib/dunning";

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<DunningTemplate[]>([]);
  const [creating, setCreating] = useState(false);
  const [preview, setPreview] = useState<DunningTemplate | null>(null);
  const [form, setForm] = useState({
    template_code: "", language: "en", channel: "EMAIL" as DunningActionType,
    subject: "", body_text: "", notes: "",
  });

  const load = () => dunningApi.listTemplates().then(setTemplates);
  useEffect(() => { load(); }, []);

  const create = async () => {
    await dunningApi.createTemplate(form as any);
    setCreating(false);
    setForm({ template_code: "", language: "en", channel: "EMAIL", subject: "", body_text: "", notes: "" });
    load();
  };

  const MERGE_FIELDS = ["{{customer_name}}", "{{overdue_amount}}", "{{oldest_due_date}}", "{{case_no}}"];

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Message Templates</h1>
          <p className="text-sm text-gray-500 mt-1">Email, SMS, WhatsApp templates for dunning communications</p>
        </div>
        <button onClick={() => setCreating(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
          + New Template
        </button>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 text-xs text-blue-800">
        <strong>Merge fields:</strong> {MERGE_FIELDS.join(" · ")}
      </div>

      <div className="grid grid-cols-2 gap-4">
        {templates.map((t) => (
          <div key={t.id} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded text-gray-700">{t.template_code}</span>
              <div className="flex gap-2">
                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">{t.channel}</span>
                <span className="px-2 py-0.5 bg-gray-100 text-gray-500 rounded text-xs">{t.language.toUpperCase()}</span>
              </div>
            </div>
            <div className="font-semibold text-sm text-gray-900 mb-1">{t.subject}</div>
            <div className="text-xs text-gray-500 line-clamp-3">{t.body_text}</div>
            <button onClick={() => setPreview(t)} className="mt-3 text-xs text-blue-600 hover:underline">Preview</button>
          </div>
        ))}
        {templates.length === 0 && (
          <div className="col-span-2 text-center text-gray-400 py-8">No templates yet. Create your first communication template.</div>
        )}
      </div>

      {/* Create Modal */}
      {creating && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-2xl space-y-4">
            <h2 className="text-lg font-bold text-gray-900">New Message Template</h2>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-700">Template Code</label>
                <input value={form.template_code} onChange={(e) => setForm({ ...form, template_code: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="LEVEL1_EMAIL" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Channel</label>
                <select value={form.channel} onChange={(e) => setForm({ ...form, channel: e.target.value as DunningActionType })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  {(["EMAIL", "SMS", "WHATSAPP", "PORTAL_NOTIFICATION"] as DunningActionType[]).map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Language</label>
                <input value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="en" />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Subject</label>
              <input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Body Text</label>
              <div className="text-xs text-gray-400 mb-1">Merge fields: {MERGE_FIELDS.join(", ")}</div>
              <textarea value={form.body_text} onChange={(e) => setForm({ ...form, body_text: e.target.value })}
                rows={6} className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono" />
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setCreating(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button onClick={create} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium">Create</button>
            </div>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {preview && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-xl space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Template Preview — {preview.template_code}</h2>
            <div className="bg-gray-50 rounded-lg p-4 text-sm">
              <div className="font-semibold text-gray-900 mb-3 border-b pb-2">{preview.subject}</div>
              <pre className="text-gray-700 whitespace-pre-wrap text-xs">{preview.body_text}</pre>
            </div>
            <button onClick={() => setPreview(null)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
