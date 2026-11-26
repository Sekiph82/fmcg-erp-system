"use client";
// M48.S01.T023: approvals for direct marketing sends. Lists this target's pending and approved requests (payload
// summary + SHA-256), lets a second editor approve or reject, and lets the sender pick an approved request to send with.
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiError, sendApprovalsApi, type SendApproval, type SendKind, type SendPolicy } from "@/lib/send_approvals";
import { tx } from "@/lib/i18n/core";

const summary = (p: Record<string, unknown>) =>
  Object.entries(p).filter(([k]) => k !== "body" && k !== "group_id" && k !== "design_id")
    .map(([k, v]) => `${k.replace(/_/g, " ")}: ${Array.isArray(v) ? v.join(", ") || "all" : typeof v === "object" && v ? JSON.stringify(v) : String(v ?? "—")}`)
    .join(" · ");

export function SendApprovalsPanel({ kind, targetId, picked, onPick, refresh, onPolicy }: {
  kind: SendKind; targetId: string; picked: string | null; onPick: (id: string | null) => void; refresh: number;
  onPolicy?: (p: SendPolicy | null) => void;
}) {
  const { user } = useAuth();
  const [rows, setRows] = useState<SendApproval[]>([]);
  const [policy, setPolicy] = useState<SendPolicy | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const load = useCallback(async () => {
    try {
      const [p, pending, approved] = await Promise.all([sendApprovalsApi.policy(kind), sendApprovalsApi.list(kind, "PENDING"),
        sendApprovalsApi.list(kind, "APPROVED")]);
      setPolicy(p); onPolicy?.(p);
      setRows([...pending, ...approved].filter((r) => r.target_id === targetId));
    } catch (e) { setMsg({ ok: false, text: apiError(e, "Could not load approvals.") }); onPolicy?.(null); }
  }, [kind, targetId, onPolicy]);
  useEffect(() => { load(); }, [load, refresh]);
  useEffect(() => { if (picked && !rows.some((r) => r.id === picked && r.status === "APPROVED")) onPick(null); }, [rows, picked, onPick]);

  const decide = async (r: SendApproval, action: "approve" | "reject") => {
    try { await sendApprovalsApi.decide(kind, r.id, action); setMsg({ ok: true, text: action === "approve" ? "Approved." : "Rejected." }); load(); }
    catch (e) { setMsg({ ok: false, text: apiError(e) }); }
  };

  return (
    <div className="border rounded p-2 space-y-1 text-xs bg-gray-50">
      <p className="font-medium">{tx("Send approvals")}</p>
      {policy && <p className="text-gray-600">
        {policy.approval_required ? tx("A second editor must approve this exact content before it is sent.") : tx("Approval is not switched on; you can send directly.")}
        {" "}{tx("Your direct marketing sends today:")} {policy.used_today} {tx("of")} {policy.daily_cap}.</p>}
      {msg && <p role="status" className={msg.ok ? "text-emerald-700" : "text-red-700"}>{msg.text}</p>}
      {rows.length === 0 ? <p className="text-gray-500">{tx("No open approval requests for this")} {kind === "abm" ? tx("group") : tx("design")}.</p> :
        <ul className="divide-y">{rows.map((r) => {
          const own = !!user && r.requested_by === user.username;
          return (
            <li key={r.id} className="py-1 space-y-0.5">
              <div><b>{r.status.toLowerCase()}</b> {tx("· requested by")} {r.requested_by}{r.decided_by ? tx(" · decided by {decided_by}", { decided_by: r.decided_by }) : ""}</div>
              <div className="text-gray-700 break-words">{summary(r.payload)}</div>
              <div className="font-mono text-[10px] text-gray-500 break-all" title={tx("SHA-256 of the exact payload")}>{tx("sha256")} {r.content_hash}</div>
              {r.status === "PENDING" && <div className="flex flex-wrap gap-2 items-center">
                <button disabled={own} title={own ? tx("You requested this send; another editor must approve it.") : undefined}
                  onClick={() => decide(r, "approve")} className="rounded bg-emerald-600 px-2 py-0.5 text-white disabled:opacity-50">{tx("Approve")}</button>
                <button disabled={own} title={own ? tx("You requested this send; another editor decides.") : undefined}
                  onClick={() => decide(r, "reject")} className="rounded border px-2 py-0.5 disabled:opacity-50">{tx("Reject")}</button>
                {own && <span className="text-gray-500">{tx("You requested this; another editor must approve or reject it.")}</span>}
              </div>}
              {r.status === "APPROVED" && <label className="flex items-center gap-1">
                <input type="radio" name={`approval-${kind}-${targetId}`} checked={picked === r.id} onChange={() => onPick(r.id)} />
                {tx("Send with this approval (the content and recipients must match exactly)")}</label>}
            </li>);
        })}</ul>}
    </div>
  );
}
