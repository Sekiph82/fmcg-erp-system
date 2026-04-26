"use client";
import { useState, useEffect } from "react";
import { plApi, PLDiscountRule, PLDiscountType, PLDiscountScope } from "@/lib/price_list";

export default function DiscountRules() {
  const [rules, setRules] = useState<PLDiscountRule[]>([]);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    rule_code: "", rule_name: "", scope: "LINE" as PLDiscountScope,
    discount_type: "PERCENTAGE" as PLDiscountType, discount_value: "",
    max_discount_pct: "", requires_approval: false, min_margin_pct: "",
    applies_to_channel: "", reason_required: false, notes: "",
  });

  const load = () => plApi.listDiscountRules(false).then(setRules);
  useEffect(() => { load(); }, []);

  const create = async () => {
    await plApi.createDiscountRule({
      ...form,
      discount_value: Number(form.discount_value),
      max_discount_pct: form.max_discount_pct ? Number(form.max_discount_pct) : undefined,
      min_margin_pct: form.min_margin_pct ? Number(form.min_margin_pct) : undefined,
    } as any);
    setCreating(false);
    load();
  };

  const SCOPE_COLORS: Record<PLDiscountScope, string> = {
    LINE: "bg-blue-100 text-blue-800",
    ORDER: "bg-indigo-100 text-indigo-800",
    CUSTOMER: "bg-purple-100 text-purple-800",
    VOLUME: "bg-teal-100 text-teal-800",
    CHANNEL: "bg-orange-100 text-orange-800",
    MANUAL: "bg-gray-100 text-gray-700",
    PROMOTIONAL: "bg-yellow-100 text-yellow-800",
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Discount Rules</h1>
          <p className="text-sm text-gray-500 mt-1">Configurable discount policies with approval thresholds and margin guards</p>
        </div>
        <button onClick={() => setCreating(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
          + New Rule
        </button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {["Code", "Name", "Scope", "Type", "Value", "Max Disc %", "Min Margin", "Approval Req.", "Reason Req.", "Active"].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rules.length === 0 ? (
              <tr><td colSpan={10} className="px-4 py-8 text-center text-gray-400">No discount rules defined.</td></tr>
            ) : rules.map((r) => (
              <tr key={r.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs text-gray-700">{r.rule_code}</td>
                <td className="px-4 py-3 font-medium text-gray-900">{r.rule_name}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${SCOPE_COLORS[r.scope]}`}>{r.scope}</span>
                </td>
                <td className="px-4 py-3 text-gray-600">{r.discount_type.replace(/_/g, " ")}</td>
                <td className="px-4 py-3 font-mono font-semibold">
                  {r.discount_type === "PERCENTAGE" ? `${r.discount_value}%` : Number(r.discount_value).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-gray-500">{r.max_discount_pct ? `${r.max_discount_pct}%` : "—"}</td>
                <td className="px-4 py-3 text-gray-500">{r.min_margin_pct ? `${r.min_margin_pct}%` : "—"}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`text-xs px-1.5 py-0.5 rounded-full ${r.requires_approval ? "bg-yellow-100 text-yellow-800" : "bg-gray-100 text-gray-500"}`}>
                    {r.requires_approval ? "Yes" : "No"}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`text-xs px-1.5 py-0.5 rounded-full ${r.reason_required ? "bg-orange-100 text-orange-800" : "bg-gray-100 text-gray-500"}`}>
                    {r.reason_required ? "Yes" : "No"}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`text-xs px-1.5 py-0.5 rounded-full ${r.active_flag ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                    {r.active_flag ? "Active" : "Off"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {creating && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-lg space-y-4">
            <h2 className="text-lg font-bold text-gray-900">New Discount Rule</h2>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-700">Rule Code</label>
                <input value={form.rule_code} onChange={(e) => setForm({ ...form, rule_code: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="CHAN-DISC-5" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Scope</label>
                <select value={form.scope} onChange={(e) => setForm({ ...form, scope: e.target.value as PLDiscountScope })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  {(["LINE", "ORDER", "CUSTOMER", "VOLUME", "CHANNEL", "MANUAL", "PROMOTIONAL"] as PLDiscountScope[]).map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Rule Name</label>
              <input value={form.rule_name} onChange={(e) => setForm({ ...form, rule_name: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-700">Discount Type</label>
                <select value={form.discount_type} onChange={(e) => setForm({ ...form, discount_type: e.target.value as PLDiscountType })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  <option value="PERCENTAGE">Percentage</option>
                  <option value="FIXED_AMOUNT">Fixed Amount</option>
                  <option value="OVERRIDE_PRICE">Override Price</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Discount Value</label>
                <input type="number" value={form.discount_value} onChange={(e) => setForm({ ...form, discount_value: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Max Discount %</label>
                <input type="number" value={form.max_discount_pct} onChange={(e) => setForm({ ...form, max_discount_pct: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Min Margin % (floor)</label>
              <input type="number" value={form.min_margin_pct} onChange={(e) => setForm({ ...form, min_margin_pct: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.requires_approval} onChange={(e) => setForm({ ...form, requires_approval: e.target.checked })} />
                Requires Approval
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.reason_required} onChange={(e) => setForm({ ...form, reason_required: e.target.checked })} />
                Reason Required
              </label>
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setCreating(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button onClick={create} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium">Create</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
