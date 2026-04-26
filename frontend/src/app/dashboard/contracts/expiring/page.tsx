"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { contractsApi, STATUS_COLORS, PARTY_COLORS, CONTRACT_TYPE_LABELS } from "@/lib/contracts";
import Link from "next/link";

export default function ExpiringContractsPage() {
  const [days, setDays] = useState(60);
  const { data: contracts = [], isLoading } = useQuery({
    queryKey: ["ct-expiring", days],
    queryFn: () => contractsApi.reportExpiring(days),
  });
  const today = new Date();

  return (
    <div className="p-6 space-y-5 min-h-screen bg-[#060d18] text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Expiring Contracts</h1>
          <p className="text-slate-500 text-sm mt-0.5">{contracts.length} contracts expiring within {days} days</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-400">Within</label>
          {[30, 60, 90].map((d) => (
            <button key={d} onClick={() => setDays(d)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${days === d ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"}`}>
              {d}d
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-white/[0.07] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-white/[0.03] text-slate-500 text-xs uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3 text-left">Code</th>
              <th className="px-4 py-3 text-left">Name</th>
              <th className="px-4 py-3 text-left">Type</th>
              <th className="px-4 py-3 text-left">Party</th>
              <th className="px-4 py-3 text-left">Expires</th>
              <th className="px-4 py-3 text-left">Days Left</th>
              <th className="px-4 py-3 text-left">Auto Renew</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {isLoading && <tr><td colSpan={7} className="text-center py-8 text-slate-600">Loading…</td></tr>}
            {!isLoading && contracts.length === 0 && <tr><td colSpan={7} className="text-center py-8 text-slate-600">No contracts expiring soon</td></tr>}
            {contracts.map((c) => {
              const daysLeft = c.end_date ? Math.ceil((new Date(c.end_date).getTime() - today.getTime()) / 86400000) : 0;
              return (
                <tr key={c.id} className="hover:bg-white/[0.02]">
                  <td className="px-4 py-3 font-mono text-xs text-indigo-300">
                    <Link href={`/dashboard/contracts/list/${c.id}`} className="hover:text-indigo-200">{c.contract_code}</Link>
                  </td>
                  <td className="px-4 py-3 text-white max-w-[180px] truncate">{c.contract_name}</td>
                  <td className="px-4 py-3 text-xs text-slate-400">{CONTRACT_TYPE_LABELS[c.contract_type]}</td>
                  <td className="px-4 py-3"><span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${PARTY_COLORS[c.party_type]}`}>{c.party_type}</span></td>
                  <td className="px-4 py-3 text-slate-300 text-xs">{c.end_date}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-semibold ${daysLeft <= 14 ? "text-red-400" : daysLeft <= 30 ? "text-amber-400" : "text-slate-300"}`}>
                      {daysLeft}d
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">{c.auto_renew ? "Yes" : "No"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
