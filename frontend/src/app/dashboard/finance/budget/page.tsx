"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { financeApi, Budget, BudgetStatus } from "@/lib/finance";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

const statusBadge = (s: BudgetStatus) =>
  s === "APPROVED" ? "green" : s === "LOCKED" ? "blue" : "yellow";

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

export default function BudgetPage() {
  const qc = useQueryClient();
  const [selectedBudget, setSelectedBudget] = useState<Budget | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [bvaYear, setBvaYear] = useState(new Date().getFullYear());
  const [bvaDept, setBvaDept] = useState("");

  const { data: budgets = [] } = useQuery({
    queryKey: ["finance-budgets"],
    queryFn: () => financeApi.listBudgets(),
  });

  const { data: budgetDetail } = useQuery({
    queryKey: ["finance-budget-detail", selectedBudget?.id],
    queryFn: () => (selectedBudget ? financeApi.getBudget(selectedBudget.id) : null),
    enabled: !!selectedBudget,
  });

  const { data: bvaData = [], isLoading: bvaLoading } = useQuery({
    queryKey: ["finance-bva", bvaYear, bvaDept],
    queryFn: () => financeApi.budgetVsActual(bvaYear, bvaDept || undefined),
  });

  const createBudget = useMutation({
    mutationFn: (data: object) => financeApi.createBudget(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["finance-budgets"] }); setShowNew(false); },
  });

  const approveBudget = useMutation({
    mutationFn: (id: string) => financeApi.approveBudget(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["finance-budgets"] }),
  });

  const departments = Array.from(new Set(budgets.map((b) => b.department)));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Budget Management</h1>
          <p className="text-sm text-gray-500 mt-1">Department budgets, approval and variance tracking</p>
        </div>
        <Button onClick={() => setShowNew(true)}>New Budget</Button>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Budget list */}
        <div className="bg-white rounded-lg border">
          <div className="px-5 py-3 border-b font-semibold text-gray-800">Budgets</div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Year</th>
                <th className="px-5 py-2 text-left">Department</th>
                <th className="px-5 py-2 text-right">Total</th>
                <th className="px-5 py-2 text-left">Status</th>
                <th className="px-5 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {budgets.map((b) => (
                <tr
                  key={b.id}
                  className={`hover:bg-gray-50 cursor-pointer ${selectedBudget?.id === b.id ? "bg-indigo-50" : ""}`}
                  onClick={() => setSelectedBudget(b)}
                >
                  <td className="px-5 py-3 font-semibold">{b.year}</td>
                  <td className="px-5 py-3 text-gray-700">{b.department}</td>
                  <td className="px-5 py-3 text-right">
                    {b.total_budgeted != null ? Number(b.total_budgeted).toLocaleString(undefined, { minimumFractionDigits: 0 }) : "—"}
                  </td>
                  <td className="px-5 py-3"><Badge label={b.status} variant={statusBadge(b.status)} /></td>
                  <td className="px-5 py-3">
                    {b.status === "DRAFT" && (
                      <button
                        className="text-xs text-indigo-600 hover:underline"
                        onClick={(e) => { e.stopPropagation(); approveBudget.mutate(b.id); }}
                      >
                        Approve
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {budgets.length === 0 && (
                <tr><td colSpan={5} className="px-5 py-8 text-center text-gray-400">No budgets</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Budget detail */}
        <div className="bg-white rounded-lg border">
          <div className="px-5 py-3 border-b font-semibold text-gray-800">
            {budgetDetail ? `${budgetDetail.department} ${budgetDetail.year} — Lines` : "Select a budget to view lines"}
          </div>
          {budgetDetail ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                  <th className="px-5 py-2 text-left">Category</th>
                  <th className="px-5 py-2 text-left">Month</th>
                  <th className="px-5 py-2 text-right">Budgeted</th>
                </tr>
              </thead>
              <tbody className="divide-y max-h-64 overflow-y-auto">
                {(budgetDetail.lines ?? []).map((l) => (
                  <tr key={l.id} className="hover:bg-gray-50">
                    <td className="px-5 py-2 text-gray-700">{l.category}</td>
                    <td className="px-5 py-2 text-gray-500">{MONTHS[l.month - 1]}</td>
                    <td className="px-5 py-2 text-right">{Number(l.budgeted_amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                  </tr>
                ))}
                {(budgetDetail.lines ?? []).length === 0 && (
                  <tr><td colSpan={3} className="px-5 py-6 text-center text-gray-400">No lines</td></tr>
                )}
              </tbody>
            </table>
          ) : (
            <p className="px-5 py-12 text-center text-gray-400 text-sm">Click a budget row on the left</p>
          )}
        </div>
      </div>

      {/* Budget vs Actual */}
      <div className="bg-white rounded-lg border">
        <div className="px-5 py-3 border-b flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">Budget vs Actual</h2>
          <div className="flex items-center gap-3">
            <select
              className="border rounded px-3 py-1.5 text-sm"
              value={bvaYear}
              onChange={(e) => setBvaYear(parseInt(e.target.value))}
            >
              {[new Date().getFullYear() - 1, new Date().getFullYear(), new Date().getFullYear() + 1].map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <select
              className="border rounded px-3 py-1.5 text-sm"
              value={bvaDept}
              onChange={(e) => setBvaDept(e.target.value)}
            >
              <option value="">All Departments</option>
              {departments.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
        </div>
        {bvaLoading ? (
          <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Department</th>
                <th className="px-5 py-2 text-left">Category</th>
                <th className="px-5 py-2 text-left">Month</th>
                <th className="px-5 py-2 text-right">Budgeted</th>
                <th className="px-5 py-2 text-right">Actual</th>
                <th className="px-5 py-2 text-right">Variance</th>
                <th className="px-5 py-2 text-right">Var %</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {bvaData.map((row, i) => {
                const over = row.variance > 0;
                return (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-5 py-2 text-gray-700">{row.department}</td>
                    <td className="px-5 py-2 text-gray-600">{row.category}</td>
                    <td className="px-5 py-2 text-gray-500">{MONTHS[row.month - 1]}</td>
                    <td className="px-5 py-2 text-right">{Number(row.budgeted).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    <td className="px-5 py-2 text-right">{Number(row.actual).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    <td className={`px-5 py-2 text-right font-semibold ${over ? "text-red-600" : row.variance < 0 ? "text-green-600" : "text-gray-500"}`}>
                      {over ? "+" : ""}{Number(row.variance).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className={`px-5 py-2 text-right text-xs ${over ? "text-red-500" : "text-green-500"}`}>
                      {row.variance_pct != null ? `${over ? "+" : ""}${Number(row.variance_pct).toFixed(1)}%` : "—"}
                    </td>
                  </tr>
                );
              })}
              {bvaData.length === 0 && (
                <tr><td colSpan={7} className="px-5 py-8 text-center text-gray-400">No budget vs actual data for {bvaYear}</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* New Budget modal */}
      {showNew && (
        <NewBudgetModal
          onClose={() => setShowNew(false)}
          onSubmit={(data) => createBudget.mutate(data)}
          loading={createBudget.isPending}
        />
      )}
    </div>
  );
}

function NewBudgetModal({ onClose, onSubmit, loading }: { onClose: () => void; onSubmit: (d: object) => void; loading: boolean }) {
  const [form, setForm] = useState({
    year: new Date().getFullYear().toString(),
    department: "",
    currency: "KES",
    notes: "",
  });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 space-y-4">
        <h2 className="font-semibold text-lg">New Budget</h2>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Year</label>
              <input className="w-full border rounded px-3 py-2 text-sm" type="number" value={form.year} onChange={(e) => set("year", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Currency</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.currency} onChange={(e) => set("currency", e.target.value)} />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Department</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.department} onChange={(e) => set("department", e.target.value)} placeholder="e.g. Operations, Sales…" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
            <textarea className="w-full border rounded px-3 py-2 text-sm" rows={2} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit({ ...form, year: parseInt(form.year), lines: [] })}>Create</Button>
        </div>
      </div>
    </div>
  );
}
