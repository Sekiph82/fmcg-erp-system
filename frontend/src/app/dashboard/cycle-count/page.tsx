"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getDashboard, Dashboard } from "@/lib/cycleCount";

export default function CycleCountDashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboard().then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const navLinks = [
    { href: "/dashboard/cycle-count/plans",    label: "Count Plans",       desc: "ABC/random/location strategies" },
    { href: "/dashboard/cycle-count/tasks",    label: "Count Tasks",       desc: "Daily task queue" },
    { href: "/dashboard/cycle-count/entries",  label: "Count Entries",     desc: "Record physical counts" },
    { href: "/dashboard/cycle-count/variances", label: "Variance Review",  desc: "Approve/reject adjustments" },
    { href: "/dashboard/cycle-count/reports",  label: "Reports & AI",      desc: "Accuracy, variance, AI insights" },
  ];

  if (loading) return <div className="p-8 text-gray-500">Loading...</div>;

  const kpis = data ? [
    { label: "Active Plans",       value: data.active_plans,         color: "text-green-700" },
    { label: "Tasks Today",        value: data.tasks_today,          color: "text-gray-900" },
    { label: "Overdue",            value: data.tasks_overdue,        color: "text-red-600",  alert: data.tasks_overdue > 0 },
    { label: "Pending",            value: data.tasks_pending,        color: "text-gray-900" },
    { label: "Done Today",         value: data.tasks_completed_today, color: "text-green-700" },
    { label: "Accuracy (7d)",      value: `${data.accuracy_pct_7d}%`, color: data.accuracy_pct_7d >= 98 ? "text-green-700" : "text-amber-600" },
    { label: "Open Variances",     value: data.open_variances,       color: "text-amber-600", alert: data.open_variances > 0 },
    { label: "Pending Adj.",       value: data.pending_adjustments,  color: "text-indigo-700", alert: data.pending_adjustments > 0 },
  ] : [];

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Cycle Count</h1>
        <p className="text-sm text-gray-500 mt-1">Inventory accuracy through scheduled periodic counting</p>
      </div>

      <div className="grid grid-cols-4 sm:grid-cols-8 gap-3">
        {kpis.map((k) => (
          <div key={k.label} className={`bg-white rounded-xl border p-3 ${(k as { alert?: boolean }).alert ? "border-amber-300" : "border-gray-200"}`}>
            <div className={`text-xl font-bold ${k.color}`}>{k.value}</div>
            <div className="text-xs text-gray-500 mt-1 leading-tight">{k.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {navLinks.map((l) => (
          <Link key={l.href} href={l.href} className="bg-white border border-gray-200 rounded-xl p-4 hover:border-indigo-300 hover:bg-indigo-50 transition-colors">
            <div className="font-semibold text-gray-900 text-sm">{l.label}</div>
            <div className="text-xs text-gray-500 mt-1">{l.desc}</div>
          </Link>
        ))}
      </div>

      {data && data.recent_variances.length > 0 && (
        <div className="bg-white rounded-2xl border border-amber-200 p-6">
          <h2 className="text-sm font-semibold text-amber-700 mb-3">Recent Variances (Outside Tolerance)</h2>
          <div className="space-y-2">
            {data.recent_variances.map((v, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <span className="font-mono text-xs text-gray-500">{String(v.id).slice(0, 8)}...</span>
                <span className={`font-medium ${Number(v.variance_qty) < 0 ? "text-red-600" : "text-amber-600"}`}>
                  {Number(v.variance_qty) > 0 ? "+" : ""}{Number(v.variance_qty).toFixed(2)}
                </span>
                <span className="text-gray-500">{Number(v.variance_pct).toFixed(1)}%</span>
                {v.variance_value && (
                  <span className="text-gray-500">KES {Math.abs(Number(v.variance_value)).toLocaleString()}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
