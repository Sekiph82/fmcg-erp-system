"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { expensesApi, ExpenseDashboard, fmtCurrency } from "@/lib/expenses";

export default function ExpenseDashboardPage() {
  const [data, setData] = useState<ExpenseDashboard | null>(null);

  useEffect(() => {
    expensesApi.dashboard().then(setData).catch(console.error);
  }, []);

  const kpis = data
    ? [
        { label: "Total Claims", value: data.total_claims, color: "bg-blue-50 text-blue-700" },
        { label: "Pending Approval", value: data.pending_approval, color: "bg-yellow-50 text-yellow-700" },
        { label: "Finance Approved (Unpaid)", value: data.approved_unpaid, color: "bg-purple-50 text-purple-700" },
        { label: "Reimbursed This Month", value: fmtCurrency(data.total_reimbursed_month), color: "bg-green-50 text-green-700" },
        { label: "Claimed This Month", value: fmtCurrency(data.total_claimed_month), color: "bg-indigo-50 text-indigo-700" },
        { label: "Policy Violations (Open)", value: data.policy_violations_open, color: "bg-red-50 text-red-700" },
        { label: "Overdue Advances", value: data.overdue_advances, color: "bg-orange-50 text-orange-700" },
        { label: "AI Alerts", value: data.ai_alerts, color: "bg-gray-50 text-gray-700" },
      ]
    : [];

  const links = [
    { href: "/dashboard/expenses/claims", label: "My Claims" },
    { href: "/dashboard/expenses/claims/new", label: "New Claim" },
    { href: "/dashboard/expenses/approval", label: "Approval Queue" },
    { href: "/dashboard/expenses/reimbursement", label: "Reimbursement" },
    { href: "/dashboard/expenses/advances", label: "Advances" },
    { href: "/dashboard/expenses/categories", label: "Categories" },
    { href: "/dashboard/expenses/policies", label: "Policies" },
    { href: "/dashboard/expenses/reports", label: "Reports" },
    { href: "/dashboard/expenses/ai", label: "AI Insights" },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Expense Claims</h1>
        <Link href="/dashboard/expenses/claims/new" className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
          + New Claim
        </Link>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {kpis.map((k) => (
          <div key={k.label} className={`rounded-xl p-4 ${k.color}`}>
            <p className="text-xs font-medium opacity-70">{k.label}</p>
            <p className="text-2xl font-bold mt-1">{k.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 md:grid-cols-5 gap-3">
        {links.map((l) => (
          <Link key={l.href} href={l.href} className="bg-white border rounded-lg p-3 text-sm font-medium text-center hover:bg-gray-50 shadow-sm">
            {l.label}
          </Link>
        ))}
      </div>
    </div>
  );
}
