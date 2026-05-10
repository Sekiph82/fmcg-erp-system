"use client";

import { useCallback, useState, useEffect } from "react";
import { secondarySalesApi, InventorySnapshot } from "@/lib/secondarySales";

export default function DistributorInventoryPage() {
  const [snapshots, setSnapshots] = useState<InventorySnapshot[]>([]);
  const [distributors, setDistributors] = useState<{ id: string; name: string }[]>([]);
  const [filterDist, setFilterDist] = useState("");
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({
    distributor_id: "",
    product_id: "",
    stock_qty: "",
    snapshot_date: new Date().toISOString().split("T")[0],
    notes: "",
  });
  const [products, setProducts] = useState<{ id: string; sku: string; name: string }[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await secondarySalesApi.listSnapshots({
        distributor_id: filterDist || undefined,
      });
      setSnapshots(data);
    } finally {
      setLoading(false);
    }
  }, [filterDist]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    import("@/lib/api").then(({ apiClient }) => {
      apiClient.get("/api/v1/distributors/").then((res) => {
        const data = res.data?.data ?? res.data;
        setDistributors((data || []).map((d: any) => ({ id: d.id, name: d.name })));
      });
      apiClient.get("/api/v1/products/", { params: { limit: 500 } }).then((res) => {
        const data = res.data?.data ?? res.data;
        setProducts((data || []).map((p: any) => ({ id: p.id, sku: p.sku, name: p.name })));
      });
    });
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await secondarySalesApi.createSnapshot({
        distributor_id: form.distributor_id,
        product_id: form.product_id,
        stock_qty: parseFloat(form.stock_qty),
        snapshot_date: form.snapshot_date,
        notes: form.notes || undefined,
      });
      setShowModal(false);
      setForm({ distributor_id: "", product_id: "", stock_qty: "", snapshot_date: new Date().toISOString().split("T")[0], notes: "" });
      load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const totalStock = snapshots.reduce((s, snap) => s + snap.stock_qty, 0);
  const atRisk = snapshots.filter((s) => s.days_of_stock != null && Number(s.days_of_stock) > 60).length;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Distributor Inventory</h1>
          <p className="text-sm text-gray-500 mt-1">Stock snapshots at distributor level</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          + Add Snapshot
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Total Snapshots", value: snapshots.length },
          { label: "Total Stock (units)", value: totalStock.toLocaleString() },
          { label: "Overstock Risk (>60 days)", value: atRisk, color: "text-red-600" },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-lg border p-4">
            <p className="text-xs text-gray-500">{k.label}</p>
            <p className={`text-2xl font-bold mt-1 ${k.color || "text-gray-800"}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Filter */}
      <select
        value={filterDist}
        onChange={(e) => setFilterDist(e.target.value)}
        className="border rounded-lg px-3 py-2 text-sm"
      >
        <option value="">All Distributors</option>
        {distributors.map((d) => (
          <option key={d.id} value={d.id}>{d.name}</option>
        ))}
      </select>

      {/* Table */}
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
            <tr>
              <th className="px-4 py-3 text-left">Distributor</th>
              <th className="px-4 py-3 text-left">Product</th>
              <th className="px-4 py-3 text-left">SKU</th>
              <th className="px-4 py-3 text-right">Stock Qty</th>
              <th className="px-4 py-3 text-right">Days of Stock</th>
              <th className="px-4 py-3 text-right">ST Rate</th>
              <th className="px-4 py-3 text-left">Snapshot Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : snapshots.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No inventory snapshots recorded</td></tr>
            ) : (
              snapshots.map((s) => {
                const daysRisk = s.days_of_stock != null && Number(s.days_of_stock) > 60;
                return (
                  <tr key={s.id} className={`hover:bg-gray-50 ${daysRisk ? "bg-red-50" : ""}`}>
                    <td className="px-4 py-2">{s.distributor_name || "—"}</td>
                    <td className="px-4 py-2">{s.product_name || "—"}</td>
                    <td className="px-4 py-2 font-mono text-xs">{s.product_sku || "—"}</td>
                    <td className="px-4 py-2 text-right font-semibold">{Number(s.stock_qty).toLocaleString()}</td>
                    <td className={`px-4 py-2 text-right ${daysRisk ? "text-red-600 font-bold" : ""}`}>
                      {s.days_of_stock != null ? `${Number(s.days_of_stock).toFixed(0)} days` : "—"}
                    </td>
                    <td className="px-4 py-2 text-right">
                      {s.sell_through_rate != null ? `${(Number(s.sell_through_rate) * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-500">{s.snapshot_date}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Add Snapshot Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold mb-4">Add Inventory Snapshot</h2>
            <form onSubmit={handleSave} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Distributor *</label>
                <select
                  required
                  value={form.distributor_id}
                  onChange={(e) => setForm({ ...form, distributor_id: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                >
                  <option value="">Select…</option>
                  {distributors.map((d) => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Product *</label>
                <select
                  required
                  value={form.product_id}
                  onChange={(e) => setForm({ ...form, product_id: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                >
                  <option value="">Select…</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>{p.sku} — {p.name}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Stock Qty *</label>
                  <input
                    required
                    type="number"
                    step="0.001"
                    value={form.stock_qty}
                    onChange={(e) => setForm({ ...form, stock_qty: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Snapshot Date *</label>
                  <input
                    required
                    type="date"
                    value={form.snapshot_date}
                    onChange={(e) => setForm({ ...form, snapshot_date: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                  />
                </div>
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
              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 py-2 border rounded-lg text-sm hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? "Saving…" : "Save"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
