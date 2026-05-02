"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { financeApi, COA, AccountType } from "@/lib/finance";

const TYPE_COLOR: Record<AccountType, string> = {
  ASSET: "bg-blue-100 text-blue-700",
  LIABILITY: "bg-red-100 text-red-700",
  EQUITY: "bg-purple-100 text-purple-700",
  REVENUE: "bg-green-100 text-green-700",
  EXPENSE: "bg-orange-100 text-orange-700",
};

const ACCOUNT_TYPES: AccountType[] = ["ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE"];

export default function ChartOfAccountsPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [filterType, setFilterType] = useState<AccountType | "">("");
  const [search, setSearch] = useState("");

  const [form, setForm] = useState({
    code: "", name: "", account_type: "ASSET" as AccountType,
    is_control: false, notes: "",
  });

  const { data: accounts, isLoading } = useQuery<COA[]>({
    queryKey: ["coa-all"],
    queryFn: () => financeApi.listCOA(false),
    staleTime: 30_000,
  });

  const createMut = useMutation({
    mutationFn: (data: object) => financeApi.createCOA(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["coa-all"] });
      qc.invalidateQueries({ queryKey: ["coa"] });
      setShowForm(false);
      setForm({ code: "", name: "", account_type: "ASSET", is_control: false, notes: "" });
    },
  });

  const filtered = (accounts ?? []).filter((a) => {
    if (filterType && a.account_type !== filterType) return false;
    if (search && !a.code.toLowerCase().includes(search.toLowerCase()) &&
        !a.name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="max-w-6xl mx-auto space-y-5 pb-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Chart of Accounts</h1>
          <p className="text-sm text-gray-400 mt-0.5">Manage accounts for double-entry bookkeeping</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700"
        >
          + Add Account
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-indigo-200 shadow-sm p-5 space-y-4">
          <h2 className="font-semibold text-gray-800">New Account</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Code *</label>
              <input value={form.code} onChange={(e) => setForm((f) => ({ ...f, code: e.target.value }))}
                placeholder="e.g. 1000"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-gray-500 mb-1">Name *</label>
              <input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Cash and Cash Equivalents"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Type *</label>
              <select value={form.account_type} onChange={(e) => setForm((f) => ({ ...f, account_type: e.target.value as AccountType }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300">
                {ACCOUNT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div className="flex items-center gap-2 mt-5">
              <input type="checkbox" id="is_control" checked={form.is_control}
                onChange={(e) => setForm((f) => ({ ...f, is_control: e.target.checked }))} />
              <label htmlFor="is_control" className="text-sm text-gray-600">Control/Summary Account</label>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Notes</label>
              <input value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
            </div>
          </div>
          {createMut.isError && (
            <p className="text-sm text-red-500">Failed to create account. Check code is unique.</p>
          )}
          <div className="flex gap-2">
            <button
              onClick={() => createMut.mutate(form)}
              disabled={!form.code || !form.name || createMut.isPending}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
            >
              {createMut.isPending ? "Saving…" : "Save"}
            </button>
            <button onClick={() => setShowForm(false)}
              className="px-4 py-2 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <input value={search} onChange={(e) => setSearch(e.target.value)}
          placeholder="Search code or name…"
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
        <select value={filterType} onChange={(e) => setFilterType(e.target.value as AccountType | "")}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300">
          <option value="">All Types</option>
          {ACCOUNT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <span className="text-xs text-gray-400">{filtered.length} accounts</span>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Code</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Name</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Type</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Control?</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Status</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Notes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {isLoading && (
              <tr><td colSpan={6} className="text-center py-8 text-gray-400">Loading…</td></tr>
            )}
            {!isLoading && filtered.length === 0 && (
              <tr><td colSpan={6} className="text-center py-8 text-gray-400">No accounts found.</td></tr>
            )}
            {filtered.map((a) => (
              <tr key={a.id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 font-mono text-xs font-semibold text-gray-700">{a.code}</td>
                <td className="px-4 py-2.5 font-medium text-gray-800">{a.name}</td>
                <td className="px-4 py-2.5">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${TYPE_COLOR[a.account_type]}`}>
                    {a.account_type}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-xs text-gray-500">
                  {a.is_control ? <span className="bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full">Control</span> : "—"}
                </td>
                <td className="px-4 py-2.5">
                  {a.is_active
                    ? <span className="bg-green-100 text-green-700 text-xs px-2 py-0.5 rounded-full">Active</span>
                    : <span className="bg-gray-100 text-gray-500 text-xs px-2 py-0.5 rounded-full">Inactive</span>}
                </td>
                <td className="px-4 py-2.5 text-xs text-gray-400 max-w-xs truncate">{a.notes ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
