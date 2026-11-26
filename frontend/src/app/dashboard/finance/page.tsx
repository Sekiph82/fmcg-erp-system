"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { financeApi } from "@/lib/finance";
import { Badge } from "@/components/ui/Badge";
import { RequirePermission } from "@/components/PermissionGuard";
import { useAuth } from "@/context/AuthContext";
import { tx } from "@/lib/i18n/core";

function FinanceDashboardContent() {
  const router = useRouter();
  const { hasPermission } = useAuth();
  const canReports = hasPermission("finance.export");  // cash position and M-Pesa summary are export-level reports

  const { data: cashPosition = [] } = useQuery({
    queryKey: ["finance-cash-position"],
    queryFn: () => financeApi.cashPosition(),
    enabled: canReports,
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
    enabled: canReports,
  });

  const totalCash = cashPosition.reduce((s, r) => s + Number(r.balance), 0);
  const totalReceivables = receivables.reduce((s, r) => s + Number(r.outstanding), 0);
  const overdueCount = receivables.filter((r) => r.days_overdue && r.days_overdue > 0).length;
  const exceptionCount = recons.filter((r) => r.status === "EXCEPTION").length;
  const unmatchedCount = recons.filter((r) => r.status === "UNMATCHED").length;
  const monthMpesaTotal = mpesaSummary.reduce((s, r) => s + Number(r.total_received), 0);
  const monthMpesaMatched = mpesaSummary.reduce((s, r) => s + Number(r.matched_count), 0);
  const monthMpesaUnmatched = mpesaSummary.reduce((s, r) => s + Number(r.unmatched_count), 0);

  const tiles = [
    {
      label: tx("Total Cash & Bank"),
      value: `KES ${totalCash.toLocaleString(undefined, { minimumFractionDigits: 0 })}`,
      sub: tx("{length} accounts", { length: cashPosition.length }),
      color: "text-green-700",
      href: "/dashboard/finance/cashbook",
    },
    {
      label: tx("Outstanding Receivables"),
      value: `KES ${totalReceivables.toLocaleString(undefined, { minimumFractionDigits: 0 })}`,
      sub: `${overdueCount > 0 ? tx("{overdueCount} overdue", { overdueCount }) : "no overdue"}`,
      color: overdueCount > 0 ? "text-red-600" : "text-orange-600",
      href: "/dashboard/finance/receivables",
    },
    {
      label: tx("M-Pesa This Month"),
      value: `KES ${monthMpesaTotal.toLocaleString(undefined, { minimumFractionDigits: 0 })}`,
      sub: tx("{monthMpesaMatched} matched / {monthMpesaUnmatched} pending", { monthMpesaMatched, monthMpesaUnmatched }),
      color: "text-indigo-700",
      href: "/dashboard/finance/mpesa",
    },
    {
      label: tx("Recon Exceptions"),
      value: exceptionCount.toString(),
      sub: tx("{unmatchedCount} unmatched", { unmatchedCount }),
      color: exceptionCount > 0 ? "text-red-600" : "text-gray-700",
      href: "/dashboard/finance/mpesa",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{tx("Finance & Accounting")}</h1>
          <p className="text-sm text-gray-500 mt-1">{tx("Cash, M-Pesa, receivables, costing & budgets")}</p>
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
          <h2 className="font-semibold text-gray-800">{tx("Cash Position")}</h2>
          <button
            className="text-xs text-indigo-600 hover:underline"
            onClick={() => router.push("/dashboard/finance/cashbook")}
          >
            {tx("Manage accounts")}
          </button>
        </div>
        {cashPosition.length === 0 ? (
          <p className="px-5 py-8 text-sm text-gray-400 text-center">{tx("No cash accounts configured")}</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">{tx("Account")}</th>
                <th className="px-5 py-2 text-left">{tx("Type")}</th>
                <th className="px-5 py-2 text-right">{tx("Balance")}</th>
                <th className="px-5 py-2 text-right">{tx("Pending In")}</th>
                <th className="px-5 py-2 text-right">{tx("Pending Out")}</th>
                <th className="px-5 py-2 text-right">{tx("Cleared")}</th>
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
          { label: tx("Cashbook & Bank Entries"), desc: tx("Record and manage cash/bank/M-Pesa transactions"), href: "/dashboard/finance/cashbook" },
          { label: tx("M-Pesa Reconciliation"), desc: tx("Match M-Pesa receipts to invoices automatically or manually"), href: "/dashboard/finance/mpesa" },
          { label: tx("Product Costing"), desc: tx("View production cost rollups and unit costs by period"), href: "/dashboard/finance/costing" },
          { label: tx("Receivables"), desc: tx("Customer outstanding balances and overdue invoices"), href: "/dashboard/finance/receivables" },
          { label: tx("Budget Management"), desc: tx("Create, approve and track department budgets vs actuals"), href: "/dashboard/finance/budget" },
          { label: tx("Journal Entries"), desc: tx("Double-entry ledger entries and chart of accounts"), href: "/dashboard/finance/cashbook?tab=journal" },
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

const FinanceAccountingPage   = dynamic(() => import("@/app/dashboard/finance/accounting/page"),    { ssr: false });
const FinanceCashbookPage     = dynamic(() => import("@/app/dashboard/finance/cashbook/page"),       { ssr: false });
const FinanceReceivablesPage  = dynamic(() => import("@/app/dashboard/finance/receivables/page"),    { ssr: false });
const FinanceBudgetPage       = dynamic(() => import("@/app/dashboard/finance/budget/page"),         { ssr: false });
const FinanceMpesaPage        = dynamic(() => import("@/app/dashboard/finance/mpesa/page"),          { ssr: false });
const FinanceCostingPage      = dynamic(() => import("@/app/dashboard/finance/costing/page"),        { ssr: false });
const FinanceExchangeRatesPage= dynamic(() => import("@/app/dashboard/finance/exchange-rates/page"), { ssr: false });
const FinancePostingRulesPage = dynamic(() => import("@/app/dashboard/finance/posting-rules/page"), { ssr: false });
const FinanceEtimsPage        = dynamic(() => import("@/app/dashboard/finance/etims/page"),          { ssr: false });
const FinanceVATPage          = dynamic(() => import("@/app/dashboard/finance/vat-returns/page"),    { ssr: false });
const BankReconPage           = dynamic(() => import("@/app/dashboard/bank-reconciliation/page"),    { ssr: false });
const InvoiceMatchPage        = dynamic(() => import("@/app/dashboard/invoice-match/page"),          { ssr: false });
const FixedAssetsPage         = dynamic(() => import("@/app/dashboard/fixed-assets/page"),           { ssr: false });
const DimensionsPage          = dynamic(() => import("@/app/dashboard/dimensions/page"),             { ssr: false });
const DunningPage             = dynamic(() => import("@/app/dashboard/dunning/page"),                { ssr: false });
const TaxPage                 = dynamic(() => import("@/app/dashboard/tax/page"),                    { ssr: false });
const BankAPIPage             = dynamic(() => import("@/app/dashboard/bank-api/page"),               { ssr: false });
const ExpensesPage            = dynamic(() => import("@/app/dashboard/expenses/page"),               { ssr: false });

export default function FinanceDashboardPage() {
  const tabs = [
    { key: "overview",       label: tx("Overview"),        permission: "finance.view", exact: true, content: <FinanceDashboardContent /> },
    { key: "accounting",     label: tx("Accounting"),      permission: "finance.view", exact: true, content: <FinanceAccountingPage /> },
    { key: "cashbook",       label: tx("Cashbook"),        permission: "finance.view", exact: true, content: <FinanceCashbookPage /> },
    { key: "receivables",    label: tx("Receivables"),     permission: "finance.view", exact: true, content: <FinanceReceivablesPage /> },
    { key: "budget",         label: tx("Budget"),          permission: "finance.view", exact: true, content: <FinanceBudgetPage /> },
    { key: "mpesa",          label: tx("M-Pesa"),          permission: "finance.view", exact: true, content: <FinanceMpesaPage /> },
    { key: "costing",        label: tx("Costing"),         permission: "finance.view", exact: true, content: <FinanceCostingPage /> },
    { key: "exchange-rates", label: tx("Exchange Rates"),  permission: "finance.view", exact: true, content: <FinanceExchangeRatesPage /> },
    { key: "posting-rules", label: tx("Posting Rules"),   permission: "finance.view", exact: true, content: <FinancePostingRulesPage /> },
    { key: "etims",          label: "eTIMS",           permission: "finance.view", exact: true, content: <FinanceEtimsPage /> },
    { key: "vat-returns",    label: tx("VAT Returns"),     permission: "finance.view", exact: true, content: <FinanceVATPage /> },
    { key: "bank-recon",     label: tx("Bank Recon"),      permission: "finance.view", content: <BankReconPage /> },
    { key: "invoice-match",  label: tx("Invoice Match"),   permission: "finance.view", exact: true, content: <InvoiceMatchPage /> },
    { key: "fixed-assets",   label: tx("Fixed Assets"),    permission: "finance.view", exact: true, content: <FixedAssetsPage /> },
    { key: "dimensions",     label: tx("Dimensions"),      permission: "finance.view", exact: true, content: <DimensionsPage /> },
    { key: "dunning",        label: tx("Dunning"),         permission: "finance.view", exact: true, content: <DunningPage /> },
    { key: "tax",            label: tx("Tax"),             permission: "finance.view", exact: true, content: <TaxPage /> },
    { key: "bank-api",       label: tx("Bank API"),        permission: "finance.view", content: <BankAPIPage /> },
    { key: "expenses",       label: tx("Expenses"),        permission: "hr.view",      content: <ExpensesPage /> },
  ];
  return (
    <ModuleWorkspace
      title={tx("Finance")}
      description={tx("Accounting, cashbook, receivables, bank recon, tax, expenses")}
      permission="finance.view"
      tabs={tabs}
      defaultTab="overview"
    />
  );
}
