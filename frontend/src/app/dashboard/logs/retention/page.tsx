"use client";
import { useEffect, useState } from "react";

interface RetentionPolicy {
  id: string;
  module: string;
  retain_days: number;
  active_flag: boolean;
}

const DEFAULT_MODULES = [
  "auth", "inventory", "sales", "finance", "production",
  "procurement", "quality", "hr", "logistics", "admin",
];

export default function RetentionPoliciesPage() {
  const [policies, setPolicies] = useState<RetentionPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ module: "", retain_days: "365" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    fetch("/api/v1/audit/retention")
      .then((r) => r.json())
      .then(setPolicies)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const save = async () => {
    if (!form.module || !form.retain_days) return;
    setSaving(true);
    try {
      const r = await fetch("/api/v1/audit/retention", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ module: form.module, retain_days: Number(form.retain_days) }),
      });
      if (!r.ok) throw new Error(await r.text());
      setForm({ module: "", retain_days: "365" });
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const COMMON_RETENTIONS = [
    { label: "30 days", days: 30 },
    { label: "90 days", days: 90 },
    { label: "1 year", days: 365 },
    { label: "3 years", days: 1095 },
    { label: "7 years", days: 2555 },
  ];

  return (
    <div className="p-6 space-y-6 max-w-3xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Audit Retention Policies</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Configure how long audit logs are retained per module before purging.
        </p>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* Add / update form */}
      <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Set Retention Policy</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Module</label>
            <input
              list="modules-list"
              value={form.module}
              onChange={(e) => setForm((p) => ({ ...p, module: e.target.value }))}
              placeholder="e.g. finance"
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <datalist id="modules-list">
              {DEFAULT_MODULES.map((m) => <option key={m} value={m} />)}
            </datalist>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Retain Days</label>
            <input
              type="number"
              min={1}
              max={3650}
              value={form.retain_days}
              onChange={(e) => setForm((p) => ({ ...p, retain_days: e.target.value }))}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={save}
              disabled={saving || !form.module || !form.retain_days}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-1.5 rounded disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save Policy"}
            </button>
          </div>
        </div>
        {/* Quick pick */}
        <div className="flex flex-wrap gap-2">
          {COMMON_RETENTIONS.map((r) => (
            <button
              key={r.days}
              onClick={() => setForm((p) => ({ ...p, retain_days: String(r.days) }))}
              className={`text-xs rounded-full border px-3 py-1 transition-colors ${
                form.retain_days === String(r.days)
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-gray-50 text-gray-600 border-gray-300 hover:bg-gray-100"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Existing policies */}
      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50">
          <h2 className="text-sm font-semibold text-gray-700">
            Active Policies
            <span className="ml-2 font-normal text-gray-400">{policies.length} configured</span>
          </h2>
        </div>

        {loading ? (
          <div className="p-6 text-sm text-gray-400 text-center">Loading…</div>
        ) : policies.length === 0 ? (
          <div className="p-6 text-sm text-gray-400 text-center">
            No retention policies configured yet. Add one above.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500">
              <tr>
                <th className="text-left px-4 py-2">Module</th>
                <th className="text-left px-4 py-2">Retain Days</th>
                <th className="text-left px-4 py-2">Approx Retention</th>
                <th className="text-left px-4 py-2">Status</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {policies.map((p) => {
                const years = (p.retain_days / 365).toFixed(1);
                return (
                  <tr key={p.id}>
                    <td className="px-4 py-2.5 font-medium text-gray-900 capitalize">{p.module}</td>
                    <td className="px-4 py-2.5 text-gray-700">{p.retain_days} days</td>
                    <td className="px-4 py-2.5 text-gray-500">{years} year{Number(years) !== 1 ? "s" : ""}</td>
                    <td className="px-4 py-2.5">
                      <span className={`text-xs rounded-full px-2 py-0.5 ${p.active_flag ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                        {p.active_flag ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-2.5">
                      <button
                        onClick={() => setForm({ module: p.module, retain_days: String(p.retain_days) })}
                        className="text-xs text-blue-600 hover:text-blue-800"
                      >
                        Edit
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
        <p className="font-semibold mb-1">Regulatory Guidance</p>
        <p className="text-xs text-blue-700">
          Kenya Companies Act requires financial records for 7 years. KEBS quality logs: 3 years minimum.
          HR records: 5 years. Security/auth logs: 1 year minimum. Set policies accordingly.
          Purge is NOT automatic — policies are advisory until a scheduled purge job is configured.
        </p>
      </div>
    </div>
  );
}
