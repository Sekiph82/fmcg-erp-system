"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { marketingApi, CRMProfile, CRM_STATUS_COLORS, RelationshipStatus } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

export default function CRMFollowUpPage() {
  const today = new Date().toISOString().split("T")[0];

  const { data: profiles = [], isLoading } = useQuery({
    queryKey: ["crm-followup"],
    queryFn: () => marketingApi.crm.list({ limit: 200 }).then((r) => r.data),
  });

  const overdue = profiles.filter(
    (p) => p.next_followup_date && p.next_followup_date < today
  );
  const dueToday = profiles.filter(
    (p) => p.next_followup_date === today
  );
  const upcoming = profiles.filter(
    (p) => p.next_followup_date && p.next_followup_date > today
  ).slice(0, 20);

  function ProfileRow({ p, highlight }: { p: CRMProfile; highlight?: string }) {
    return (
      <tr className="border-b border-slate-800 hover:bg-slate-800/30">
        <td className="px-4 py-3 font-mono text-xs text-slate-400">{p.customer_id.slice(0, 8)}…</td>
        <td className="px-4 py-3">
          <span className={`font-medium text-sm ${CRM_STATUS_COLORS[p.relationship_status as RelationshipStatus]}`}>
            {p.relationship_status}
          </span>
        </td>
        <td className="px-4 py-3 text-slate-300 text-xs">{p.loyalty_status}</td>
        <td className="px-4 py-3 text-xs">
          <span className={highlight ?? "text-slate-300"}>{p.next_followup_date}</span>
        </td>
        <td className="px-4 py-3 text-xs text-slate-400">{p.acquisition_source ?? "—"}</td>
        <td className="px-4 py-3">
          <Link href={`/dashboard/marketing/crm/${p.id}`}
            className="px-2 py-1 rounded bg-blue-600/20 text-blue-400 hover:bg-blue-600/40 text-xs">
            View
          </Link>
        </td>
      </tr>
    );
  }

  const tableHead = (
    <tr className="border-b border-slate-700/50 bg-[#131c2e]">
      {["Customer ID", "Status", "Loyalty", "Follow-up Date", "Source", ""].map((h) => (
        <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">{h}</th>
      ))}
    </tr>
  );

  return (
    <RequirePermission permission="crm.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">
        <div className="mb-6">
          <a href="/dashboard/marketing/crm" className="text-sm text-slate-400 hover:text-white mb-1 inline-block">
            ← CRM
          </a>
          <h1 className="text-2xl font-bold">Follow-ups Due</h1>
        </div>

        {isLoading ? (
          <p className="text-slate-400">Loading...</p>
        ) : (
          <div className="space-y-8">
            {/* Overdue */}
            <section>
              <h2 className="text-lg font-semibold text-red-400 mb-3">
                Overdue <span className="text-sm font-normal text-slate-400">({overdue.length})</span>
              </h2>
              {overdue.length === 0 ? (
                <p className="text-slate-500 text-sm">No overdue follow-ups.</p>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-red-500/30">
                  <table className="w-full text-sm">
                    <thead>{tableHead}</thead>
                    <tbody>{overdue.map((p) => <ProfileRow key={p.id} p={p} highlight="text-red-400 font-medium" />)}</tbody>
                  </table>
                </div>
              )}
            </section>

            {/* Due Today */}
            <section>
              <h2 className="text-lg font-semibold text-yellow-400 mb-3">
                Due Today <span className="text-sm font-normal text-slate-400">({dueToday.length})</span>
              </h2>
              {dueToday.length === 0 ? (
                <p className="text-slate-500 text-sm">None due today.</p>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-yellow-500/30">
                  <table className="w-full text-sm">
                    <thead>{tableHead}</thead>
                    <tbody>{dueToday.map((p) => <ProfileRow key={p.id} p={p} highlight="text-yellow-400 font-medium" />)}</tbody>
                  </table>
                </div>
              )}
            </section>

            {/* Upcoming */}
            {upcoming.length > 0 && (
              <section>
                <h2 className="text-lg font-semibold text-slate-300 mb-3">
                  Upcoming <span className="text-sm font-normal text-slate-400">({upcoming.length})</span>
                </h2>
                <div className="overflow-x-auto rounded-xl border border-slate-700/50">
                  <table className="w-full text-sm">
                    <thead>{tableHead}</thead>
                    <tbody>{upcoming.map((p) => <ProfileRow key={p.id} p={p} />)}</tbody>
                  </table>
                </div>
              </section>
            )}
          </div>
        )}
      </div>
    </RequirePermission>
  );
}
