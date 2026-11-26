"use client";
import { useQuery } from "@tanstack/react-query";
import { vanSalesApi, VAN_STATUS_COLORS, VanStatus } from "@/lib/van_sales";
import Link from "next/link";
import { useState } from "react";
import { tx } from "@/lib/i18n/core";

const STATUSES: VanStatus[] = ["ACTIVE", "INACTIVE", "ON_ROUTE", "IN_REPAIR"];

export default function VansListPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const { data: vans = [], isLoading } = useQuery({
    queryKey: ["vans", statusFilter],
    queryFn: () => vanSalesApi.listVans({ status: statusFilter || undefined }),
  });

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">{tx("Vans")}</h1>
          <p className="text-slate-500 text-sm mt-0.5">{vans.length} {tx("vans")}</p>
        </div>
        <Link href="/dashboard/van-sales/vans/new"
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">
          {tx("+ New Van")}
        </Link>
      </div>

      <div className="flex gap-2 flex-wrap">
        <button onClick={() => setStatusFilter("")}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${!statusFilter ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"}`}>
          {tx("All")}
        </button>
        {STATUSES.map((s) => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${statusFilter === s ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"}`}>
            {s}
          </button>
        ))}
      </div>

      <div className="rounded-xl border border-white/[0.07] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-white/[0.03] text-slate-500 text-xs uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3 text-left">{tx("Code")}</th>
              <th className="px-4 py-3 text-left">{tx("Plate")}</th>
              <th className="px-4 py-3 text-left">{tx("Driver")}</th>
              <th className="px-4 py-3 text-left">{tx("Capacity")}</th>
              <th className="px-4 py-3 text-left">{tx("Status")}</th>
              <th className="px-4 py-3 text-left">{tx("Actions")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {isLoading && <tr><td colSpan={6} className="text-center py-8 text-slate-600">{tx("Loading…")}</td></tr>}
            {!isLoading && vans.length === 0 && <tr><td colSpan={6} className="text-center py-8 text-slate-600">{tx("No vans")}</td></tr>}
            {vans.map((v) => (
              <tr key={v.id} className="hover:bg-white/[0.02]">
                <td className="px-4 py-3 text-indigo-300 font-mono text-xs">
                  <Link href={`/dashboard/van-sales/vans/${v.id}`} className="hover:text-indigo-200">{v.van_code}</Link>
                </td>
                <td className="px-4 py-3 text-slate-300">{v.plate_number ?? "—"}</td>
                <td className="px-4 py-3 text-slate-400 text-xs font-mono">{v.driver_id ? v.driver_id.slice(0, 8) + "…" : "—"}</td>
                <td className="px-4 py-3 text-slate-400">{v.capacity_kg ? tx("{capacity_kg} kg", { capacity_kg: v.capacity_kg }) : "—"}</td>
                <td className="px-4 py-3">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${VAN_STATUS_COLORS[v.status]}`}>{v.status}</span>
                </td>
                <td className="px-4 py-3">
                  <Link href={`/dashboard/van-sales/vans/${v.id}`} className="text-xs text-indigo-400 hover:text-indigo-300">{tx("View →")}</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
