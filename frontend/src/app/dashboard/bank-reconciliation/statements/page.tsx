"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { brApi, BRStatement, BRStatementStatus, STATUS_COLOR } from "@/lib/bank_reconciliation";

const STATUSES: { value: BRStatementStatus | ""; label: string }[] = [
  { value: "", label: "All" },
  { value: "DRAFT", label: "Draft" },
  { value: "IMPORTED", label: "Imported" },
  { value: "IN_RECONCILIATION", label: "In Recon" },
  { value: "RECONCILED", label: "Reconciled" },
  { value: "CLOSED", label: "Closed" },
  { value: "LOCKED", label: "Locked" },
];

export default function StatementsListPage() {
  const [statusFilter, setStatusFilter] = useState<BRStatementStatus | "">("");

  const { data: statements = [], isLoading } = useQuery<BRStatement[]>({
    queryKey: ["br-statements", statusFilter],
    queryFn: () => brApi.listStatements(statusFilter ? { status: statusFilter } : undefined),
  });

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Bank Statements</h1>
        <Link href="/dashboard/bank-reconciliation/import"
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
          Import Statement
        </Link>
      </div>

      <div className="flex gap-1 flex-wrap">
        {STATUSES.map((s) => (
          <button key={s.value} onClick={() => setStatusFilter(s.value)}
            className={`px-3 py-1.5 text-xs rounded-lg border ${
              statusFilter === s.value ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-600 hover:bg-gray-50"
            }`}>
            {s.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-gray-400">Loading…</p>
      ) : (
        <div className="bg-white border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {["Statement No", "Account", "Period", "Opening", "Closing", "Lines", "Source", "Status", ""].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {statements.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs font-medium">{s.statement_no}</td>
                  <td className="px-4 py-2 text-xs text-gray-600">{s.bank_account_id.slice(0, 8)}…</td>
                  <td className="px-4 py-2 text-xs">{s.period_start_date} → {s.period_end_date}</td>
                  <td className="px-4 py-2">{Number(s.opening_balance).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                  <td className="px-4 py-2 font-medium">{Number(s.closing_balance).toLocaleString(undefined, { minimumFractionDigits: 2 })} {s.statement_currency}</td>
                  <td className="px-4 py-2">{s.total_lines}</td>
                  <td className="px-4 py-2 text-xs text-gray-500">{s.import_source}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[s.status]}`}>
                      {s.status.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <Link href={`/dashboard/bank-reconciliation/statements/${s.id}`}
                      className="text-blue-600 hover:underline text-xs">
                      Open
                    </Link>
                  </td>
                </tr>
              ))}
              {statements.length === 0 && (
                <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400 text-sm">No statements found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
