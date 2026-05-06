"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  approvalsApi, ApprovalRequest, ApprovalRule, ApprovalModule,
  ApprovalStatus, STATUS_COLOR,
} from "@/lib/approvals";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

const MODULE_LABELS: Record<ApprovalModule, string> = {
  PURCHASE_ORDER:       "Purchase Order",
  PURCHASE_REQUISITION: "Purchase Requisition",
  BUDGET:               "Budget",
  PRODUCTION_ORDER:     "Production Order",
  SALES_INVOICE:        "Sales Invoice",
  EXPENSE:              "Expense",
  CONTRACT:             "Contract",
  PRICE_LIST:           "Price List",
  CREDIT_NOTE:          "Credit Note",
  OTHER:                "Other",
};

function fmtDate(s?: string | null) {
  if (!s) return "—";
  return new Date(s).toLocaleDateString("en-KE", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function fmtAmt(n?: number | null, currency = "KES") {
  if (n == null) return "—";
  return `${currency} ${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function StatusBadge({ status }: { status: ApprovalStatus }) {
  return <span className={`text-xs font-bold px-2 py-0.5 rounded ${STATUS_COLOR[status]}`}>{status}</span>;
}

export default function ApprovalsPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"inbox" | "all" | "rules">("inbox");
  const [selected, setSelected] = useState<ApprovalRequest | null>(null);
  const [rejectModal, setRejectModal] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [newRuleModal, setNewRuleModal] = useState(false);

  const { data: inbox = [], isLoading: inboxLoading } = useQuery({
    queryKey: ["approvals-inbox"],
    queryFn: () => approvalsApi.myPending(),
    enabled: tab === "inbox",
  });

  const { data: allReqs = [], isLoading: allLoading } = useQuery({
    queryKey: ["approvals-all"],
    queryFn: () => approvalsApi.all(),
    enabled: tab === "all",
  });

  const { data: rules = [], isLoading: rulesLoading } = useQuery({
    queryKey: ["approval-rules"],
    queryFn: () => approvalsApi.listRules(),
    enabled: tab === "rules",
  });

  const approve = useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) => approvalsApi.approve(id, notes),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["approvals-inbox"] }); qc.invalidateQueries({ queryKey: ["approvals-all"] }); setSelected(null); },
  });

  const reject = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => approvalsApi.reject(id, reason),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["approvals-inbox"] }); qc.invalidateQueries({ queryKey: ["approvals-all"] }); setRejectModal(null); setRejectReason(""); setSelected(null); },
  });

  const deleteRule = useMutation({
    mutationFn: (id: string) => approvalsApi.deleteRule(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["approval-rules"] }),
  });

  const toggleRule = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => approvalsApi.updateRule(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["approval-rules"] }),
  });

  const displayList = tab === "inbox" ? inbox : allReqs;
  const isLoading = tab === "inbox" ? inboxLoading : allLoading;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Approval Workflow</h1>
        <p className="text-sm text-gray-500 mt-1">Multi-level approval engine for POs, Budgets, Expenses and more</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "My Pending",   value: inbox.filter((r) => r.status === "PENDING").length,   color: "text-amber-700" },
          { label: "Escalated",    value: inbox.filter((r) => r.status === "ESCALATED").length, color: "text-orange-700" },
          { label: "Active Rules", value: rules.filter((r) => r.is_active).length,              color: "text-indigo-700" },
          { label: "Total Inbox",  value: inbox.length,                                          color: "text-gray-700" },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-lg border p-3 text-center">
            <p className="text-xs text-gray-500 mb-1">{k.label}</p>
            <p className={`text-2xl font-bold ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {([
          { key: "inbox", label: `My Inbox${inbox.length ? ` (${inbox.length})` : ""}` },
          { key: "all",   label: "All Requests" },
          { key: "rules", label: "Approval Rules" },
        ] as const).map((t) => (
          <button
            key={t.key}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab === t.key ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* INBOX + ALL tabs */}
      {(tab === "inbox" || tab === "all") && (
        <div className="grid grid-cols-3 gap-6">
          {/* Request list */}
          <div className="col-span-2 bg-white rounded-lg border">
            <div className="px-5 py-3 border-b font-semibold text-gray-800">
              {tab === "inbox" ? "Pending — Requires My Action" : "All Approval Requests"}
            </div>
            {isLoading ? (
              <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                    <th className="px-4 py-2 text-left">Ref</th>
                    <th className="px-4 py-2 text-left">Module</th>
                    <th className="px-4 py-2 text-right">Amount</th>
                    <th className="px-4 py-2 text-center">Level</th>
                    <th className="px-4 py-2 text-left">Status</th>
                    <th className="px-4 py-2 text-left">Submitted</th>
                    <th className="px-4 py-2 text-left">By</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {displayList.map((r) => (
                    <tr
                      key={r.id}
                      className={`hover:bg-gray-50 cursor-pointer ${selected?.id === r.id ? "bg-indigo-50" : ""} ${r.status === "ESCALATED" ? "bg-orange-50" : ""}`}
                      onClick={() => setSelected(r)}
                    >
                      <td className="px-4 py-2.5 font-mono font-semibold text-indigo-700">{r.object_ref}</td>
                      <td className="px-4 py-2.5 text-gray-600 text-xs">{MODULE_LABELS[r.module]}</td>
                      <td className="px-4 py-2.5 text-right text-gray-700">{fmtAmt(r.amount, r.currency)}</td>
                      <td className="px-4 py-2.5 text-center text-gray-500 text-xs">{r.current_level}/{r.max_level}</td>
                      <td className="px-4 py-2.5"><StatusBadge status={r.status} /></td>
                      <td className="px-4 py-2.5 text-gray-400 text-xs">{fmtDate(r.created_at)}</td>
                      <td className="px-4 py-2.5 text-gray-500 text-xs">{r.requested_by_name ?? "—"}</td>
                    </tr>
                  ))}
                  {displayList.length === 0 && (
                    <tr><td colSpan={7} className="px-5 py-8 text-center text-gray-400">
                      {tab === "inbox" ? "Inbox empty — no pending approvals" : "No approval requests"}
                    </td></tr>
                  )}
                </tbody>
              </table>
            )}
          </div>

          {/* Detail panel */}
          <div className="bg-white rounded-lg border p-5 space-y-4">
            {selected ? (
              <>
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-mono font-bold text-indigo-700 text-lg">{selected.object_ref}</p>
                    <p className="text-sm text-gray-500">{MODULE_LABELS[selected.module]}</p>
                  </div>
                  <StatusBadge status={selected.status} />
                </div>

                <div className="space-y-1.5 text-sm">
                  {[
                    ["Amount",    fmtAmt(selected.amount, selected.currency)],
                    ["Level",     `${selected.current_level} of ${selected.max_level}`],
                    ["Submitted", fmtDate(selected.created_at)],
                    ["By",        selected.requested_by_name ?? "—"],
                  ].map(([label, value]) => (
                    <div key={label} className="flex gap-2">
                      <span className="text-gray-400 w-20 shrink-0">{label}</span>
                      <span className="text-gray-700 font-medium">{value}</span>
                    </div>
                  ))}
                  {selected.description && (
                    <p className="text-gray-500 italic text-xs mt-2">{selected.description}</p>
                  )}
                </div>

                {/* Steps timeline */}
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Approval Steps</p>
                  <div className="space-y-2">
                    {selected.steps.map((s) => (
                      <div key={s.id} className={`text-xs border rounded p-2 ${s.level === selected.current_level && s.status === "PENDING" ? "border-amber-300 bg-amber-50" : ""}`}>
                        <div className="flex items-center gap-2 justify-between">
                          <span className="font-medium">Level {s.level}</span>
                          <StatusBadge status={s.status} />
                        </div>
                        <p className="text-gray-500 mt-1">Role: {s.required_role}</p>
                        {s.sla_deadline && <p className="text-gray-400">SLA: {fmtDate(s.sla_deadline)}</p>}
                        {s.action_by_name && <p className="text-gray-600">{s.action_by_name} · {fmtDate(s.action_at)}</p>}
                        {s.rejection_reason && <p className="text-red-600 mt-1">Reason: {s.rejection_reason}</p>}
                        {s.notes && <p className="text-gray-500 italic">{s.notes}</p>}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Actions */}
                {selected.status === "PENDING" || selected.status === "ESCALATED" ? (
                  <div className="flex gap-2 pt-2">
                    <Button
                      onClick={() => approve.mutate({ id: selected.id })}
                      loading={approve.isPending}
                      className="flex-1"
                    >
                      Approve
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => setRejectModal(selected.id)}
                      className="flex-1"
                    >
                      Reject
                    </Button>
                  </div>
                ) : null}
              </>
            ) : (
              <p className="text-center text-gray-400 text-sm py-12">Select a request to view details</p>
            )}
          </div>
        </div>
      )}

      {/* RULES tab */}
      {tab === "rules" && (
        <div className="bg-white rounded-lg border">
          <div className="px-5 py-3 border-b flex items-center justify-between">
            <h2 className="font-semibold text-gray-800">Approval Rules ({rules.length})</h2>
            <Button onClick={() => setNewRuleModal(true)}>+ Add Rule</Button>
          </div>
          {rulesLoading ? (
            <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                  <th className="px-4 py-2 text-left">Module</th>
                  <th className="px-4 py-2 text-center">Level</th>
                  <th className="px-4 py-2 text-left">Required Role</th>
                  <th className="px-4 py-2 text-right">Amount Min</th>
                  <th className="px-4 py-2 text-right">Amount Max</th>
                  <th className="px-4 py-2 text-right">SLA (h)</th>
                  <th className="px-4 py-2 text-center">Active</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {rules.map((r) => (
                  <tr key={r.id} className={`hover:bg-gray-50 ${!r.is_active ? "opacity-50" : ""}`}>
                    <td className="px-4 py-2.5 text-gray-700">{MODULE_LABELS[r.module]}</td>
                    <td className="px-4 py-2.5 text-center font-bold text-indigo-600">{r.level}</td>
                    <td className="px-4 py-2.5 font-mono text-xs text-gray-700">{r.required_role}</td>
                    <td className="px-4 py-2.5 text-right text-gray-600">{fmtAmt(r.amount_min)}</td>
                    <td className="px-4 py-2.5 text-right text-gray-600">{r.amount_max != null ? fmtAmt(r.amount_max) : "No limit"}</td>
                    <td className="px-4 py-2.5 text-right text-gray-600">{r.sla_hours}h</td>
                    <td className="px-4 py-2.5 text-center">
                      <button
                        className={`text-xs px-2 py-0.5 rounded font-medium ${r.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}
                        onClick={() => toggleRule.mutate({ id: r.id, is_active: !r.is_active })}
                      >
                        {r.is_active ? "Active" : "Inactive"}
                      </button>
                    </td>
                    <td className="px-4 py-2.5">
                      <button className="text-xs text-red-500 hover:underline" onClick={() => deleteRule.mutate(r.id)}>Delete</button>
                    </td>
                  </tr>
                ))}
                {rules.length === 0 && (
                  <tr><td colSpan={8} className="px-5 py-8 text-center text-gray-400">No rules — add rules to enable approval routing</td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Reject modal */}
      {rejectModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 space-y-4">
            <h2 className="font-semibold text-lg">Reject Approval</h2>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Reason (required)</label>
              <textarea
                className="w-full border rounded px-3 py-2 text-sm"
                rows={3}
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Explain why this is rejected…"
              />
            </div>
            <div className="flex gap-2 justify-end">
              <Button variant="secondary" onClick={() => { setRejectModal(null); setRejectReason(""); }}>Cancel</Button>
              <Button
                loading={reject.isPending}
                onClick={() => { if (rejectReason.trim()) reject.mutate({ id: rejectModal, reason: rejectReason }); }}
                disabled={!rejectReason.trim()}
              >
                Reject
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* New rule modal */}
      {newRuleModal && (
        <NewRuleModal
          onClose={() => setNewRuleModal(false)}
          onSave={() => { qc.invalidateQueries({ queryKey: ["approval-rules"] }); setNewRuleModal(false); }}
        />
      )}
    </div>
  );
}

function NewRuleModal({ onClose, onSave }: { onClose: () => void; onSave: () => void }) {
  const [form, setForm] = useState({
    module: "PURCHASE_ORDER" as ApprovalModule,
    level: "1",
    required_role: "",
    amount_min: "0",
    amount_max: "",
    sla_hours: "24",
    description: "",
  });
  const [saving, setSaving] = useState(false);
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  async function save() {
    setSaving(true);
    try {
      await approvalsApi.createRule({
        module: form.module,
        level: parseInt(form.level),
        required_role: form.required_role,
        amount_min: parseFloat(form.amount_min) || 0,
        amount_max: form.amount_max ? parseFloat(form.amount_max) : undefined,
        sla_hours: parseInt(form.sla_hours) || 24,
        description: form.description || undefined,
      });
      onSave();
    } finally {
      setSaving(false);
    }
  }

  const MODULES: ApprovalModule[] = [
    "PURCHASE_ORDER","PURCHASE_REQUISITION","BUDGET","PRODUCTION_ORDER",
    "SALES_INVOICE","EXPENSE","CONTRACT","PRICE_LIST","CREDIT_NOTE","OTHER",
  ];

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 space-y-4">
        <h2 className="font-semibold text-lg">New Approval Rule</h2>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Module</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.module} onChange={(e) => set("module", e.target.value)}>
              {MODULES.map((m) => <option key={m} value={m}>{m.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Level</label>
              <input type="number" min="1" max="5" className="w-full border rounded px-3 py-2 text-sm" value={form.level} onChange={(e) => set("level", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">SLA (hours)</label>
              <input type="number" className="w-full border rounded px-3 py-2 text-sm" value={form.sla_hours} onChange={(e) => set("sla_hours", e.target.value)} />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Required Role</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.required_role} onChange={(e) => set("required_role", e.target.value)} placeholder="e.g. finance_manager" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Amount Min (KES)</label>
              <input type="number" className="w-full border rounded px-3 py-2 text-sm" value={form.amount_min} onChange={(e) => set("amount_min", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Amount Max (blank = no limit)</label>
              <input type="number" className="w-full border rounded px-3 py-2 text-sm" value={form.amount_max} onChange={(e) => set("amount_max", e.target.value)} placeholder="Unlimited" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.description} onChange={(e) => set("description", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={saving} onClick={save} disabled={!form.required_role.trim()}>Save Rule</Button>
        </div>
      </div>
    </div>
  );
}
