"use client";
import { useEffect, useState } from "react";

interface RLSPolicy {
  policy_id: string;
  policy_name: string;
  data_source: string;
  scope: "user" | "role";
  principal: string;
  filter_field: string;
  operator: string;
  filter_value: string;
  active_flag: boolean;
  description: string | null;
  created_by: string | null;
  created_at: string;
}

interface NewPolicyForm {
  policy_name: string;
  data_source: string;
  scope: "user" | "role";
  principal: string;
  filter_field: string;
  operator: string;
  filter_value: string;
  description: string;
}

const OPERATORS = ["eq", "neq", "gt", "lt", "gte", "lte", "in", "like"];

const BASE = "/api/v1/reports-builder";

async function apiListPolicies(activeOnly: boolean): Promise<RLSPolicy[]> {
  const r = await fetch(`${BASE}/rls?active_only=${activeOnly}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function apiCreatePolicy(body: NewPolicyForm): Promise<RLSPolicy> {
  const r = await fetch(`${BASE}/rls`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function apiTogglePolicy(id: string, active: boolean): Promise<void> {
  await fetch(`${BASE}/rls/${id}?active_flag=${active}`, { method: "PATCH" });
}

async function apiDeletePolicy(id: string): Promise<void> {
  await fetch(`${BASE}/rls/${id}`, { method: "DELETE" });
}

const EMPTY_FORM: NewPolicyForm = {
  policy_name: "",
  data_source: "",
  scope: "user",
  principal: "",
  filter_field: "",
  operator: "eq",
  filter_value: "",
  description: "",
};

export default function RLSManagementPage() {
  const [policies, setPolicies] = useState<RLSPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<NewPolicyForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [activeOnly, setActiveOnly] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    apiListPolicies(activeOnly).then(setPolicies).catch((e) => setError(String(e))).finally(() => setLoading(false));
  };

  useEffect(load, [activeOnly]);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      await apiCreatePolicy(form);
      setForm(EMPTY_FORM);
      setShowForm(false);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const toggle = async (id: string, current: boolean) => {
    await apiTogglePolicy(id, !current);
    load();
  };

  const del = async (id: string) => {
    if (!confirm("Delete this RLS policy?")) return;
    await apiDeletePolicy(id);
    load();
  };

  const fmtDate = (iso: string) =>
    new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Row-Level Security</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Control which data rows each user or role can see in reports.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={activeOnly}
              onChange={(e) => setActiveOnly(e.target.checked)}
              className="h-3.5 w-3.5"
            />
            Active only
          </label>
          <button
            onClick={() => setShowForm(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded"
          >
            + Add Policy
          </button>
        </div>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* Create form */}
      {showForm && (
        <div className="bg-white border rounded-lg p-5 shadow-sm space-y-4">
          <h2 className="text-sm font-semibold text-gray-700">New RLS Policy</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { label: "Policy Name *", key: "policy_name", placeholder: "e.g. Kenya Region Only" },
              { label: "Data Source *", key: "data_source", placeholder: "e.g. sales_orders" },
              { label: "Principal *", key: "principal", placeholder: "user_id or role name" },
              { label: "Filter Field *", key: "filter_field", placeholder: "e.g. region" },
              { label: "Filter Value *", key: "filter_value", placeholder: "e.g. KENYA" },
              { label: "Description", key: "description", placeholder: "Optional" },
            ].map(({ label, key, placeholder }) => (
              <div key={key}>
                <label className="text-xs text-gray-500 block mb-1">{label}</label>
                <input
                  type="text"
                  placeholder={placeholder}
                  value={(form as unknown as Record<string, string>)[key]}
                  onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500 block mb-1">Scope</label>
              <select
                value={form.scope}
                onChange={(e) => setForm((p) => ({ ...p, scope: e.target.value as "user" | "role" }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="user">User</option>
                <option value="role">Role</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Operator</label>
              <select
                value={form.operator}
                onChange={(e) => setForm((p) => ({ ...p, operator: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {OPERATORS.map((op) => <option key={op} value={op}>{op}</option>)}
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={save}
              disabled={saving || !form.policy_name || !form.data_source || !form.principal || !form.filter_field || !form.filter_value}
              className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded disabled:opacity-50"
            >
              {saving ? "Saving…" : "Create Policy"}
            </button>
            <button
              onClick={() => { setShowForm(false); setForm(EMPTY_FORM); }}
              className="border border-gray-300 text-sm text-gray-600 px-4 py-2 rounded hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Policies table */}
      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50">
          <h2 className="text-sm font-semibold text-gray-700">
            RLS Policies
            <span className="ml-2 font-normal text-gray-400">{policies.length} {activeOnly ? "active" : "total"}</span>
          </h2>
        </div>

        {loading ? (
          <div className="p-6 text-sm text-gray-400 text-center">Loading…</div>
        ) : policies.length === 0 ? (
          <div className="p-6 text-sm text-gray-400 text-center">
            No RLS policies yet. Add one to restrict report data by user or role.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500">
                <tr>
                  <th className="text-left px-4 py-2">Policy Name</th>
                  <th className="text-left px-4 py-2">Data Source</th>
                  <th className="text-left px-4 py-2">Scope</th>
                  <th className="text-left px-4 py-2">Principal</th>
                  <th className="text-left px-4 py-2">Filter</th>
                  <th className="text-left px-4 py-2">Status</th>
                  <th className="text-left px-4 py-2">Created</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {policies.map((p) => (
                  <tr key={p.policy_id} className={!p.active_flag ? "opacity-50" : ""}>
                    <td className="px-4 py-2.5 font-medium text-gray-900">{p.policy_name}</td>
                    <td className="px-4 py-2.5 font-mono text-xs text-gray-600">{p.data_source}</td>
                    <td className="px-4 py-2.5">
                      <span className={`text-xs rounded-full px-2 py-0.5 ${p.scope === "user" ? "bg-blue-100 text-blue-700" : "bg-purple-100 text-purple-700"}`}>
                        {p.scope}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-gray-600 font-mono text-xs">{p.principal}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-600 font-mono">
                      {p.filter_field} <span className="text-gray-400">{p.operator}</span> {p.filter_value}
                    </td>
                    <td className="px-4 py-2.5">
                      {p.active_flag ? (
                        <span className="text-green-700 bg-green-100 text-xs rounded-full px-2 py-0.5">Active</span>
                      ) : (
                        <span className="text-gray-500 bg-gray-100 text-xs rounded-full px-2 py-0.5">Inactive</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-gray-400 text-xs">{fmtDate(p.created_at)}</td>
                    <td className="px-4 py-2.5">
                      <div className="flex gap-2">
                        <button
                          onClick={() => toggle(p.policy_id, p.active_flag)}
                          className="text-xs text-blue-600 hover:text-blue-800"
                        >
                          {p.active_flag ? "Disable" : "Enable"}
                        </button>
                        <button
                          onClick={() => del(p.policy_id)}
                          className="text-xs text-red-600 hover:text-red-800"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Info box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
        <p className="font-semibold mb-1">How Row-Level Security Works</p>
        <p className="text-xs text-blue-700">
          RLS policies restrict which rows a user or role can see in reports. When a report is run,
          the system checks active policies for the current user and their roles, then applies the
          corresponding filters automatically. Use <strong>scope=user</strong> to target individual
          users, <strong>scope=role</strong> to apply to everyone with that role.
        </p>
      </div>
    </div>
  );
}
