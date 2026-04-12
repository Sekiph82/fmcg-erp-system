"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { financeApi } from "@/lib/finance";
import { Badge } from "@/components/ui/Badge";
import { RequirePermission } from "@/components/PermissionGuard";

function FinanceDashboardContent() {
  const router = useRouter();

  const { data: cashPosition = [] } = useQuery({
    queryKey: ["finance-cash-position"],
    queryFn: () => financeApi.cashPosition(),
  });

  const { data: receivables = [] } = useQuery({
    queryKey: ["finance-receivables"],
    queryFn: () => financeApi.receivables(),
  });

  const { data: recons = [] } = useQuery({
    queryKey: ["finance-recon-exceptions"],
    queryFn: () => financeApi.reconciliationExceptions(),
  });

  const today = new Date().toISOString().slice(0, 10);
  const monthStart = today.slice(0, 7) + "-01";

  const { data: mpesaSummary = [] } = useQuery({
    queryKey: ["finance-mpesa-summary", monthStart, today],
    queryFn: () => financeApi.mpesaSummary(monthStart, today),
  });

  const totalCash = cashPosition.reduce((s, r) => s + r.balance, 0);
  const totalReceivables = receivables.reduce((s, r) => s + r.outstanding, 0);
  const overdueCount = receivables.filter((r) => r.days_overdue && r.days_overdue > 0).length;
  const exceptionCount = recons.filter((r) => r.status === "EXCEPTION").length;
  const unmatchedCount = recons.filter((r) => r.status === "UNMATCHED").length;
  const monthMpesaTotal = mpesaSummary.reduce((s, r) => s + r.total_received, 0);
  const monthMpesaMatched = mpesaSummary.reduce((s, r) => s + r.matched_count, 0);
  const monthMpesaUnmatched = mpesaSummary.reduce((s, r) => s + r.unmatched_count, 0);

  const tiles = [
    {
      label: "Total Cash & Bank",
      value: `KES ${totalCash.toLocaleString(undefined, { minimumFractionDigits: 0 })}`,
      sub: `${cashPosition.length} accounts`,
      color: "text-green-700",
      href: "/dashboard/finance/cashbook",
    },
    {
      label: "Outstanding Receivables",
      value: `KES ${totalReceivables.toLocaleString(undefined, { minimumFractionDigits: 0 })}`,
      sub: `${overdueCount > 0 ? `${overdueCount} overdue` : "no overdue"}`,
      color: overdueCount > 0 ? "text-red-600" : "text-orange-600",
      href: "/dashboard/finance/receivables",
    },
    {
      label: "M-Pesa This Month",
      value: `KES ${monthMpesaTotal.toLocaleString(undefined, { minimumFractionDigits: 0 })}`,
      sub: `${monthMpesaMatched} matched / ${monthMpesaUnmatched} pending`,
      color: "text-indigo-700",
      href: "/dashboard/finance/mpesa",
    },
    {
      label: "Recon Exceptions",
      value: exceptionCount.toString(),
      sub: `${unmatchedCount} unmatched`,
      color: exceptionCount > 0 ? "text-red-600" : "text-gray-700",
      href: "/dashboard/finance/mpesa",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Finance & Accounting</h1>
          <p className="text-sm text-gray-500 mt-1">Cash, M-Pesa, receivables, costing & budgets</p>
        </div>
      </div>

      {/* Summary tiles */}
      <div className="grid grid-cols-4 gap-4">
        {tiles.map((tile) => (
          <button
            key={tile.label}
            onClick={() => router.push(tile.href)}
            className="bg-white rounded-lg border p-5 text-left hover:border-indigo-300 transition-colors"
          >
            <p className="text-xs text-gray-500 uppercase tracking-wide">{tile.label}</p>
            <p className={`text-2xl font-bold mt-1 ${tile.color}`}>{tile.value}</p>
            <p className="text-xs text-gray-400 mt-1">{tile.sub}</p>
          </button>
        ))}
      </div>

      {/* Cash Position table */}
      <div className="bg-white rounded-lg border">
        <div className="px-5 py-3 border-b flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">Cash Position</h2>
          <button
            className="text-xs text-indigo-600 hover:underline"
            onClick={() => router.push("/dashboard/finance/cashbook")}
          >
            Manage accounts
          </button>
        </div>
        {cashPosition.length === 0 ? (
          <p className="px-5 py-8 text-sm text-gray-400 text-center">No cash accounts configured</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Account</th>
                <th className="px-5 py-2 text-left">Type</th>
                <th className="px-5 py-2 text-right">Balance</th>
                <th className="px-5 py-2 text-right">Pending In</th>
                <th className="px-5 py-2 text-right">Pending Out</th>
                <th className="px-5 py-2 text-right">Cleared</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {cashPosition.map((row) => (
                <tr key={row.account_id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-medium text-gray-900">{row.account_name}</td>
                  <td className="px-5 py-3">
                    <Badge
                      label={row.account_type}
                      variant={row.account_type === "MPESA" ? "blue" : row.account_type === "BANK" ? "green" : "gray"}
                    />
                  </td>
                  <td className="px-5 py-3 text-right font-semibold">{Number(row.balance).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                  <td className="px-5 py-3 text-right text-green-600">{Number(row.pending_in).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                  <td className="px-5 py-3 text-right text-red-500">{Number(row.pending_out).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                  <td className="px-5 py-3 text-right">{Number(row.cleared_balance).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Quick-links */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Cashbook & Bank Entries", desc: "Record and manage cash/bank/M-Pesa transactions", href: "/dashboard/finance/cashbook" },
          { label: "M-Pesa Reconciliation", desc: "Match M-Pesa receipts to invoices automatically or manually", href: "/dashboard/finance/mpesa" },
          { label: "Product Costing", desc: "View production cost rollups and unit costs by period", href: "/dashboard/finance/costing" },
          { label: "Receivables", desc: "Customer outstanding balances and overdue invoices", href: "/dashboard/finance/receivables" },
          { label: "Budget Management", desc: "Create, approve and track department budgets vs actuals", href: "/dashboard/finance/budget" },
          { label: "Journal Entries", desc: "Double-entry ledger entries and chart of accounts", href: "/dashboard/finance/cashbook?tab=journal" },
        ].map((item) => (
          <button
            key={item.href}
            onClick={() => router.push(item.href)}
            className="bg-white rounded-lg border p-4 text-left hover:border-indigo-300 transition-colors"
          >
            <p className="font-semibold text-sm text-gray-800">{item.label}</p>
            <p className="text-xs text-gray-500 mt-1">{item.desc}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function FinanceDashboardPage() {
  return (
    <RequirePermission permission="finance.view">
      <FinanceDashboardContent />
    </RequirePermission>
  );
}
