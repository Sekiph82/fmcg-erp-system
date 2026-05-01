"use client";

import { useState, useEffect, useCallback } from "react";
import { putawayApi, PutawayRule, PutawayRuleType } from "@/lib/putaway";
import { wmsApi } from "@/lib/wms";

const RULE_TYPE_LABELS: Record<PutawayRuleType, string> = {
  FIXED: "Fixed Location",
  ZONE: "Zone-Based",
  CATEGORY: "Category-Based",
  RANDOM: "Random Storage",
  NEAREST: "Nearest Empty",
};

export default function PutawayRulesPage() {
  const [rules, setRules] = useState<PutawayRule[]>([]);
  const [zones, setZones] = useState<any[]>([]);
  const [warehouses, setWarehouses] = useState<any[]>([]);
  const [filterWarehouse, setFilterWarehouse] = useState("");
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingRule, setEditingRule] = useState<PutawayRule | null>(null);
  const [form, setForm] = useState({
    rule_code: "",
    warehouse_id: "",
    rule_type: "ZONE" as PutawayRuleType,
    priority: "100",
    category: "",
    zone_id: "",
    is_active: true,
    notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [aiInsights, setAiInsights] = useState<any>(null);
  const [aiLoading, setAiLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await putawayApi.listRules({
        warehouse_id: filterWarehouse || undefined,
      });
      setRules(data);
    } finally {
      setLoading(false);
    }
  }, [filterWarehouse]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    wmsApi.listZones().then((zs) => {
      setZones(zs);
      const whMap: Record<string, { id: string; name: string }> = {};
      zs.forEach((z) => {
        if (z.warehouse_id) whMap[z.warehouse_id] = { id: z.warehouse_id, name: z.warehouse_name || z.warehouse_id };
      });
      setWarehouses(Object.values(whMap));
    });
  }, []);

  const openCreate = () => {
    setEditingRule(null);
    setForm({ rule_code: "", warehouse_id: "", rule_type: "ZONE", priority: "100", category: "", zone_id: "", is_active: true, notes: "" });
    setError("");
    setShowModal(true);
  };

  const openEdit = (rule: PutawayRule) => {
    setEditingRule(rule);
    setForm({
      rule_code: rule.rule_code,
      warehouse_id: rule.warehouse_id,
      rule_type: rule.rule_type,
      priority: String(rule.priority),
      category: rule.category || "",
      zone_id: rule.zone_id || "",
      is_active: rule.is_active,
      notes: rule.notes || "",
    });
    setError("");
    setShowModal(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload: any = {
        rule_code: form.rule_code,
        warehouse_id: form.warehouse_id,
        rule_type: form.rule_type,
        priority: parseInt(form.priority),
        category: form.category || undefined,
        zone_id: form.zone_id || undefined,
        is_active: form.is_active,
        notes: form.notes || undefined,
      };
      if (editingRule) {
        await putawayApi.updateRule(editingRule.id, payload);
      } else {
        await putawayApi.createRule(payload);
      }
      setShowModal(false);
      load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const loadSpaceOptimizer = async () => {
    if (!filterWarehouse) return;
    setAiLoading(true);
    try {
      const res = await putawayApi.spaceOptimizer(filterWarehouse);
      setAiInsights(res);
    } finally {
      setAiLoading(false);
    }
  };

  const filteredZones = zones.filter((z) => !form.warehouse_id || z.warehouse_id === form.warehouse_id);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Putaway Rules</h1>
          <p className="text-sm text-gray-500 mt-1">Configure location assignment strategies</p>
        </div>
        <button
          onClick={openCreate}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          + New Rule
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          value={filterWarehouse}
          onChange={(e) => setFilterWarehouse(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Warehouses</option>
          {warehouses.map((w) => (
            <option key={w.id} value={w.id}>{w.name}</option>
          ))}
        </select>
        {filterWarehouse && (
          <button
            onClick={loadSpaceOptimizer}
            disabled={aiLoading}
            className="px-3 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
          >
            {aiLoading ? "Analyzing…" : "AI Space Optimizer"}
          </button>
        )}
      </div>

      {/* Space Optimizer AI Output */}
      {aiInsights && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-purple-800">Space Optimizer Analysis</h3>
            <span className="text-xs text-purple-600">
              Overall utilization: <strong>{aiInsights.overall_utilization_pct}%</strong>
              {" · "}{aiInsights.available_locations} locations free
            </span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {(aiInsights.zone_breakdown || []).map((z: any) => (
              <div key={z.zone_code} className="bg-white rounded border p-2 text-xs">
                <p className="font-semibold">{z.zone_name}</p>
                <p className="text-gray-500">{z.utilization_pct}% — {z.occupied_locations}/{z.total_locations} used</p>
              </div>
            ))}
          </div>
          <div>
            <p className="text-xs font-semibold text-purple-700 mb-1">Insights:</p>
            {(aiInsights.ai_insights || []).map((i: string, idx: number) => (
              <p key={idx} className="text-xs text-purple-700">• {i}</p>
            ))}
          </div>
        </div>
      )}

      {/* Rules Table */}
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
            <tr>
              <th className="px-4 py-3 text-left">Priority</th>
              <th className="px-4 py-3 text-left">Code</th>
              <th className="px-4 py-3 text-left">Type</th>
              <th className="px-4 py-3 text-left">Zone / Location</th>
              <th className="px-4 py-3 text-left">Category</th>
              <th className="px-4 py-3 text-left">Warehouse</th>
              <th className="px-4 py-3 text-left">Active</th>
              <th className="px-4 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : rules.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No putaway rules configured</td></tr>
            ) : (
              rules.map((rule) => (
                <tr key={rule.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-semibold text-gray-700">{rule.priority}</td>
                  <td className="px-4 py-3 font-mono text-xs">{rule.rule_code}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-xs">
                      {RULE_TYPE_LABELS[rule.rule_type]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-xs">
                    {rule.zone_name || rule.location_code || "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{rule.category || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{rule.warehouse_name || "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${rule.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {rule.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => openEdit(rule)}
                      className="text-blue-600 hover:underline text-xs"
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Rule Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
            <h2 className="text-lg font-semibold mb-4">{editingRule ? "Edit Rule" : "New Putaway Rule"}</h2>
            <form onSubmit={handleSave} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Rule Code *</label>
                  <input
                    required
                    disabled={!!editingRule}
                    value={form.rule_code}
                    onChange={(e) => setForm({ ...form, rule_code: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 text-sm disabled:bg-gray-50"
                    placeholder="e.g. COLD-ZONE"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Priority *</label>
                  <input
                    required
                    type="number"
                    value={form.priority}
                    onChange={(e) => setForm({ ...form, priority: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                    placeholder="Lower = higher priority"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Warehouse *</label>
                  <select
                    required
                    value={form.warehouse_id}
                    onChange={(e) => setForm({ ...form, warehouse_id: e.target.value, zone_id: "" })}
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                  >
                    <option value="">Select…</option>
                    {warehouses.map((w) => (
                      <option key={w.id} value={w.id}>{w.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Rule Type *</label>
                  <select
                    required
                    value={form.rule_type}
                    onChange={(e) => setForm({ ...form, rule_type: e.target.value as PutawayRuleType })}
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                  >
                    {(Object.keys(RULE_TYPE_LABELS) as PutawayRuleType[]).map((t) => (
                      <option key={t} value={t}>{RULE_TYPE_LABELS[t]}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Target Zone</label>
                <select
                  value={form.zone_id}
                  onChange={(e) => setForm({ ...form, zone_id: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                >
                  <option value="">No zone restriction</option>
                  {filteredZones.map((z) => (
                    <option key={z.id} value={z.id}>{z.name} ({z.zone_type})</option>
                  ))}
                </select>
              </div>
              {form.rule_type === "CATEGORY" && (
                <div>
                  <label className="block text-sm font-medium mb-1">Category</label>
                  <input
                    value={form.category}
                    onChange={(e) => setForm({ ...form, category: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                    placeholder="e.g. COLD_ITEMS"
                  />
                </div>
              )}
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={form.is_active}
                  onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  className="rounded"
                />
                <label htmlFor="is_active" className="text-sm">Active</label>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Notes</label>
                <textarea
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  rows={2}
                />
              </div>
              {error && <p className="text-red-600 text-sm">{error}</p>}
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? "Saving…" : editingRule ? "Update Rule" : "Create Rule"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
