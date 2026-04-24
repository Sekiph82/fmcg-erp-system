"use client";
import { useEffect, useState } from "react";
import {
  shelfLifeApi, ItemShelfLifeConfig, PickingStrategyConfig,
  STRATEGY_LABEL, ShelfLifeCategory,
} from "@/lib/shelfLife";

const CATEGORIES: ShelfLifeCategory[] = ["raw", "intermediate", "bulk", "finished_goods", "packaging", "other"];
const STRATEGIES = ["fefo", "fifo", "lifo", "manual", "hybrid"] as const;
const BLOCK_POLICIES = ["block", "warn", "allow_with_approval"] as const;
const NEAR_EXPIRY_POLICIES = ["allow", "warn", "require_approval", "block_external"] as const;

export default function FEFOConfigPage() {
  const [configs, setConfigs] = useState<ItemShelfLifeConfig[]>([]);
  const [strategies, setStrategies] = useState<PickingStrategyConfig[]>([]);
  const [showItemModal, setShowItemModal] = useState(false);
  const [showStratModal, setShowStratModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [tab, setTab] = useState<"item" | "strategy">("item");

  const [form, setForm] = useState({
    shelf_life_category: "raw",
    shelf_life_days: "",
    near_expiry_threshold_days: "30",
    min_remaining_days_issue: "",
    min_remaining_days_ship: "",
    picking_strategy_default: "fefo",
    expiry_block_policy: "block",
    near_expiry_issue_policy: "warn",
    near_expiry_ship_policy: "warn",
    allowed_retest: false,
    max_hold_hours: "",
    notes: "",
  });

  const [stratForm, setStratForm] = useState({
    scope: "item_default",
    strategy: "fefo",
    notes: "",
  });

  const load = () => {
    shelfLifeApi.listItemConfigs().then(setConfigs).catch(console.error);
    shelfLifeApi.listPickingStrategies().then(setStrategies).catch(console.error);
  };

  useEffect(() => { load(); }, []);

  const saveItem = async () => {
    setSaving(true);
    try {
      await shelfLifeApi.createItemConfig({
        shelf_life_category: form.shelf_life_category as ShelfLifeCategory,
        shelf_life_days: form.shelf_life_days ? parseInt(form.shelf_life_days) : undefined,
        near_expiry_threshold_days: parseInt(form.near_expiry_threshold_days) || 30,
        min_remaining_days_issue: form.min_remaining_days_issue ? parseInt(form.min_remaining_days_issue) : undefined,
        min_remaining_days_ship: form.min_remaining_days_ship ? parseInt(form.min_remaining_days_ship) : undefined,
        picking_strategy_default: form.picking_strategy_default as any,
        expiry_block_policy: form.expiry_block_policy as any,
        near_expiry_issue_policy: form.near_expiry_issue_policy as any,
        near_expiry_ship_policy: form.near_expiry_ship_policy as any,
        allowed_retest: form.allowed_retest,
        max_hold_hours: form.max_hold_hours || undefined,
        notes: form.notes || undefined,
      } as any);
      setShowItemModal(false);
      load();
    } finally { setSaving(false); }
  };

  const saveStrat = async () => {
    setSaving(true);
    try {
      await shelfLifeApi.createPickingStrategy({
        scope: stratForm.scope as any,
        strategy: stratForm.strategy as any,
        notes: stratForm.notes || undefined,
      } as any);
      setShowStratModal(false);
      load();
    } finally { setSaving(false); }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">FEFO Configuration</h1>
          <p className="text-sm text-gray-500">Shelf-life policies and picking strategy settings</p>
        </div>
        <button
          onClick={() => tab === "item" ? setShowItemModal(true) : setShowStratModal(true)}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700"
        >
          + Add {tab === "item" ? "Item Config" : "Picking Strategy"}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {(["item", "strategy"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded text-sm font-medium ${tab === t ? "bg-white shadow text-gray-800" : "text-gray-500"}`}>
            {t === "item" ? "Item Shelf-Life Config" : "Picking Strategy Overrides"}
          </button>
        ))}
      </div>

      {tab === "item" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                {["Category", "Shelf-Life Days", "Near-Expiry (d)", "Min Issue (d)", "Min Ship (d)", "Strategy", "Block Policy", "Retest"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {configs.length === 0 ? (
                <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No item configs yet</td></tr>
              ) : configs.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{c.shelf_life_category}</td>
                  <td className="px-4 py-3">{c.shelf_life_days ?? "—"}</td>
                  <td className="px-4 py-3">{c.near_expiry_threshold_days}</td>
                  <td className="px-4 py-3">{c.min_remaining_days_issue ?? "—"}</td>
                  <td className="px-4 py-3">{c.min_remaining_days_ship ?? "—"}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded text-xs">{c.picking_strategy_default.toUpperCase()}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${c.expiry_block_policy === "block" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}>
                      {c.expiry_block_policy}
                    </span>
                  </td>
                  <td className="px-4 py-3">{c.allowed_retest ? "Yes" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "strategy" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                {["Scope", "Strategy", "Active", "Notes", "Created"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {strategies.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No strategy overrides configured</td></tr>
              ) : strategies.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{s.scope}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded text-xs">{s.strategy.toUpperCase()}</span>
                  </td>
                  <td className="px-4 py-3">{s.is_active ? "✓" : "✗"}</td>
                  <td className="px-4 py-3 text-gray-500">{s.notes || "—"}</td>
                  <td className="px-4 py-3 text-gray-400">{new Date(s.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Item Config Modal */}
      {showItemModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <h3 className="font-semibold text-gray-800 text-lg">Add Item Shelf-Life Config</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-gray-600">Category</label>
                <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.shelf_life_category} onChange={e => setForm(f => ({ ...f, shelf_life_category: e.target.value }))}>
                  {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Shelf-Life Days</label>
                <input type="number" className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.shelf_life_days} onChange={e => setForm(f => ({ ...f, shelf_life_days: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Near-Expiry Threshold (days)</label>
                <input type="number" className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.near_expiry_threshold_days} onChange={e => setForm(f => ({ ...f, near_expiry_threshold_days: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Min Remaining for Issue (days)</label>
                <input type="number" className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.min_remaining_days_issue} onChange={e => setForm(f => ({ ...f, min_remaining_days_issue: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Min Remaining for Shipment (days)</label>
                <input type="number" className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.min_remaining_days_ship} onChange={e => setForm(f => ({ ...f, min_remaining_days_ship: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Default Picking Strategy</label>
                <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.picking_strategy_default} onChange={e => setForm(f => ({ ...f, picking_strategy_default: e.target.value }))}>
                  {STRATEGIES.map(s => <option key={s} value={s}>{STRATEGY_LABEL[s]}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Expiry Block Policy</label>
                <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.expiry_block_policy} onChange={e => setForm(f => ({ ...f, expiry_block_policy: e.target.value }))}>
                  {BLOCK_POLICIES.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Near-Expiry Issue Policy</label>
                <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.near_expiry_issue_policy} onChange={e => setForm(f => ({ ...f, near_expiry_issue_policy: e.target.value }))}>
                  {NEAR_EXPIRY_POLICIES.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Near-Expiry Shipment Policy</label>
                <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.near_expiry_ship_policy} onChange={e => setForm(f => ({ ...f, near_expiry_ship_policy: e.target.value }))}>
                  {NEAR_EXPIRY_POLICIES.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Max Hold Hours (bulk/intermediate)</label>
                <input type="number" className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.max_hold_hours} onChange={e => setForm(f => ({ ...f, max_hold_hours: e.target.value }))} />
              </div>
              <div className="flex items-center gap-2 mt-4">
                <input type="checkbox" id="retest" checked={form.allowed_retest}
                  onChange={e => setForm(f => ({ ...f, allowed_retest: e.target.checked }))} />
                <label htmlFor="retest" className="text-sm text-gray-700">Allow Retest for this item</label>
              </div>
              <div className="col-span-2">
                <label className="text-xs font-medium text-gray-600">Notes</label>
                <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
              </div>
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <button onClick={() => setShowItemModal(false)} className="px-4 py-2 text-sm border rounded-lg">Cancel</button>
              <button onClick={saveItem} disabled={saving}
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">
                {saving ? "Saving…" : "Save Config"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Strategy Modal */}
      {showStratModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
            <h3 className="font-semibold text-gray-800 text-lg">Add Picking Strategy Override</h3>
            <div>
              <label className="text-xs font-medium text-gray-600">Scope</label>
              <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={stratForm.scope} onChange={e => setStratForm(f => ({ ...f, scope: e.target.value }))}>
                {["item_warehouse_location","item_warehouse","item_default","warehouse_default","system_fallback"].map(s =>
                  <option key={s} value={s}>{s}</option>
                )}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Strategy</label>
              <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={stratForm.strategy} onChange={e => setStratForm(f => ({ ...f, strategy: e.target.value }))}>
                {STRATEGIES.map(s => <option key={s} value={s}>{STRATEGY_LABEL[s]}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Notes</label>
              <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={stratForm.notes} onChange={e => setStratForm(f => ({ ...f, notes: e.target.value }))} />
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowStratModal(false)} className="px-4 py-2 text-sm border rounded-lg">Cancel</button>
              <button onClick={saveStrat} disabled={saving}
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">
                {saving ? "Saving…" : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
