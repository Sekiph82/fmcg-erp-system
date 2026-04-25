"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  brApi, BRStatementLine, BRStatement,
  LINE_STATUS_COLOR, STATUS_COLOR,
} from "@/lib/bank_reconciliation";

export default function MpesaReconPage() {
  const qc = useQueryClient();
  const [selectedStmt, setSelectedStmt] = useState<string | null>(null);

  const { data: statements = [], isLoading: lStmts } = useQuery<BRStatement[]>({
    queryKey: ["br-mpesa-stmts"],
    queryFn: () => brApi.listStatements({ limit: 100 }),
  });

  const mpesaStmts = statements.filter(
    (s) => s.import_source === "MPESA"
  );

  const { data: lines = [], isLoading: lLines } = useQuery<BRStatementLine[]>({
    queryKey: ["br-lines-mpesa", selectedStmt],
    queryFn: () => brApi.getLines(selectedStmt!),
    enabled: !!selectedStmt,
  });

  const autoMatch = useMutation({
    mutationFn: () => brApi.autoMatch(selectedStmt!, { confidence_threshold: 0.65 }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["br-lines-mpesa", selectedStmt] }),
  });

  const unmatchedCount  = lines.filter((l) => l.match_status === "UNMATCHED").length;
  const matchedCount    = lines.filter((l) => l.match_status === "MATCHED").length;
  const totalAmount     = lines.reduce((s, l) => s + Number(l.amount), 0);
  const unmatchedAmount = lines.filter((l) => l.match_status === "UNMATCHED").reduce((s, l) => s + Number(l.unmatched_amount), 0);

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">M-Pesa Reconciliation</h1>
        <p className="text-sm text-gray-500 mt-1">Match M-Pesa statement lines against ERP M-Pesa collections & payouts</p>
      </div>

      {/* M-Pesa statement selector */}
      <div className="bg-white border rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Select M-Pesa Statement</h2>
        {lStmts ? (
          <p className="text-sm text-gray-400">Loading…</p>
        ) : mpesaStmts.length === 0 ? (
          <div className="space-y-2">
            <p className="text-sm text-gray-500">No M-Pesa statements imported yet.</p>
            <Link href="/dashboard/bank-reconciliation/import"
              className="inline-block px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700">
              Import M-Pesa Statement
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {mpesaStmts.map((s) => (
              <button key={s.id} onClick={() => setSelectedStmt(s.id)}
                className={`p-3 rounded-xl border text-left text-sm transition ${
                  selectedStmt === s.id ? "border-green-500 bg-green-50" : "border-gray-200 hover:border-gray-300"
                }`}>
                <p className="font-medium text-gray-800">{s.statement_no}</p>
                <p className="text-xs text-gray-500">{s.period_start_date} → {s.period_end_date}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[s.status]}`}>
                    {s.status.replace(/_/g, " ")}
                  </span>
                  <span className="text-xs text-gray-400">{s.total_lines} lines</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Statement lines */}
      {selectedStmt && (
        <div className="space-y-4">
          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "Total Lines", value: lines.length },
              { label: "Total Amount", value: totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2 }) },
              { label: "Matched", value: matchedCount, cls: "text-green-700" },
              { label: "Unmatched Amt", value: unmatchedAmount.toLocaleString(undefined, { minimumFractionDigits: 2 }), cls: unmatchedCount > 0 ? "text-red-700" : "text-green-700" },
            ].map((s) => (
              <div key={s.label} className="bg-white border rounded-xl p-3">
                <p className="text-xs text-gray-500">{s.label}</p>
                <p className={`text-xl font-bold mt-0.5 ${s.cls ?? "text-gray-900"}`}>{s.value}</p>
              </div>
            ))}
          </div>

          <div className="flex gap-2">
            <button onClick={() => autoMatch.mutate()} disabled={autoMatch.isPending}
              className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50">
              {autoMatch.isPending ? "Matching…" : "Auto-Match M-Pesa"}
            </button>
            {autoMatch.data && (
              <span className="text-xs text-green-700 bg-green-50 px-3 py-2 rounded self-center">
                {(autoMatch.data as { auto_applied: number; suggestions_created: number }).auto_applied} applied,{" "}
                {(autoMatch.data as { auto_applied: number; suggestions_created: number }).suggestions_created} suggested
              </span>
            )}
            <Link href={`/dashboard/bank-reconciliation/statements/${selectedStmt}`}
              className="px-4 py-2 bg-white border text-sm rounded-lg text-gray-600 hover:bg-gray-50">
              Full Workspace
            </Link>
          </div>

          {/* Lines table */}
          <div className="bg-white border rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b bg-gray-50">
              <h2 className="text-sm font-semibold text-gray-700">M-Pesa Statement Lines</h2>
            </div>
            {lLines ? (
              <p className="p-4 text-gray-400 text-sm">Loading…</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                  <tr>
                    {["#", "Date", "D/C", "Amount", "Unmatched", "Reference", "Narration", "Status"].map((h) => (
                      <th key={h} className="px-3 py-2 text-left font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {lines.map((l: BRStatementLine) => (
                    <tr key={l.id} className="hover:bg-gray-50">
                      <td className="px-3 py-2 text-gray-400 text-xs">{l.line_no}</td>
                      <td className="px-3 py-2 text-xs">{l.transaction_date}</td>
                      <td className="px-3 py-2">
                        <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${l.debit_credit_indicator === "C" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                          {l.debit_credit_indicator === "C" ? "CR" : "DR"}
                        </span>
                      </td>
                      <td className="px-3 py-2 font-medium">{Number(l.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                      <td className="px-3 py-2 font-medium text-red-600">
                        {Number(l.unmatched_amount) > 0 ? Number(l.unmatched_amount).toLocaleString(undefined, { minimumFractionDigits: 2 }) : "—"}
                      </td>
                      <td className="px-3 py-2 font-mono text-xs text-gray-600">{l.external_reference || "—"}</td>
                      <td className="px-3 py-2 text-xs text-gray-600 max-w-xs truncate">{l.narration || "—"}</td>
                      <td className="px-3 py-2">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${LINE_STATUS_COLOR[l.match_status]}`}>
                          {l.match_status.replace(/_/g, " ")}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {lines.length === 0 && (
                    <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400 text-sm">No lines in this statement.</td></tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-sm text-green-800">
        <p className="font-semibold mb-1">M-Pesa Reconciliation Tips</p>
        <ul className="space-y-1 text-xs list-disc list-inside text-green-700">
          <li>Import M-Pesa statements selecting &quot;MPESA&quot; as import source</li>
          <li>M-Pesa codes (e.g. QF12345ABC) are matched against ERP mpesa_receipt field</li>
          <li>Use Auto-Match with lower confidence threshold (0.65) for phone-based matching</li>
          <li>STK push collections appear as CR lines — AR payments as DR in books</li>
        </ul>
      </div>
    </div>
  );
}
