"use client";
import { useState, useEffect } from "react";
import { plApi, PLHeader, PLStatus, PLType, PL_STATUS_COLORS, PL_TYPE_COLORS } from "@/lib/price_list";

export default function PriceListDashboard() {
  const [headers, setHeaders] = useState<PLHeader[]>([]);
  const [kpis, setKpis] = useState<any>(null);
  const [expiring, setExpiring] = useState<PLHeader[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<PLStatus | "">("");
  const [typeFilter, setTypeFilter] = useState<PLType | "">("");
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    price_list_code: "", price_list_name: "", currency: "KES",
    pl_type: "STANDARD" as PLType, valid_from: "", valid_to: "",
    priority_rank: 50, default_flag: false, created_by: "", notes: "",
  });

  const load = () => {
    setLoading(true);
    Promise.all([
      plApi.listHeaders({ status: statusFilter || undefined, pl_type: typeFilter || undefined }),
      plApi.getDashboard(),
      plApi.getExpiring(30),
    ]).then(([h, k, e]) => { setHeaders(h); setKpis(k); setExpiring(e); }).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [statusFilter, typeFilter]);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    await plApi.createHeader(form as any);
    setCreating(false);
    load();
  };

  const PL_TYPES: PLType[] = ["STANDARD", "WHOLESALE", "RETAIL", "EXPORT", "DISTRIBUTOR", "MODERN_TRADE", "CUSTOMER_SPECIFIC", "PROMO", "CUSTOM"];
  const PL_STATUSES: PLStatus[] = ["DRAFT", "UNDER_REVIEW", "APPROVED", "ACTIVE", "EXPIRED", "ARCHIVED"];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Price Lists</h1>
          <p className="text-sm text-gray-500 mt-1">Multi-tier pricing — customers, channels, regions, promos, quantity breaks</p>
        </div>
        <div className="flex gap-2">
          <a href="/dashboard/price-lists/approval-queue"
            className="px-3 py-2 bg-yellow-100 text-yellow-800 rounded-lg text-sm font-medium hover:bg-yellow-200">
            Approval Queue {kpis?.pending_approval > 0 ? `(${kpis.pending_approval})` : ""}
          </a>
          <button onClick={() => setCreating(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            + New Price List
          </button>
        </div>
      </div>

      {/* KPIs */}
      {kpis && (
        <div className="grid grid-cols-5 gap-4">
          {[
            { label: "Active Lists", v: kpis.active_price_lists, c: "text-green-700" },
            { label: "Draft", v: kpis.draft_price_lists, c: "text-gray-700" },
            { label: "Pending Approval", v: kpis.pending_approval, c: "text-yellow-700" },
            { label: "Expired (Still Active)", v: kpis.expired_active_lists, c: "text-red-700" },
            { label: "Active Lines", v: kpis.total_active_lines, c: "text-blue-700" },
          ].map((k) => (
            <div key={k.label} className="bg-white rounded-xl border border-gray-200 p-4">
              <div className={`text-2xl font-bold ${k.c}`}>{k.v}</div>
              <div className="text-xs text-gray-500 mt-1">{k.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Expiring Alert */}
      {expiring.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-red-800 mb-2">Price Lists Expiring in 30 Days</h3>
          <div className="flex flex-wrap gap-2">
            {expiring.map((h) => (
              <a key={h.id} href={`/dashboard/price-lists/${h.id}`}
                className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded-lg hover:bg-red-200">
                {h.price_list_code} — expires {h.valid_to}
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as any)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
          <option value="">All Statuses</option>
          {PL_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value as any)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
          <option value="">All Types</option>
          {PL_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
        </select>
        <span className="px-3 py-2 text-sm text-gray-500">{headers.length} price lists</span>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {["Code", "Name", "Type", "Currency", "Valid From", "Valid To", "Status", "Priority", "Default", "Actions"].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={10} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : headers.length === 0 ? (
              <tr><td colSpan={10} className="px-4 py-8 text-center text-gray-400">No price lists found.</td></tr>
            ) : headers.map((h) => (
              <tr key={h.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs text-gray-700">{h.price_list_code}</td>
                <td className="px-4 py-3 font-medium text-blue-700">
                  <a href={`/dashboard/price-lists/${h.id}`} className="hover:underline">{h.price_list_name}</a>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${PL_TYPE_COLORS[h.pl_type]}`}>
                    {h.pl_type.replace(/_/g, " ")}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono text-xs">{h.currency}</td>
                <td className="px-4 py-3 text-gray-500 text-xs">{h.valid_from}</td>
                <td className="px-4 py-3 text-gray-500 text-xs">{h.valid_to || "Open"}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${PL_STATUS_COLORS[h.status]}`}>{h.status}</span>
                </td>
                <td className="px-4 py-3 text-center text-xs font-bold text-gray-600">{h.priority_rank}</td>
                <td className="px-4 py-3 text-center">
                  {h.default_flag && <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">DEFAULT</span>}
                </td>
                <td className="px-4 py-3">
                  <a href={`/dashboard/price-lists/${h.id}`} className="text-blue-600 hover:underline text-xs">Edit</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {creating && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-lg">
            <h2 className="text-lg font-bold text-gray-900 mb-4">New Price List</h2>
            <form onSubmit={create} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-700">Code</label>
                  <input required value={form.price_list_code} onChange={(e) => setForm({ ...form, price_list_code: e.target.value })}
                    className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="WHL-2026-KES" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-700">Type</label>
                  <select value={form.pl_type} onChange={(e) => setForm({ ...form, pl_type: e.target.value as PLType })}
                    className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {PL_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Name</label>
                <input required value={form.price_list_name} onChange={(e) => setForm({ ...form, price_list_name: e.target.value })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-700">Currency</label>
                  <input value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}
                    className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-700">Valid From</label>
                  <input required type="date" value={form.valid_from} onChange={(e) => setForm({ ...form, valid_from: e.target.value })}
                    className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-700">Valid To</label>
                  <input type="date" value={form.valid_to} onChange={(e) => setForm({ ...form, valid_to: e.target.value })}
                    className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-700">Priority Rank</label>
                  <input type="number" value={form.priority_rank} onChange={(e) => setForm({ ...form, priority_rank: Number(e.target.value) })}
                    className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-700">Created By</label>
                  <input value={form.created_by} onChange={(e) => setForm({ ...form, created_by: e.target.value })}
                    className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" checked={form.default_flag} onChange={(e) => setForm({ ...form, default_flag: e.target.checked })} />
                <label className="text-sm text-gray-700">Set as default price list</label>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setCreating(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
                <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
