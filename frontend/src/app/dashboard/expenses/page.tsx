"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { expensesApi, ExpenseDashboard, fmtCurrency } from "@/lib/expenses";

export default function ExpenseDashboardPage() {
  const [data, setData] = useState<ExpenseDashboard | null>(null);

  useEffect(() => { expensesApi.dashboard().then(setData).catch(console.error); }, []);

  const kpis = data ? [
    { label: "Total Claims",               value: data.total_claims,                    color: "text-white" },
    { label: "Pending Approval",           value: data.pending_approval,               color: "text-amber-400" },
    { label: "Finance Approved (Unpaid)",  value: data.approved_unpaid,                color: "text-purple-400" },
    { label: "Reimbursed This Month",      value: fmtCurrency(data.total_reimbursed_month), color: "text-emerald-400" },
    { label: "Claimed This Month",         value: fmtCurrency(data.total_claimed_month),    color: "text-blue-400" },
    { label: "Policy Violations",          value: data.policy_violations_open,         color: "text-red-400" },
    { label: "Overdue Advances",           value: data.overdue_advances,               color: "text-orange-400" },
    { label: "AI Alerts",                  value: data.ai_alerts,                      color: "text-slate-400" },
  ] : [];

  const links = [
    { href: "/dashboard/expenses/claims",        label: "My Claims" },
    { href: "/dashboard/expenses/claims/new",    label: "New Claim" },
    { href: "/dashboard/expenses/approval",      label: "Approval Queue" },
    { href: "/dashboard/expenses/reimbursement", label: "Reimbursement" },
    { href: "/dashboard/expenses/advances",      label: "Advances" },
    { href: "/dashboard/expenses/categories",    label: "Categories" },
    { href: "/dashboard/expenses/policies",      label: "Policies" },
    { href: "/dashboard/expenses/reports",       label: "Reports" },
    { href: "/dashboard/expenses/ai",            label: "AI Insights" },
  ];

  return (
    <div className="p-6 space-y-6 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Expense Claims</h1>
          <p className="text-slate-500 text-sm mt-0.5">Employee expense submission, approval & reimbursement</p>
        </div>
        <Link href="/dashboard/expenses/claims/new"
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">
          + New Claim
        </Link>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {kpis.map((k) => (
          <div key={k.label} className="glow-card p-5">
            <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">{k.label}</p>
            <p className={`text-2xl font-bold ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 md:grid-cols-5 gap-3">
        {links.map((l) => (
          <Link key={l.href} href={l.href}
            className="glow-card hover:bg-white/[0.04] p-4 text-sm font-medium text-slate-300 text-center transition-colors">
            {l.label}
          </Link>
        ))}
      </div>
    </div>
  );
}
