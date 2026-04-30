"use client";
import { use, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { contractsApi, STATUS_COLORS, PARTY_COLORS, CONTRACT_TYPE_LABELS, SEVERITY_COLORS } from "@/lib/contracts";
import Link from "next/link";

export default function ContractDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const qc = useQueryClient();
  const [tab, setTab] = useState<"terms" | "rebates" | "perf" | "history" | "approvals">("terms");
  const [comments, setComments] = useState("");
  const [termReason, setTermReason] = useState("");
  const [showTerminate, setShowTerminate] = useState(false);
  const [perfForm, setPerfForm] = useState({ period: "", target_value: "", actual_value: "" });

  const { data: c, isLoading } = useQuery({ queryKey: ["contract", id], queryFn: () => contractsApi.get(id) });
  const { data: perf = [] } = useQuery({ queryKey: ["ct-perf", id], queryFn: () => contractsApi.listPerformance(id), enabled: tab === "perf" });
  const { data: history = [] } = useQuery({ queryKey: ["ct-history", id], queryFn: () => contractsApi.history(id), enabled: tab === "history" });
  const { data: approvals = [] } = useQuery({ queryKey: ["ct-approvals", id], queryFn: () => contractsApi.approvals(id), enabled: tab === "approvals" });

  const inv = (fn: () => Promise<any>) => fn().then(() => qc.invalidateQueries({ queryKey: ["contract", id] }));

  const submitMut = useMutation({ mutationFn: () => contractsApi.submit(id, comments), onSuccess: () => { qc.invalidateQueries({ queryKey: ["contract", id] }); setComments(""); } });
  const approveMut = useMutation({ mutationFn: () => contractsApi.approve(id, comments), onSuccess: () => { qc.invalidateQueries({ queryKey: ["contract", id] }); setComments(""); } });
  const rejectMut = useMutation({ mutationFn: () => contractsApi.reject(id, comments), onSuccess: () => { qc.invalidateQueries({ queryKey: ["contract", id] }); setComments(""); } });
  const activateMut = useMutation({ mutationFn: () => contractsApi.activate(id), onSuccess: () => qc.invalidateQueries({ queryKey: ["contract", id] }) });
  const terminateMut = useMutation({ mutationFn: () => contractsApi.terminate(id, termReason), onSuccess: () => { qc.invalidateQueries({ queryKey: ["contract", id] }); setShowTerminate(false); } });
  const perfMut = useMutation({
    mutationFn: () => contractsApi.upsertPerformance(id, { period: perfForm.period, target_value: parseFloat(perfForm.target_value) || undefined, actual_value: parseFloat(perfForm.actual_value) || undefined }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["ct-perf", id] }); setPerfForm({ period: "", target_value: "", actual_value: "" }); },
  });

  if (isLoading || !c) return <div className="p-6 text-slate-500">Loading…</div>;

  const daysLeft = c.end_date ? Math.ceil((new Date(c.end_date).getTime() - Date.now()) / 86400000) : null;

  return (
    <div className="p-6 space-y-6 text-slate-200">
      <div className="flex items-start justify-between">
        <div>
          <Link href="/dashboard/contracts/list" className="text-slate-500 text-sm hover:text-slate-300">← Contracts</Link>
          <div className="flex items-center gap-3 mt-1 flex-wrap">
            <h1 className="text-xl font-bold text-white">{c.contract_code}</h1>
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${PARTY_COLORS[c.party_type]}`}>{c.party_type}</span>
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[c.status]}`}>{c.status}</span>
            <span className="text-xs text-slate-500">v{c.current_version}</span>
          </div>
          <p className="text-slate-400 text-sm mt-0.5">{c.contract_name} · {CONTRACT_TYPE_LABELS[c.contract_type]}</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          {c.status === "DRAFT" && <button onClick={() => submitMut.mutate()} className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium">Submit for Review</button>}
          {c.status === "UNDER_REVIEW" && <>
            <button onClick={() => approveMut.mutate()} className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium">Approve</button>
            <button onClick={() => rejectMut.mutate()} className="px-3 py-1.5 rounded-lg border border-red-500/40 text-red-400 text-xs">Reject</button>
          </>}
          {c.status === "APPROVED" && <button onClick={() => activateMut.mutate()} className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium">Activate</button>}
          {["ACTIVE", "APPROVED"].includes(c.status) && <button onClick={() => setShowTerminate(true)} className="px-3 py-1.5 rounded-lg border border-red-500/40 text-red-400 text-xs">Terminate</button>}
        </div>
      </div>

      {/* Info */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Start Date", value: c.start_date },
          { label: "End Date", value: c.end_date ?? "No end" },
          { label: "Days Left", value: daysLeft !== null ? (daysLeft < 0 ? `${Math.abs(daysLeft)}d expired` : `${daysLeft}d`) : "—", color: daysLeft !== null && daysLeft < 30 ? "text-amber-400" : "text-white" },
          { label: "Currency", value: c.currency },
          { label: "Terms", value: String(c.terms.length) },
          { label: "Rebates", value: String(c.rebates.length) },
          { label: "Auto Renew", value: c.auto_renew ? "Yes" : "No" },
          { label: "Notice Days", value: String(c.renewal_notice_days) },
        ].map((item) => (
          <div key={item.label} className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-3">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5">{item.label}</p>
            <p className={`text-sm font-medium ${(item as any).color ?? "text-white"}`}>{item.value}</p>
          </div>
        ))}
      </div>

      {/* Approval comment input */}
      {["DRAFT", "UNDER_REVIEW"].includes(c.status) && (
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-4">
          <label className="text-xs text-slate-400 mb-1 block">Comments (for approval actions)</label>
          <input value={comments} onChange={(e) => setComments(e.target.value)}
            className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
            placeholder="Optional comments…" />
        </div>
      )}

      {/* Terminate panel */}
      {showTerminate && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 space-y-3">
          <h3 className="text-sm font-semibold text-red-300">Terminate Contract</h3>
          <input value={termReason} onChange={(e) => setTermReason(e.target.value)}
            className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
            placeholder="Reason for termination (required)" />
          <div className="flex gap-2">
            <button onClick={() => terminateMut.mutate()} disabled={!termReason || terminateMut.isPending}
              className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white text-sm disabled:opacity-50">
              {terminateMut.isPending ? "Terminating…" : "Confirm Terminate"}
            </button>
            <button onClick={() => setShowTerminate(false)} className="px-4 py-2 rounded-lg border border-white/[0.08] text-slate-400 text-sm">Cancel</button>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-white/[0.07]">
        {(["terms", "rebates", "perf", "history", "approvals"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === t ? "border-indigo-500 text-indigo-300" : "border-transparent text-slate-500 hover:text-slate-300"}`}>
            {t === "terms" ? "Terms" : t === "rebates" ? "Rebates" : t === "perf" ? "Performance" : t === "history" ? "Versions" : "Approval Log"}
          </button>
        ))}
      </div>

      {tab === "terms" && (
        <div className="rounded-xl border border-white/[0.07] overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-white/[0.03] text-slate-500 text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3 text-left">Type</th>
                <th className="px-4 py-3 text-left">Value Type</th>
                <th className="px-4 py-3 text-right">Value</th>
                <th className="px-4 py-3 text-right">Min</th>
                <th className="px-4 py-3 text-right">Max</th>
                <th className="px-4 py-3 text-left">Valid</th>
                <th className="px-4 py-3 text-left">Active</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {c.terms.map((t) => (
                <tr key={t.id} className="hover:bg-white/[0.02]">
                  <td className="px-4 py-3 text-slate-300 text-xs">{t.term_type.replace(/_/g, " ")}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{t.value_type}</td>
                  <td className="px-4 py-3 text-right text-white font-medium">{t.value}</td>
                  <td className="px-4 py-3 text-right text-slate-400">{t.min_threshold ?? "—"}</td>
                  <td className="px-4 py-3 text-right text-slate-400">{t.max_threshold ?? "—"}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{t.valid_from ?? "—"} → {t.valid_to ?? "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${t.active_flag ? "bg-emerald-500/20 text-emerald-300" : "bg-slate-500/20 text-slate-400"}`}>
                      {t.active_flag ? "Active" : "Inactive"}
                    </span>
                  </td>
                </tr>
              ))}
              {c.terms.length === 0 && <tr><td colSpan={7} className="text-center py-6 text-slate-600">No terms defined</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === "rebates" && (
        <div className="rounded-xl border border-white/[0.07] overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-white/[0.03] text-slate-500 text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3 text-left">Name</th>
                <th className="px-4 py-3 text-left">Type</th>
                <th className="px-4 py-3 text-right">Threshold</th>
                <th className="px-4 py-3 text-right">Rate %</th>
                <th className="px-4 py-3 text-right">Accrued</th>
                <th className="px-4 py-3 text-right">Settled</th>
                <th className="px-4 py-3 text-left">Frequency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {c.rebates.map((r) => (
                <tr key={r.id} className="hover:bg-white/[0.02]">
                  <td className="px-4 py-3 text-white">{r.rebate_name ?? "—"}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{r.rebate_type}</td>
                  <td className="px-4 py-3 text-right text-slate-400">{r.threshold ?? "—"}</td>
                  <td className="px-4 py-3 text-right text-emerald-400">{r.rebate_pct ? `${r.rebate_pct}%` : "—"}</td>
                  <td className="px-4 py-3 text-right text-white font-medium">KES {Number(r.accrued_amount).toLocaleString()}</td>
                  <td className="px-4 py-3 text-right text-blue-400">KES {Number(r.settled_amount).toLocaleString()}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{r.settlement_frequency}</td>
                </tr>
              ))}
              {c.rebates.length === 0 && <tr><td colSpan={7} className="text-center py-6 text-slate-600">No rebates defined</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === "perf" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-4">
            <h3 className="text-xs font-semibold text-white mb-3">Log Performance</h3>
            <div className="grid grid-cols-3 gap-3">
              {[
                { k: "period", label: "Period (YYYY-MM)", placeholder: "2026-04" },
                { k: "target_value", label: "Target", placeholder: "500000" },
                { k: "actual_value", label: "Actual", placeholder: "420000" },
              ].map(({ k, label, placeholder }) => (
                <div key={k}>
                  <label className="text-[10px] text-slate-400 mb-1 block">{label}</label>
                  <input value={(perfForm as any)[k]} onChange={(e) => setPerfForm((f) => ({ ...f, [k]: e.target.value }))}
                    placeholder={placeholder}
                    className="w-full bg-white/[0.04] border border-white/[0.08] rounded px-2 py-1.5 text-xs text-white focus:outline-none" />
                </div>
              ))}
            </div>
            <button onClick={() => perfMut.mutate()} disabled={!perfForm.period || perfMut.isPending}
              className="mt-3 px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium disabled:opacity-50">
              {perfMut.isPending ? "Saving…" : "Save"}
            </button>
          </div>

          <div className="rounded-xl border border-white/[0.07] overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-white/[0.03] text-slate-500 text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 text-left">Period</th>
                  <th className="px-4 py-3 text-right">Target</th>
                  <th className="px-4 py-3 text-right">Actual</th>
                  <th className="px-4 py-3 text-right">Achievement %</th>
                  <th className="px-4 py-3 text-right">Rebate Earned</th>
                  <th className="px-4 py-3 text-left">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {perf.map((p) => (
                  <tr key={p.id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3 text-slate-300 font-mono text-xs">{p.period}</td>
                    <td className="px-4 py-3 text-right text-slate-400">{Number(p.target_value ?? 0).toLocaleString()}</td>
                    <td className="px-4 py-3 text-right text-white font-medium">{Number(p.actual_value ?? 0).toLocaleString()}</td>
                    <td className="px-4 py-3 text-right">
                      <span className={`font-medium ${Number(p.achievement_pct ?? 0) >= 100 ? "text-emerald-400" : Number(p.achievement_pct ?? 0) >= 60 ? "text-amber-400" : "text-red-400"}`}>
                        {Number(p.achievement_pct ?? 0).toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-emerald-400">KES {Number(p.rebate_earned ?? 0).toLocaleString()}</td>
                    <td className="px-4 py-3 text-xs text-slate-400">{p.status}</td>
                  </tr>
                ))}
                {perf.length === 0 && <tr><td colSpan={6} className="text-center py-6 text-slate-600">No performance data</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "history" && (
        <div className="space-y-2">
          {history.map((v) => (
            <div key={v.id} className="p-4 rounded-xl border border-white/[0.07] bg-[#0d1829]">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-semibold text-white">Version {v.version_no}</span>
                <span className="text-xs text-slate-500">{new Date(v.created_at).toLocaleDateString()}</span>
              </div>
              <p className="text-xs text-slate-400">{v.change_summary ?? "No summary"}</p>
              {v.effective_date && <p className="text-xs text-slate-600 mt-1">Effective: {v.effective_date}</p>}
            </div>
          ))}
          {history.length === 0 && <p className="text-slate-600 text-sm text-center py-6">No version history</p>}
        </div>
      )}

      {tab === "approvals" && (
        <div className="space-y-2">
          {approvals.map((a) => (
            <div key={a.id} className="flex items-start gap-3 p-3 rounded-xl border border-white/[0.07] bg-[#0d1829]">
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium shrink-0 mt-0.5 ${
                a.action === "APPROVED" ? "bg-emerald-500/20 text-emerald-300"
                : a.action === "REJECTED" ? "bg-red-500/20 text-red-300"
                : "bg-slate-500/20 text-slate-400"
              }`}>{a.action}</span>
              <div>
                <p className="text-xs text-slate-400">{a.comments ?? "No comments"}</p>
                <p className="text-[10px] text-slate-600 mt-0.5">{new Date(a.created_at).toLocaleString()}</p>
              </div>
            </div>
          ))}
          {approvals.length === 0 && <p className="text-slate-600 text-sm text-center py-6">No approval history</p>}
        </div>
      )}
    </div>
  );
}
