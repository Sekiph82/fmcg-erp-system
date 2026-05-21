"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { brApi } from "@/lib/bank_reconciliation";

interface LineRow {
  transaction_date: string;
  narration: string;
  amount: string;
  debit_credit_indicator: string;
  external_reference: string;
  bank_reference: string;
  counterparty_name: string;
}

const emptyLine = (): LineRow => ({
  transaction_date: "",
  narration: "",
  amount: "",
  debit_credit_indicator: "C",
  external_reference: "",
  bank_reference: "",
  counterparty_name: "",
});

export default function BRImportPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [form, setForm] = useState({
    bank_account_id: "",
    statement_date: "",
    period_start_date: "",
    period_end_date: "",
    opening_balance: "",
    closing_balance: "",
    statement_currency: "KES",
    import_source: "MANUAL" as const,
    imported_by: "",
  });
  const [lines, setLines] = useState<LineRow[]>([emptyLine()]);
  const [error, setError] = useState<string | null>(null);

  const { data: accounts = [] } = useQuery({
    queryKey: ["br-accounts"],
    queryFn: () => brApi.listAccounts(true),
  });

  const submit = useMutation({
    mutationFn: () => brApi.importStatement({
      ...form,
      opening_balance: parseFloat(form.opening_balance) || 0,
      closing_balance: parseFloat(form.closing_balance) || 0,
      lines: lines.filter((l) => l.transaction_date && l.amount).map((l) => ({
        ...l,
        amount: parseFloat(l.amount) || 0,
      })),
    }),
    onSuccess: (stmt) => {
      qc.invalidateQueries({ queryKey: ["br-dashboard"] });
      router.push(`/dashboard/bank-reconciliation/statements/${stmt.id}`);
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Import failed"),
  });

  const updateLine = (i: number, field: keyof LineRow, val: string) => {
    setLines((prev) => prev.map((l, idx) => idx === i ? { ...l, [field]: val } : l));
  };

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <h1 className="text-2xl font-bold text-gray-900">Import Bank Statement</h1>

      {error && <p className="text-red-600 text-sm bg-red-50 px-3 py-2 rounded">{error}</p>}

      {/* Header */}
      <div className="bg-white border rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">Statement Header</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-gray-500 font-medium">Bank Account *</label>
            <select value={form.bank_account_id} onChange={(e) => setForm({ ...form, bank_account_id: e.target.value })}
              className="mt-1 w-full border rounded-lg px-3 py-2 text-sm">
              <option value="">Select account…</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>{a.account_name} — {a.bank_name} ({a.currency})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 font-medium">Import Source</label>
            <select value={form.import_source} onChange={(e) => setForm({ ...form, import_source: e.target.value as "MANUAL" })}
              className="mt-1 w-full border rounded-lg px-3 py-2 text-sm">
              {["MANUAL", "CSV", "OFX", "MPESA", "API"].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          {[
            { key: "statement_date", label: "Statement Date", type: "date" },
            { key: "period_start_date", label: "Period Start", type: "date" },
            { key: "period_end_date", label: "Period End", type: "date" },
            { key: "statement_currency", label: "Currency", type: "text" },
            { key: "opening_balance", label: "Opening Balance", type: "number" },
            { key: "closing_balance", label: "Closing Balance", type: "number" },
            { key: "imported_by", label: "Imported By", type: "text" },
          ].map(({ key, label, type }) => (
            <div key={key}>
              <label className="text-xs text-gray-500 font-medium">{label}</label>
              <input type={type} value={(form as Record<string, string>)[key]}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
          ))}
        </div>
      </div>

      {/* Lines */}
      <div className="bg-white border rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b bg-gray-50 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">Statement Lines ({lines.length})</h2>
          <button onClick={() => setLines((p) => [...p, emptyLine()])}
            className="text-xs px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700">
            + Add Line
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-50 text-gray-500 uppercase">
              <tr>
                {["Date *", "D/C", "Amount *", "Narration", "Ext. Ref", "Bank Ref", "Counterparty", ""].map((h) => (
                  <th key={h} className="px-3 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {lines.map((l, i) => (
                <tr key={i}>
                  <td className="px-2 py-1">
                    <input type="date" value={l.transaction_date}
                      onChange={(e) => updateLine(i, "transaction_date", e.target.value)}
                      className="border rounded px-2 py-1 w-32" />
                  </td>
                  <td className="px-2 py-1">
                    <select value={l.debit_credit_indicator}
                      onChange={(e) => updateLine(i, "debit_credit_indicator", e.target.value)}
                      className="border rounded px-2 py-1 w-16">
                      <option value="C">CR</option>
                      <option value="D">DR</option>
                    </select>
                  </td>
                  <td className="px-2 py-1">
                    <input type="number" step="0.01" value={l.amount}
                      onChange={(e) => updateLine(i, "amount", e.target.value)}
                      className="border rounded px-2 py-1 w-28" />
                  </td>
                  <td className="px-2 py-1">
                    <input type="text" value={l.narration}
                      onChange={(e) => updateLine(i, "narration", e.target.value)}
                      className="border rounded px-2 py-1 w-40" />
                  </td>
                  <td className="px-2 py-1">
                    <input type="text" value={l.external_reference}
                      onChange={(e) => updateLine(i, "external_reference", e.target.value)}
                      className="border rounded px-2 py-1 w-28" />
                  </td>
                  <td className="px-2 py-1">
                    <input type="text" value={l.bank_reference}
                      onChange={(e) => updateLine(i, "bank_reference", e.target.value)}
                      className="border rounded px-2 py-1 w-28" />
                  </td>
                  <td className="px-2 py-1">
                    <input type="text" value={l.counterparty_name}
                      onChange={(e) => updateLine(i, "counterparty_name", e.target.value)}
                      className="border rounded px-2 py-1 w-32" />
                  </td>
                  <td className="px-2 py-1">
                    <button onClick={() => setLines((p) => p.filter((_, idx) => idx !== i))}
                      className="text-red-500 hover:text-red-700 text-xs">✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex gap-3">
        <button
          onClick={() => submit.mutate()}
          disabled={submit.isPending || !form.bank_account_id}
          className="px-6 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50">
          {submit.isPending ? "Importing…" : "Import Statement"}
        </button>
        <button onClick={() => window.history.back()}
          className="px-4 py-2 border text-sm rounded-lg text-gray-600 hover:bg-gray-50">
          Cancel
        </button>
      </div>
    </div>
  );
}
