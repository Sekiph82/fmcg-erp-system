"use client";
import { useQuery } from "@tanstack/react-query";
import { subscriptionApi, STATUS_COLORS, RECURRENCE_LABELS, SubscriptionStatus } from "@/lib/subscription";
import Link from "next/link";
import { useState } from "react";

const STATUSES: SubscriptionStatus[] = ["DRAFT", "ACTIVE", "PAUSED", "EXPIRED", "CANCELLED", "ARCHIVED"];

export default function TemplateListPage() {
  const [statusFilter, setStatusFilter] = useState<string>("");

  const { data: templates = [], isLoading } = useQuery({
    queryKey: ["sub-templates", statusFilter],
    queryFn: () => subscriptionApi.listTemplates({ status: statusFilter || undefined, limit: 100 }),
  });

  return (
    <div className="p-6 space-y-5 min-h-screen bg-[#060d18] text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Recurring Templates</h1>
          <p className="text-slate-500 text-sm mt-0.5">{templates.length} templates</p>
        </div>
        <Link
          href="/dashboard/recurring-orders/templates/new"
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium"
        >
          + New Template
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setStatusFilter("")}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
            statusFilter === "" ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"
          }`}
        >
          All
        </button>
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              statusFilter === s ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="rounded-xl border border-white/[0.07] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-white/[0.03] text-slate-500 text-xs uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3 text-left">Code</th>
              <th className="px-4 py-3 text-left">Name</th>
              <th className="px-4 py-3 text-left">Customer</th>
              <th className="px-4 py-3 text-left">Recurrence</th>
              <th className="px-4 py-3 text-left">Next Generation</th>
              <th className="px-4 py-3 text-left">Mode</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Lines</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {isLoading && (
              <tr><td colSpan={8} className="text-center py-8 text-slate-600">Loading...</td></tr>
            )}
            {!isLoading && templates.length === 0 && (
              <tr><td colSpan={8} className="text-center py-8 text-slate-600">No templates</td></tr>
            )}
            {templates.map((t) => (
              <tr key={t.id} className="hover:bg-white/[0.02] transition-colors">
                <td className="px-4 py-3 font-mono text-indigo-300 text-xs">
                  <Link href={`/dashboard/recurring-orders/templates/${t.id}`} className="hover:text-indigo-200">
                    {t.template_code}
                  </Link>
                </td>
                <td className="px-4 py-3 text-white">{t.template_name}</td>
                <td className="px-4 py-3 text-slate-400 text-xs font-mono">{t.customer_id.slice(0, 8)}…</td>
                <td className="px-4 py-3 text-slate-300 text-xs">{RECURRENCE_LABELS[t.recurrence_type]}</td>
                <td className="px-4 py-3 text-slate-400 text-xs">
                  {t.next_generation_date ?? <span className="text-slate-600">—</span>}
                </td>
                <td className="px-4 py-3 text-xs text-slate-400">{t.generation_mode.replace("_", " ")}</td>
                <td className="px-4 py-3">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[t.status]}`}>
                    {t.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-400">{t.lines.length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
