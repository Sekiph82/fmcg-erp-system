"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { contractsApi, STATUS_COLORS, PARTY_COLORS, CONTRACT_TYPE_LABELS, ContractStatus, PartyType } from "@/lib/contracts";
import Link from "next/link";
import { tx } from "@/lib/i18n/core";

const STATUSES: ContractStatus[] = ["DRAFT","UNDER_REVIEW","APPROVED","ACTIVE","EXPIRED","TERMINATED","ARCHIVED"];
const PARTIES: PartyType[] = ["CUSTOMER","DISTRIBUTOR","SUPPLIER"];

export default function ContractListPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [partyFilter, setPartyFilter] = useState("");

  const { data: contracts = [], isLoading } = useQuery({
    queryKey: ["contracts", statusFilter, partyFilter],
    queryFn: () => contractsApi.list({
      status: statusFilter || undefined,
      party_type: partyFilter || undefined,
      limit: 100,
    }),
  });

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">{tx("All Contracts")}</h1>
          <p className="text-slate-500 text-sm mt-0.5">{contracts.length} {tx("contracts")}</p>
        </div>
        <Link href="/dashboard/contracts/new"
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">
          {tx("+ New Contract")}
        </Link>
      </div>

      <div className="flex gap-2 flex-wrap">
        {["", ...PARTIES].map((p) => (
          <button key={p} onClick={() => setPartyFilter(p)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${partyFilter === p ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"}`}>
            {p || tx("All Parties")}
          </button>
        ))}
        <div className="w-px h-6 bg-white/[0.07] self-center" />
        {["", ...STATUSES].map((s) => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${statusFilter === s ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"}`}>
            {s || tx("All Status")}
          </button>
        ))}
      </div>

      <div className="rounded-xl border border-white/[0.07] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-white/[0.03] text-slate-500 text-xs uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3 text-left">{tx("Code")}</th>
              <th className="px-4 py-3 text-left">{tx("Name")}</th>
              <th className="px-4 py-3 text-left">{tx("Type")}</th>
              <th className="px-4 py-3 text-left">{tx("Party")}</th>
              <th className="px-4 py-3 text-left">{tx("Start")}</th>
              <th className="px-4 py-3 text-left">{tx("End")}</th>
              <th className="px-4 py-3 text-left">{tx("Status")}</th>
              <th className="px-4 py-3 text-left">{tx("Ver")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {isLoading && <tr><td colSpan={8} className="text-center py-8 text-slate-600">{tx("Loading…")}</td></tr>}
            {!isLoading && contracts.length === 0 && <tr><td colSpan={8} className="text-center py-8 text-slate-600">{tx("No contracts")}</td></tr>}
            {contracts.map((c) => (
              <tr key={c.id} className="hover:bg-white/[0.02]">
                <td className="px-4 py-3 font-mono text-xs text-indigo-300">
                  <Link href={`/dashboard/contracts/list/${c.id}`} className="hover:text-indigo-200">{c.contract_code}</Link>
                </td>
                <td className="px-4 py-3 text-white max-w-[200px] truncate">{c.contract_name}</td>
                <td className="px-4 py-3 text-xs text-slate-400">{CONTRACT_TYPE_LABELS[c.contract_type]}</td>
                <td className="px-4 py-3">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${PARTY_COLORS[c.party_type]}`}>{c.party_type}</span>
                </td>
                <td className="px-4 py-3 text-xs text-slate-400">{c.start_date}</td>
                <td className="px-4 py-3 text-xs text-slate-400">{c.end_date ?? "—"}</td>
                <td className="px-4 py-3">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[c.status]}`}>{c.status}</span>
                </td>
                <td className="px-4 py-3 text-slate-500 text-xs">{tx("v")}{c.current_version}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
