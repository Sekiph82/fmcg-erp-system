"use client";
import { useEffect, useState } from "react";
import { shelfLifeApi, CustomerShelfLifeRule } from "@/lib/shelfLife";

export default function CustomerRulesPage() {
  const [rules, setRules] = useState<CustomerShelfLifeRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    customer_id: "",
    customer_group: "",
    country_code: "",
    channel: "",
    product_id: "",
    rule_type: "fixed_days",
    min_remaining_days: "",
    min_pct_remaining: "",
    block_policy: "block",
    notes: "",
  });

  const load = () => {
    shelfLifeApi.listCustomerRules().then(setRules).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await shelfLifeApi.createCustomerRule({
        customer_id: form.customer_id || undefined,
        customer_group: form.customer_group || undefined,
        country_code: form.country_code || undefined,
        channel: form.channel || undefined,
        product_id: form.product_id || undefined,
        rule_type: form.rule_type as any,
        min_remaining_days: form.min_remaining_days ? parseInt(form.min_remaining_days) : undefined,
        min_pct_remaining: form.min_pct_remaining || undefined,
        block_policy: form.block_policy as any,
        notes: form.notes || undefined,
      } as any);
      setShowModal(false);
      load();
    } finally { setSaving(false); }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Customer Shelf-Life Rules</h1>
          <p className="text-sm text-gray-500">Customer, channel, and country-specific minimum remaining shelf-life requirements</p>
        </div>
        <button onClick={() => setShowModal(true)}
          className="px-4 py-2 text-sm bg-pink-600 text-white rounded-lg hover:bg-pink-700">
          + Add Rule
        </button>
      </div>

      {/* Info */}
      <div className="bg-pink-50 border border-pink-200 rounded-xl p-4">
        <p className="text-sm font-semibold text-pink-800 mb-1">Rule Priority</p>
        <p className="text-xs text-pink-700">Customer + Product &gt; Customer only &gt; Customer Group &gt; Country &gt; Channel. Most specific rule wins at validation time.</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              {["Customer","Group","Country","Channel","Rule Type","Min Days","Min %","Block Policy","Active"].map(h => (
                <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : rules.length === 0 ? (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">No customer shelf-life rules configured</td></tr>
            ) : rules.map(r => (
              <tr key={r.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">{r.customer_id ? r.customer_id.slice(0,8) : "—"}</td>
                <td className="px-4 py-3">{r.customer_group || "—"}</td>
                <td className="px-4 py-3">{r.country_code || "—"}</td>
                <td className="px-4 py-3">{r.channel || "—"}</td>
                <td className="px-4 py-3">
                  <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">{r.rule_type}</span>
                </td>
                <td className="px-4 py-3 font-medium">{r.min_remaining_days ? `${r.min_remaining_days}d` : "—"}</td>
                <td className="px-4 py-3">{r.min_pct_remaining ? `${r.min_pct_remaining}%` : "—"}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded text-xs ${r.block_policy === "block" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}>
                    {r.block_policy}
                  </span>
                </td>
                <td className="px-4 py-3">{r.is_active ? <span className="text-green-600">✓</span> : <span className="text-gray-400">—</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 space-y-4">
            <h3 className="font-semibold text-gray-800">Add Customer Shelf-Life Rule</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-gray-600">Customer ID (UUID)</label>
                <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.customer_id} onChange={e => setForm(f => ({ ...f, customer_id: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Customer Group</label>
                <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.customer_group} onChange={e => setForm(f => ({ ...f, customer_group: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Country Code</label>
                <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm" placeholder="e.g. KE, UG, TZ"
                  value={form.country_code} onChange={e => setForm(f => ({ ...f, country_code: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Channel</label>
                <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm" placeholder="e.g. export, domestic"
                  value={form.channel} onChange={e => setForm(f => ({ ...f, channel: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Product ID</label>
                <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.product_id} onChange={e => setForm(f => ({ ...f, product_id: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Rule Type</label>
                <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.rule_type} onChange={e => setForm(f => ({ ...f, rule_type: e.target.value }))}>
                  <option value="fixed_days">Fixed Days</option>
                  <option value="percentage">Percentage</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Min Remaining Days</label>
                <input type="number" className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.min_remaining_days} onChange={e => setForm(f => ({ ...f, min_remaining_days: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Min % Remaining</label>
                <input type="number" className="mt-1 w-full border rounded-lg px-3 py-2 text-sm" placeholder="e.g. 70"
                  value={form.min_pct_remaining} onChange={e => setForm(f => ({ ...f, min_pct_remaining: e.target.value }))} />
              </div>
              <div className="col-span-2">
                <label className="text-xs font-medium text-gray-600">Block Policy</label>
                <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.block_policy} onChange={e => setForm(f => ({ ...f, block_policy: e.target.value }))}>
                  <option value="block">Hard Block</option>
                  <option value="warn">Warn Only</option>
                  <option value="allow_with_approval">Allow with Approval</option>
                </select>
              </div>
              <div className="col-span-2">
                <label className="text-xs font-medium text-gray-600">Notes</label>
                <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 text-sm border rounded-lg">Cancel</button>
              <button onClick={handleSave} disabled={saving}
                className="px-4 py-2 text-sm bg-pink-600 text-white rounded-lg hover:bg-pink-700 disabled:opacity-50">
                {saving ? "Saving…" : "Save Rule"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
