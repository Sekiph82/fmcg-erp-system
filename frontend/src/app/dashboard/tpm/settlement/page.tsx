"use client";
import { useQuery } from "@tanstack/react-query";
import { tpmApi, TPMClaim, fmtCurrency, CLAIM_STATUS_BADGE } from "@/lib/tpm";
import Link from "next/link";

export default function TPMSettlementPage() {
  const { data: claims = [], isLoading } = useQuery({
    queryKey: ["tpm-settlement"],
    queryFn: () => tpmApi.getClaims({ status: undefined }),
  });

  const settled = claims.filter((c: TPMClaim) => c.status === "SETTLED");
  const partial = claims.filter((c: TPMClaim) => c.status === "PARTIALLY_SETTLED");
  const approved = claims.filter((c: TPMClaim) => c.status === "APPROVED");

  const totalSettled = settled.reduce((s: number, c: TPMClaim) => s + c.settled_amount, 0);
  const totalPending = approved.reduce((s: number, c: TPMClaim) => s + (c.approved_amount - c.settled_amount), 0);
  const totalPartial = partial.reduce((s: number, c: TPMClaim) => s + (c.approved_amount - c.settled_amount), 0);

  function ClaimRow({ c }: { c: TPMClaim }) {
    const outstanding = c.approved_amount - c.settled_amount;
    return (
      <tr className="border-b border-blue-900/20 hover:bg-blue-950/20">
        <td className="px-4 py-3">
          <span className="font-mono text-xs text-indigo-300">{c.claim_no}</span>
          <p className="text-xs text-gray-500">{c.claim_date}</p>
        </td>
        <td className="px-4 py-3 text-xs text-gray-400">{c.claim_type.replace(/_/g, " ")}</td>
        <td className="px-4 py-3 text-xs text-gray-400">{c.claimant_type}</td>
        <td className="px-4 py-3 text-right text-orange-400">{fmtCurrency(c.claimed_amount)}</td>
        <td className="px-4 py-3 text-right text-green-400">{fmtCurrency(c.approved_amount)}</td>
        <td className="px-4 py-3 text-right text-teal-400">{fmtCurrency(c.settled_amount)}</td>
        <td className={`px-4 py-3 text-right font-medium ${outstanding > 0 ? "text-yellow-400" : "text-gray-500"}`}>
          {fmtCurrency(outstanding)}
        </td>
        <td className="px-4 py-3">
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${CLAIM_STATUS_BADGE[c.status]}`}>
            {c.status.replace(/_/g, " ")}
          </span>
        </td>
        <td className="px-4 py-3">
          {outstanding > 0 && (
            <Link href={`/dashboard/tpm/claims`} className="text-xs text-indigo-400 hover:text-indigo-300">Settle →</Link>
          )}
        </td>
      </tr>
    );
  }

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settlement Tracker</h1>
        <p className="text-sm text-gray-500">Track settlement status of approved trade promotion claims.</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="glow-card p-4 text-center">
          <p className="text-xs text-gray-500">Fully Settled</p>
          <p className="text-lg font-bold text-teal-400 mt-1">{fmtCurrency(totalSettled)}</p>
          <p className="text-xs text-gray-500">{settled.length} claims</p>
        </div>
        <div className="glow-card p-4 text-center">
          <p className="text-xs text-gray-500">Partially Settled (Outstanding)</p>
          <p className="text-lg font-bold text-orange-400 mt-1">{fmtCurrency(totalPartial)}</p>
          <p className="text-xs text-gray-500">{partial.length} claims</p>
        </div>
        <div className="glow-card p-4 text-center">
          <p className="text-xs text-gray-500">Approved Awaiting Settlement</p>
          <p className="text-lg font-bold text-yellow-400 mt-1">{fmtCurrency(totalPending)}</p>
          <p className="text-xs text-gray-500">{approved.length} claims</p>
        </div>
      </div>

      <div className="glass-table overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-blue-900/30">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Claim</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Type</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Claimant</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Claimed</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Approved</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Settled</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Outstanding</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={9} className="text-center py-10 text-gray-400">Loading…</td></tr>
            ) : [...partial, ...approved, ...settled].length === 0 ? (
              <tr><td colSpan={9} className="text-center py-10 text-gray-400">No settlement data.</td></tr>
            ) : [...partial, ...approved, ...settled].map((c: TPMClaim) => (
              <ClaimRow key={c.id} c={c} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
