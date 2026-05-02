"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { financeApi, JournalEntry, COA } from "@/lib/finance";

function fmt(n: number) {
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

interface LineInput {
  account_id: string;
  description: string;
  debit: string;
  credit: string;
}

const emptyLine = (): LineInput => ({ account_id: "", description: "", debit: "", credit: "" });

export default function JournalEntriesPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);

  const [entry, setEntry] = useState({
    entry_no: "",
    entry_date: new Date().toISOString().slice(0, 10),
    description: "",
    notes: "",
  });
  const [lines, setLines] = useState<LineInput[]>([emptyLine(), emptyLine()]);

  const { data: accounts } = useQuery<COA[]>({
    queryKey: ["coa"],
    queryFn: () => financeApi.listCOA(false),
    staleTime: 60_000,
  });

  const { data: entries, isLoading } = useQuery<JournalEntry[]>({
    queryKey: ["journal-entries"],
    queryFn: () => financeApi.listJournal({ limit: 200 }),
    staleTime: 30_000,
  });

  const totalDebit = lines.reduce((s, l) => s + (parseFloat(l.debit) || 0), 0);
  const totalCredit = lines.reduce((s, l) => s + (parseFloat(l.credit) || 0), 0);
  const isBalanced = Math.abs(totalDebit - totalCredit) < 0.005 && totalDebit > 0;

  const createMut = useMutation({
    mutationFn: (data: object) => financeApi.createJournalEntry(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["journal-entries"] });
      setShowForm(false);
      setEntry({ entry_no: "", entry_date: new Date().toISOString().slice(0, 10), description: "", notes: "" });
      setLines([emptyLine(), emptyLine()]);
    },
  });

  const postMut = useMutation({
    mutationFn: (id: string) => financeApi.postJournalEntry(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["journal-entries"] }),
  });

  function updateLine(i: number, field: keyof LineInput, value: string) {
    setLines((prev) => prev.map((l, idx) => idx === i ? { ...l, [field]: value } : l));
  }

  function handleSubmit() {
    const payload = {
      ...entry,
      lines: lines
        .filter((l) => l.account_id)
        .map((l) => ({
          account_id: l.account_id,
          description: l.description || undefined,
          debit: parseFloat(l.debit) || 0,
          credit: parseFloat(l.credit) || 0,
        })),
    };
    createMut.mutate(payload);
  }

  return (
    <div className="max-w-6xl mx-auto space-y-5 pb-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Journal Entries</h1>
          <p className="text-sm text-gray-400 mt-0.5">Manual double-entry bookkeeping records</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700"
        >
          + New Entry
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-indigo-200 shadow-sm p-5 space-y-4">
          <h2 className="font-semibold text-gray-800">New Journal Entry</h2>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Entry No *</label>
              <input value={entry.entry_no} onChange={(e) => setEntry((f) => ({ ...f, entry_no: e.target.value }))}
                placeholder="JE-2026-001"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Date *</label>
              <input type="date" value={entry.entry_date} onChange={(e) => setEntry((f) => ({ ...f, entry_date: e.target.value }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-gray-500 mb-1">Description *</label>
              <input value={entry.description} onChange={(e) => setEntry((f) => ({ ...f, description: e.target.value }))}
                placeholder="e.g. Monthly accrual — rent expense"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
            </div>
          </div>

          {/* Lines */}
          <div>
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 rounded">
                  <th className="text-left px-2 py-2 text-xs font-semibold text-gray-500">Account</th>
                  <th className="text-left px-2 py-2 text-xs font-semibold text-gray-500">Description</th>
                  <th className="text-right px-2 py-2 text-xs font-semibold text-gray-500">Debit</th>
                  <th className="text-right px-2 py-2 text-xs font-semibold text-gray-500">Credit</th>
                  <th className="px-2 py-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {lines.map((line, i) => (
                  <tr key={i}>
                    <td className="px-2 py-1">
                      <select value={line.account_id} onChange={(e) => updateLine(i, "account_id", e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-300">
                        <option value="">Select…</option>
                        {(accounts ?? []).filter((a) => !a.is_control).map((a) => (
                          <option key={a.id} value={a.id}>{a.code} — {a.name}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-2 py-1">
                      <input value={line.description} onChange={(e) => updateLine(i, "description", e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-300" />
                    </td>
                    <td className="px-2 py-1">
                      <input type="number" value={line.debit} onChange={(e) => updateLine(i, "debit", e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-sm text-right focus:outline-none focus:ring-1 focus:ring-indigo-300" />
                    </td>
                    <td className="px-2 py-1">
                      <input type="number" value={line.credit} onChange={(e) => updateLine(i, "credit", e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-sm text-right focus:outline-none focus:ring-1 focus:ring-indigo-300" />
                    </td>
                    <td className="px-2 py-1">
                      <button onClick={() => setLines((prev) => prev.filter((_, idx) => idx !== i))}
                        className="text-gray-400 hover:text-red-500 text-xs">✕</button>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-gray-50 font-semibold text-sm">
                  <td colSpan={2} className="px-2 py-2 text-gray-600">TOTAL</td>
                  <td className="px-2 py-2 text-right text-gray-800">{fmt(totalDebit)}</td>
                  <td className="px-2 py-2 text-right text-gray-800">{fmt(totalCredit)}</td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
            <button onClick={() => setLines((prev) => [...prev, emptyLine()])}
              className="mt-2 text-xs text-indigo-600 hover:underline">+ Add Line</button>
          </div>

          {!isBalanced && totalDebit > 0 && (
            <p className="text-sm text-red-500 font-medium">
              Entry is unbalanced — difference: {fmt(Math.abs(totalDebit - totalCredit))}
            </p>
          )}
          {createMut.isError && (
            <p className="text-sm text-red-500">Failed to save. Check entry number is unique and entry is balanced.</p>
          )}

          <div className="flex gap-2">
            <button
              onClick={handleSubmit}
              disabled={!isBalanced || !entry.entry_no || !entry.description || createMut.isPending}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
            >
              {createMut.isPending ? "Saving…" : "Save as Draft"}
            </button>
            <button onClick={() => setShowForm(false)}
              className="px-4 py-2 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100">Cancel</button>
          </div>
        </div>
      )}

      {/* Entries list */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Entry No</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Date</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Description</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Source</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Debit</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Status</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {isLoading && (
              <tr><td colSpan={7} className="text-center py-8 text-gray-400">Loading…</td></tr>
            )}
            {!isLoading && (entries ?? []).length === 0 && (
              <tr><td colSpan={7} className="text-center py-8 text-gray-400">No journal entries yet.</td></tr>
            )}
            {(entries ?? []).map((e) => (
              <tr key={e.id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 font-mono text-xs font-semibold text-gray-700">{e.entry_no}</td>
                <td className="px-4 py-2.5 text-gray-600">{e.entry_date}</td>
                <td className="px-4 py-2.5 text-gray-800">{e.description}</td>
                <td className="px-4 py-2.5 text-xs text-gray-400">{e.source_module ?? "Manual"}</td>
                <td className="px-4 py-2.5 text-right text-gray-700">
                  {e.total_debit ? fmt(e.total_debit) : "—"}
                </td>
                <td className="px-4 py-2.5">
                  {e.is_posted
                    ? <span className="bg-green-100 text-green-700 text-xs px-2 py-0.5 rounded-full">Posted</span>
                    : <span className="bg-yellow-100 text-yellow-700 text-xs px-2 py-0.5 rounded-full">Draft</span>}
                </td>
                <td className="px-4 py-2.5 text-right">
                  {!e.is_posted && (
                    <button
                      onClick={() => postMut.mutate(e.id)}
                      disabled={postMut.isPending}
                      className="text-xs bg-indigo-100 text-indigo-700 px-3 py-1 rounded-full hover:bg-indigo-200 disabled:opacity-50"
                    >
                      Post
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
