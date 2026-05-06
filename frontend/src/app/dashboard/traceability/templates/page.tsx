"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { traceApi, RecallTemplate, RecallAudience } from "@/lib/traceability";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

const AUDIENCE_COLOR: Record<RecallAudience, "red" | "blue" | "yellow" | "gray" | "green"> = {
  CONSUMER:  "red",
  RETAILER:  "blue",
  REGULATOR: "yellow",
  INTERNAL:  "gray",
  MEDIA:     "green",
};

const AUDIENCES: RecallAudience[] = ["CONSUMER", "RETAILER", "REGULATOR", "INTERNAL", "MEDIA"];

export default function RecallTemplatesPage() {
  const qc = useQueryClient();
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<RecallTemplate | null>(null);
  const [filterAudience, setFilterAudience] = useState<RecallAudience | "">("");

  const { data: templates = [], isLoading } = useQuery({
    queryKey: ["recall-templates", filterAudience],
    queryFn: () => traceApi.listTemplates({ audience: filterAudience || undefined, active_only: false }),
  });

  const toggleActive = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      traceApi.updateTemplate(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recall-templates"] }),
  });

  const filtered = filterAudience ? templates.filter((t) => t.audience === filterAudience) : templates;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Recall Communication Templates</h1>
          <p className="text-sm text-gray-500 mt-1">Predefined messages for consumer/retailer/regulator notifications</p>
        </div>
        <Button onClick={() => { setEditing(null); setShowModal(true); }}>+ New Template</Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-5 gap-3">
        {AUDIENCES.map((a) => {
          const count = templates.filter((t) => t.audience === a && t.is_active).length;
          return (
            <div
              key={a}
              className={`bg-white rounded-lg border p-3 text-center cursor-pointer hover:border-indigo-300 ${filterAudience === a ? "border-indigo-500" : ""}`}
              onClick={() => setFilterAudience(filterAudience === a ? "" : a)}
            >
              <p className="text-xl font-bold text-gray-800">{count}</p>
              <Badge label={a} variant={AUDIENCE_COLOR[a]} />
            </div>
          );
        })}
      </div>

      <div className="bg-white rounded-lg border">
        <div className="px-5 py-3 border-b font-semibold text-gray-800">
          Templates ({filtered.length})
        </div>
        {isLoading ? (
          <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-4 py-2 text-left">Name</th>
                <th className="px-4 py-2 text-left">Audience</th>
                <th className="px-4 py-2 text-left">Channel</th>
                <th className="px-4 py-2 text-left">Subject</th>
                <th className="px-4 py-2 text-left">Recall Type</th>
                <th className="px-4 py-2 text-center">Active</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.map((t) => (
                <tr key={t.id} className={`hover:bg-gray-50 ${!t.is_active ? "opacity-50" : ""}`}>
                  <td className="px-4 py-2.5 font-medium text-gray-800">{t.name}</td>
                  <td className="px-4 py-2.5">
                    <Badge label={t.audience} variant={AUDIENCE_COLOR[t.audience]} />
                  </td>
                  <td className="px-4 py-2.5 text-gray-500 text-xs">{t.channel}</td>
                  <td className="px-4 py-2.5 text-gray-700 truncate max-w-xs">{t.subject}</td>
                  <td className="px-4 py-2.5 text-gray-500 text-xs">{t.recall_type ?? "All"}</td>
                  <td className="px-4 py-2.5 text-center">
                    <button
                      className={`text-xs px-2 py-0.5 rounded font-medium ${t.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}
                      onClick={() => toggleActive.mutate({ id: t.id, is_active: !t.is_active })}
                    >
                      {t.is_active ? "Active" : "Inactive"}
                    </button>
                  </td>
                  <td className="px-4 py-2.5">
                    <button
                      className="text-xs text-indigo-600 hover:underline"
                      onClick={() => { setEditing(t); setShowModal(true); }}
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={7} className="px-5 py-8 text-center text-gray-400">No templates — create your first template</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {showModal && (
        <TemplateModal
          initial={editing}
          onClose={() => { setShowModal(false); setEditing(null); }}
          onSave={() => { qc.invalidateQueries({ queryKey: ["recall-templates"] }); setShowModal(false); setEditing(null); }}
        />
      )}
    </div>
  );
}

function TemplateModal({
  initial, onClose, onSave,
}: { initial: RecallTemplate | null; onClose: () => void; onSave: () => void }) {
  const [form, setForm] = useState({
    name:          initial?.name ?? "",
    audience:      initial?.audience ?? "CONSUMER" as RecallAudience,
    recall_type:   initial?.recall_type ?? "",
    severity_level: initial?.severity_level ?? "",
    subject:       initial?.subject ?? "",
    body:          initial?.body ?? "",
    channel:       initial?.channel ?? "EMAIL",
    language:      initial?.language ?? "en",
  });
  const [saving, setSaving] = useState(false);
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  async function save() {
    setSaving(true);
    try {
      if (initial) {
        await traceApi.updateTemplate(initial.id, { name: form.name, subject: form.subject, body: form.body, channel: form.channel });
      } else {
        await traceApi.createTemplate({
          ...form,
          recall_type: form.recall_type || undefined,
          severity_level: form.severity_level || undefined,
        } as Omit<RecallTemplate, "id" | "is_active" | "created_at">);
      }
      onSave();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 space-y-4 max-h-[90vh] overflow-y-auto">
        <h2 className="font-semibold text-lg">{initial ? "Edit Template" : "New Template"}</h2>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.name} onChange={(e) => set("name", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Audience</label>
              <select className="w-full border rounded px-3 py-2 text-sm" value={form.audience} onChange={(e) => set("audience", e.target.value)} disabled={!!initial}>
                {AUDIENCES.map((a) => <option key={a} value={a}>{a}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Channel</label>
              <select className="w-full border rounded px-3 py-2 text-sm" value={form.channel} onChange={(e) => set("channel", e.target.value)}>
                {["EMAIL", "SMS", "WHATSAPP", "LETTER"].map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Recall Type (opt.)</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.recall_type} onChange={(e) => set("recall_type", e.target.value)} placeholder="All types" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Severity (opt.)</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.severity_level} onChange={(e) => set("severity_level", e.target.value)} placeholder="All levels" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Subject</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.subject} onChange={(e) => set("subject", e.target.value)} placeholder="Use {{recall_no}}, {{product}}, {{lot}}" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Body</label>
            <p className="text-xs text-gray-400 mb-1">Placeholders: {"{{recall_no}}"} {"{{product}}"} {"{{lot}}"} {"{{date}}"} {"{{company}}"}</p>
            <textarea className="w-full border rounded px-3 py-2 text-sm" rows={6} value={form.body} onChange={(e) => set("body", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={saving} onClick={save} disabled={!form.name.trim() || !form.subject.trim()}>Save</Button>
        </div>
      </div>
    </div>
  );
}
