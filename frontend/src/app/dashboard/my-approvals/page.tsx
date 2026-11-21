"use client";
// "My Approvals" (M40.S02.T001): everything waiting for my decision across modules, oldest first, with a link to the
// screen where I decide. Approval-workflow steps can be approved or rejected right here.
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { approvalsApi } from "@/lib/approvals";
import { useAuth } from "@/context/AuthContext";

interface Item { id: string; ref: string; since: string | null; rfq_id?: string; asset_id?: string }
interface Group { key: string; label: string; count: number; link: string; items: Item[] }

// Decide right here, through each module's own approve/reject endpoint (each keeps its own permission rules).
type Call = (i: Item, uid: string, note: string) => Promise<unknown>;
const post = (u: string, b?: object) => apiClient.post(u, b ?? {});
const patch = (u: string, b: object) => apiClient.patch(u, b);
const A = "/api/v1";
const DECIDE: Record<string, { approve: Call; reject?: Call }> = {
  approval_engine: { approve: (i) => approvalsApi.approve(i.id), reject: (i, _u, n) => approvalsApi.reject(i.id, n) },
  purchase_request: { approve: (i) => post(`${A}/procurement/pr/${i.id}/approve`, { approve: true }),
                      reject: (i, _u, n) => post(`${A}/procurement/pr/${i.id}/approve`, { approve: false, rejection_reason: n }) },
  purchase_order: { approve: (i) => post(`${A}/procurement/po/${i.id}/approve`) },
  rfq_award: { approve: (i, _u, n) => post(`${A}/procurement/rfq/${i.rfq_id}/awards/${i.id}/approve`, { comments: n || null }),
               reject: (i, _u, n) => post(`${A}/procurement/rfq/${i.rfq_id}/awards/${i.id}/reject`, { comments: n }) },
  supplier_document: { approve: (i) => post(`${A}/supplier-portal/documents/${i.id}/review`, { review_status: "ACCEPTED", reviewed_by: "-" }),
                       reject: (i, _u, n) => post(`${A}/supplier-portal/documents/${i.id}/review`, { review_status: "REJECTED", reviewed_by: "-", notes: n }) },
  leave: { approve: (i) => post(`${A}/hr/leave/${i.id}/review`, { approval_status: "APPROVED" }),
           reject: (i, _u, n) => post(`${A}/hr/leave/${i.id}/review`, { approval_status: "REJECTED", review_note: n }) },
  ess_leave: { approve: (i, u) => post(`${A}/ess/leave-requests/${i.id}/approve`, { approver_id: u }),
               reject: (i, u, n) => post(`${A}/ess/leave-requests/${i.id}/reject`, { approver_id: u, rejection_reason: n }) },
  ess_request: { approve: (i, u) => patch(`${A}/ess/requests/${i.id}/review`, { approver_id: u, status: "approved" }),
                 reject: (i, u, n) => patch(`${A}/ess/requests/${i.id}/review`, { approver_id: u, status: "rejected", hr_notes: n }) },
  expense_manager: { approve: (i) => post(`${A}/expenses/claims/${i.id}/manager-approve`), reject: (i, _u, n) => post(`${A}/expenses/claims/${i.id}/reject`, { notes: n }) },
  expense_finance: { approve: (i) => post(`${A}/expenses/claims/${i.id}/finance-approve`), reject: (i, _u, n) => post(`${A}/expenses/claims/${i.id}/reject`, { notes: n }) },
  timesheet: { approve: (i, u) => post(`${A}/timesheets/${i.id}/approve`, { approver_user_id: u }),
               reject: (i, u, n) => post(`${A}/timesheets/${i.id}/reject`, { approver_user_id: u, comments: n }) },
  payroll_run: { approve: (i) => post(`${A}/payroll-ke/runs/${i.id}/approve`) },
  stock_count: { approve: (i) => post(`${A}/wms/counts/${i.id}/approve`) },
  count_adjustment: { approve: (i) => post(`${A}/cycle-count/adjustments/approve`, { entry_ids: [i.id] }) },
  return: { approve: (i) => post(`${A}/returns/${i.id}/approve`) },
  portal_claim: { approve: (i) => patch(`${A}/portal/claims/${i.id}/review`, { status: "RESOLVED" }),
                  reject: (i, _u, n) => patch(`${A}/portal/claims/${i.id}/review`, { status: "REJECTED", resolution_notes: n }) },
  promo_override: { approve: (i) => post(`${A}/promotions/override-requests/${i.id}/approve`, { approved: true }),
                    reject: (i, _u, n) => post(`${A}/promotions/override-requests/${i.id}/approve`, { approved: false, approver_notes: n }) },
  campaign: { approve: (i) => post(`${A}/marketing/campaigns/${i.id}/approve`) },
  trade_spend: { approve: (i) => post(`${A}/marketing/trade-spend/${i.id}/approve`) },
  brand_spend: { approve: (i) => post(`${A}/marketing/brand-spend/${i.id}/approve`) },
  tpm_claim: { approve: (i) => post(`${A}/tpm/claims/${i.id}/review`, { approved: true }),
               reject: (i, _u, n) => post(`${A}/tpm/claims/${i.id}/review`, { approved: false, reviewer_notes: n }) },
  brand_asset: { approve: (i) => post(`${A}/brand-assets/${i.asset_id}/stages/${i.id}/approve`, {}),
                 reject: (i, _u, n) => post(`${A}/brand-assets/${i.asset_id}/stages/${i.id}/reject`, { notes: n }) },
  shelf_life_extension: { approve: (i) => post(`${A}/shelf-life/extensions/${i.id}/approve`),
                          reject: (i, _u, n) => post(`${A}/shelf-life/extensions/${i.id}/reject?reason=${encodeURIComponent(n)}`) },
};

const err = (e: unknown) => {
  const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  const inner = (d as { detail?: unknown })?.detail;
  return typeof d === "string" ? d : typeof inner === "string" ? inner : "Something went wrong.";
};
const age = (s: string | null) => {
  if (!s) return "";
  const days = Math.floor((Date.now() - new Date(s).getTime()) / 86400000);
  return days <= 0 ? "today" : days === 1 ? "1 day" : `${days} days`;
};

export default function MyApprovals() {
  const [data, setData] = useState<{ total: number; groups: Group[] } | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const { user } = useAuth();
  const load = useCallback(() => apiClient.get("/api/v1/approvals/inbox").then((r) => setData(r.data)).catch((e) => setMsg({ ok: false, text: err(e) })), []);
  useEffect(() => { load(); }, [load]);

  const decide = async (key: string, i: Item, ok: boolean) => {
    const d = DECIDE[key];
    const note = ok ? "" : (window.prompt("Reason for rejecting") ?? "").trim();
    if (!d || (!ok && !note)) return;
    setBusy(i.id);
    try {
      await (ok ? d.approve(i, user?.id ?? "", note) : d.reject!(i, user?.id ?? "", note));
      setMsg({ ok: true, text: `${i.ref}: ${ok ? "approved" : "rejected"}.` });
      await load();
    } catch (e) { setMsg({ ok: false, text: `${i.ref}: ${err(e)}` }); }
    setBusy(null);
  };

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto space-y-4">
      <div>
        <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">My Approvals</h1>
        <p className="text-sm text-gray-500">Everything waiting for your decision. You also get a notification when something new arrives.</p>
      </div>
      {msg && <div role="status" className={`rounded-lg px-3 py-2 text-sm ${msg.ok ? "bg-green-50 text-green-800" : "bg-red-50 text-red-700"}`}>{msg.text}</div>}
      {!data ? <p className="text-sm text-gray-500">Loading…</p> : data.total === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">Nothing is waiting for you.</div>
      ) : data.groups.map((g) => (
        <section key={g.key} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
          <header className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800">
            <h2 className="font-semibold text-gray-900 dark:text-gray-100">{g.label} <span className="ml-1 rounded-full bg-amber-100 text-amber-800 px-2 py-0.5 text-xs">{g.count}</span></h2>
            {g.key !== "approval_engine" && <Link href={g.link} className="text-sm text-indigo-600 hover:underline">{DECIDE[g.key] ? "Open screen →" : "Open to decide →"}</Link>}
          </header>
          <ul className="divide-y divide-gray-100 dark:divide-gray-800">
            {g.items.map((i) => (
              <li key={i.id} className="flex items-center justify-between gap-3 px-4 py-2 text-sm">
                <span className="font-mono text-gray-800 dark:text-gray-200">{i.ref}</span>
                <span className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">waiting {age(i.since)}</span>
                  {DECIDE[g.key] && <>
                    <button disabled={busy === i.id} onClick={() => decide(g.key, i, true)} className="rounded-md bg-green-600 px-2.5 py-1 text-xs font-medium text-white disabled:opacity-50">Approve</button>
                    {DECIDE[g.key].reject && <button disabled={busy === i.id} onClick={() => decide(g.key, i, false)} className="rounded-md border border-red-300 px-2.5 py-1 text-xs font-medium text-red-700 disabled:opacity-50">Reject</button>}
                  </>}
                </span>
              </li>
            ))}
            {g.count > g.items.length && <li className="px-4 py-2 text-xs text-gray-500">…and {g.count - g.items.length} more on the screen.</li>}
          </ul>
        </section>
      ))}
    </div>
  );
}
