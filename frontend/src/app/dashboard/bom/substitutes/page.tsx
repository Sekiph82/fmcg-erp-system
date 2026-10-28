"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { bomApi, SubstGroupOut, SubstituteOut, SubstitutionPolicy, SubstitutionRequestOut } from "@/lib/bom";
import { PermissionGuard, RequirePermission } from "@/components/PermissionGuard";

const POLICIES: SubstitutionPolicy[] = ["NO_SUB", "PLANNER_APPROVAL", "QA_APPROVAL", "BOTH_REQUIRED", "SHORTAGE_ONLY", "EMERGENCY_ONLY"];

const POLICY_COLOR: Record<SubstitutionPolicy, string> = {
  NO_SUB:            "bg-gray-100 text-gray-500",
  PLANNER_APPROVAL:  "bg-blue-100 text-blue-700",
  QA_APPROVAL:       "bg-yellow-100 text-yellow-700",
  BOTH_REQUIRED:     "bg-orange-100 text-orange-700",
  SHORTAGE_ONLY:     "bg-purple-100 text-purple-700",
  EMERGENCY_ONLY:    "bg-red-100 text-red-700",
};

export default function SubstituteManagerPage() {
  const qc = useQueryClient();
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);
  const [showCreateGroup, setShowCreateGroup] = useState(false);
  const [showAddSub, setShowAddSub] = useState(false);
  const [showRequest, setShowRequest] = useState(false);
  const [requestSubstituteId, setRequestSubstituteId] = useState("");
  const [decisionReasons, setDecisionReasons] = useState<Record<string, string>>({});
  const [requestForm, setRequestForm] = useState({
    bom_id: "", bom_line_id: "", target_qty: "", context_reference: "", reason: "", shortage_evidence_reference: "",
  });
  const [groupForm, setGroupForm] = useState({ group_name: "", policy: "PLANNER_APPROVAL" as SubstitutionPolicy, notes: "" });
  const [subForm, setSubForm] = useState<Partial<SubstituteOut & { group_id: string }>>({
    item_type: "MATERIAL", priority: 1, qty_ratio: 1, is_active: true,
  });

  const { data: groups = [] } = useQuery<SubstGroupOut[]>({
    queryKey: ["bom-subst-groups"],
    queryFn: () => bomApi.listGroups(),
  });
  const { data: requests = [] } = useQuery<SubstitutionRequestOut[]>({
    queryKey: ["bom-substitution-requests"],
    queryFn: () => bomApi.substitutionRequests(),
  });
  const { data: groupLines = [] } = useQuery({
    queryKey: ["bom-subst-lines", selectedGroupId],
    queryFn: () => bomApi.substitutionLines(selectedGroupId!),
    enabled: !!selectedGroupId && showRequest,
  });

  const createGroup = useMutation({
    mutationFn: () => bomApi.createGroup(groupForm),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bom-subst-groups"] });
      setShowCreateGroup(false);
      setGroupForm({ group_name: "", policy: "PLANNER_APPROVAL", notes: "" });
    },
  });

  const addSubstitute = useMutation({
    mutationFn: () => bomApi.addSubstitute({ ...subForm, group_id: selectedGroupId! }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bom-subst-groups"] });
      setShowAddSub(false);
      setSubForm({ item_type: "MATERIAL", priority: 1, qty_ratio: 1, is_active: true });
    },
  });

  const createRequest = useMutation({
    mutationFn: () => bomApi.createSubstitutionRequest({
      ...requestForm,
      bom_id: requestForm.bom_id,
      bom_line_id: requestForm.bom_line_id,
      substitute_id: requestSubstituteId,
      target_qty: Number(requestForm.target_qty),
      shortage_evidence_reference: requestForm.shortage_evidence_reference || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bom-substitution-requests"] });
      setShowRequest(false);
    },
  });

  const decide = useMutation({
    mutationFn: ({ id, role, decision, reason }: { id: string; role: "planner" | "quality"; decision: "APPROVED" | "REJECTED"; reason: string }) =>
      bomApi.decideSubstitution(id, role, { decision, reason }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bom-substitution-requests"] }),
  });

  const selectedGroup = groups.find((g) => g.id === selectedGroupId);

  return (
    <RequirePermission permission="bom.view">
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a href="/dashboard/bom" className="text-sm text-gray-400 hover:text-gray-600">← BOMs</a>
          <h1 className="text-xl font-bold text-gray-900">Substitute Material Manager</h1>
        </div>
        <PermissionGuard permission="bom.create">
          <button onClick={() => setShowCreateGroup(true)} className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700">
            + New Group
          </button>
        </PermissionGuard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Group List */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Substitute Groups</p>
          {groups.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 text-center text-sm text-gray-400">No groups yet.</div>
          ) : groups.map((g) => (
            <div
              key={g.id}
              onClick={() => setSelectedGroupId(g.id)}
              className={`bg-white rounded-xl border shadow-sm p-3 cursor-pointer hover:border-indigo-300 transition-colors ${selectedGroupId === g.id ? "border-indigo-500" : "border-gray-100"}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-medium text-sm text-gray-800">{g.group_name}</p>
                  <p className="text-xs text-gray-400 font-mono">{g.group_code}</p>
                </div>
                <span className={`text-xs px-1.5 py-0.5 rounded shrink-0 ${POLICY_COLOR[g.policy]}`}>{g.policy.replace(/_/g, " ")}</span>
              </div>
              <p className="text-xs text-gray-400 mt-1">{g.substitutes?.length ?? 0} substitutes</p>
              {!g.is_active && <span className="text-xs text-gray-400">Inactive</span>}
            </div>
          ))}
        </div>

        {/* Substitute List */}
        <div className="lg:col-span-2">
          {!selectedGroup ? (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center text-sm text-gray-400">
              Select a substitute group to view its members.
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-800">{selectedGroup.group_name}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`text-xs px-2 py-0.5 rounded ${POLICY_COLOR[selectedGroup.policy]}`}>{selectedGroup.policy}</span>
                    {selectedGroup.notes && <span className="text-xs text-gray-400">{selectedGroup.notes}</span>}
                  </div>
                </div>
                <div className="flex gap-2">
                  <PermissionGuard permission="bom.edit">
                    <button onClick={() => { setRequestSubstituteId(selectedGroup.substitutes.find((s) => s.is_active)?.id ?? ""); setShowRequest(true); }} disabled={!selectedGroup.substitutes.some((s) => s.is_active)} className="px-3 py-1.5 text-xs bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-40">
                      Request Substitution
                    </button>
                  </PermissionGuard>
                  <PermissionGuard permission="bom.create">
                    <button onClick={() => setShowAddSub(true)} className="px-3 py-1.5 text-xs bg-teal-600 text-white rounded-lg hover:bg-teal-700">
                      + Add Substitute
                    </button>
                  </PermissionGuard>
                </div>
              </div>

              {selectedGroup.policy === "EMERGENCY_ONLY" && (
                <p className="rounded-lg bg-red-50 border border-red-100 p-3 text-xs text-red-800">
                  Emergency use is only for cases where the primary material cannot meet the scheduled quantity/date and routine procurement cannot meet the schedule. A traceable shortage evidence reference and written reason are mandatory, followed by separate planner and quality approvals. The evidence and order reference are reviewed by approvers; this workflow does not verify them against stock/order records automatically.
                </p>
              )}

              {selectedGroup.substitutes.length === 0 ? (
                <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 text-center text-sm text-gray-400">
                  No substitutes in this group yet.
                </div>
              ) : (
                <div className="space-y-2">
                  {[...selectedGroup.substitutes].sort((a, b) => a.priority - b.priority).map((sub) => (
                    <div key={sub.id} className={`bg-white rounded-xl border shadow-sm p-4 ${!sub.is_active ? "opacity-60" : "border-gray-100"}`}>
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-center gap-3">
                          <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold flex items-center justify-center">
                            {sub.priority}
                          </div>
                          <div>
                            <p className="font-medium text-gray-800">{sub.item_name || sub.item_code || "Unknown"}</p>
                            <div className="flex items-center gap-2 mt-0.5 text-xs text-gray-400">
                              <span>{sub.item_type}</span>
                              <span>·</span>
                              <span>Ratio: ×{sub.qty_ratio}</span>
                              {sub.cost_impact_pct && <span className={`${Number(sub.cost_impact_pct) > 0 ? "text-red-500" : "text-green-500"}`}>Cost: {Number(sub.cost_impact_pct) > 0 ? "+" : ""}{sub.cost_impact_pct}%</span>}
                            </div>
                          </div>
                        </div>
                        {!sub.is_active && <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded">Inactive</span>}
                      </div>
                      {(sub.quality_impact || sub.allergen_impact) && (
                        <div className="mt-2 flex gap-3 text-xs">
                          {sub.quality_impact && <span className="text-blue-600">Quality: {sub.quality_impact}</span>}
                          {sub.allergen_impact && <span className="text-red-600">Allergen: {sub.allergen_impact}</span>}
                        </div>
                      )}
                      {sub.notes && <p className="mt-1 text-xs text-gray-400">{sub.notes}</p>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-800">Substitution Approval Queue</h2>
          <span className="text-xs text-gray-500">Pending requests remain unavailable to BOM explosion.</span>
        </div>
        {requests.length === 0 ? (
          <div className="rounded-xl border border-gray-100 bg-white p-5 text-sm text-gray-400">No substitution requests yet.</div>
        ) : requests.map((request: SubstitutionRequestOut) => (
          <article key={request.id} className="rounded-xl border border-gray-100 bg-white p-4 space-y-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="font-medium text-sm text-gray-800">{request.substitute?.item_name || request.substitute?.item_code || request.substitute_id}</p>
                <p className="font-mono text-[10px] text-gray-400">Request: {request.id}</p>
                <p className="text-xs text-gray-500">{request.policy.replace(/_/g, " ")} · {request.context_reference} · {request.substitute_qty} for target {request.target_qty}</p>
                <p className="mt-1 text-xs text-gray-500">Requested by {request.requester_name}: {request.reason}</p>
                {request.shortage_evidence_reference && <p className="text-xs text-amber-700">Shortage evidence: {request.shortage_evidence_reference}</p>}
              </div>
              <span className={`rounded px-2 py-1 text-xs ${request.status === "APPROVED" ? "bg-green-100 text-green-700" : request.status === "REJECTED" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-800"}`}>{request.status}</span>
            </div>
            {request.decisions.map((decision) => (
              <p key={decision.id} className="text-xs text-gray-600">{decision.approver_role}: {decision.decision} by {decision.actor_name} — {decision.reason}</p>
            ))}
            {request.status === "PENDING" && (
              <div className="flex flex-wrap items-center gap-2 border-t pt-3">
                <input className="min-w-56 flex-1 rounded border px-2 py-1.5 text-xs" placeholder="Decision reason (required)" value={decisionReasons[request.id] ?? ""} onChange={(e) => setDecisionReasons({ ...decisionReasons, [request.id]: e.target.value })} />
                {!request.decisions.some((decision) => decision.approver_role === "PLANNER") && ["PLANNER_APPROVAL", "BOTH_REQUIRED", "SHORTAGE_ONLY", "EMERGENCY_ONLY"].includes(request.policy) && (
                  <PermissionGuard permission="bom.approve">
                    <button onClick={() => decide.mutate({ id: request.id, role: "planner", decision: "APPROVED", reason: decisionReasons[request.id] ?? "" })} disabled={(decisionReasons[request.id] ?? "").trim().length < 5 || decide.isPending} className="rounded bg-blue-600 px-3 py-1.5 text-xs text-white disabled:opacity-40">Planner approve</button>
                    <button onClick={() => decide.mutate({ id: request.id, role: "planner", decision: "REJECTED", reason: decisionReasons[request.id] ?? "" })} disabled={(decisionReasons[request.id] ?? "").trim().length < 5 || decide.isPending} className="rounded border border-red-200 px-3 py-1.5 text-xs text-red-700 disabled:opacity-40">Planner reject</button>
                  </PermissionGuard>
                )}
                {!request.decisions.some((decision) => decision.approver_role === "QUALITY") && ["QA_APPROVAL", "BOTH_REQUIRED", "EMERGENCY_ONLY"].includes(request.policy) && (
                  <PermissionGuard permission="quality.approve">
                    <button onClick={() => decide.mutate({ id: request.id, role: "quality", decision: "APPROVED", reason: decisionReasons[request.id] ?? "" })} disabled={(decisionReasons[request.id] ?? "").trim().length < 5 || decide.isPending} className="rounded bg-purple-600 px-3 py-1.5 text-xs text-white disabled:opacity-40">Quality approve</button>
                    <button onClick={() => decide.mutate({ id: request.id, role: "quality", decision: "REJECTED", reason: decisionReasons[request.id] ?? "" })} disabled={(decisionReasons[request.id] ?? "").trim().length < 5 || decide.isPending} className="rounded border border-red-200 px-3 py-1.5 text-xs text-red-700 disabled:opacity-40">Quality reject</button>
                  </PermissionGuard>
                )}
              </div>
            )}
          </article>
        ))}
      </section>

      {/* Create Group Modal */}
      {showCreateGroup && (
        <PermissionGuard permission="bom.create">
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">New Substitute Group</h2>
              <button onClick={() => setShowCreateGroup(false)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="space-y-3">
              <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Group Name *" value={groupForm.group_name} onChange={(e) => setGroupForm({ ...groupForm, group_name: e.target.value })} />
              <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={groupForm.policy} onChange={(e) => setGroupForm({ ...groupForm, policy: e.target.value as SubstitutionPolicy })}>
                {POLICIES.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
              <textarea className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" rows={2} placeholder="Notes (optional)" value={groupForm.notes} onChange={(e) => setGroupForm({ ...groupForm, notes: e.target.value })} />
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={() => createGroup.mutate()} disabled={!groupForm.group_name || createGroup.isPending} className="flex-1 bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-40">
                {createGroup.isPending ? "Creating…" : "Create Group"}
              </button>
              <button onClick={() => setShowCreateGroup(false)} className="px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
        </PermissionGuard>
      )}

      {/* Add Substitute Modal */}
      {showAddSub && selectedGroup && (
        <PermissionGuard permission="bom.create">
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Add Substitute</h2>
              <button onClick={() => setShowAddSub(false)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <p className="text-sm text-gray-500 mb-3">Group: <strong>{selectedGroup.group_name}</strong></p>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Item Type</label>
                  <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={subForm.item_type} onChange={(e) => setSubForm({ ...subForm, item_type: e.target.value as any })}>
                    <option value="MATERIAL">Material</option>
                    <option value="PRODUCT">Product</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Priority</label>
                  <input type="number" min={1} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={subForm.priority} onChange={(e) => setSubForm({ ...subForm, priority: Number(e.target.value) })} />
                </div>
              </div>
              <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Item Name" value={subForm.item_name ?? ""} onChange={(e) => setSubForm({ ...subForm, item_name: e.target.value })} />
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Qty Ratio (substitute/original)</label>
                  <input type="number" step="0.01" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={subForm.qty_ratio} onChange={(e) => setSubForm({ ...subForm, qty_ratio: Number(e.target.value) })} />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Cost Impact %</label>
                  <input type="number" step="0.1" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="e.g. 5.0 or -3.0" value={subForm.cost_impact_pct ?? ""} onChange={(e) => setSubForm({ ...subForm, cost_impact_pct: e.target.value ? Number(e.target.value) : undefined })} />
                </div>
              </div>
              <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Quality impact (optional)" value={subForm.quality_impact ?? ""} onChange={(e) => setSubForm({ ...subForm, quality_impact: e.target.value })} />
              <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Allergen impact (optional)" value={subForm.allergen_impact ?? ""} onChange={(e) => setSubForm({ ...subForm, allergen_impact: e.target.value })} />
              <textarea className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" rows={2} placeholder="Notes" value={subForm.notes ?? ""} onChange={(e) => setSubForm({ ...subForm, notes: e.target.value })} />
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={() => addSubstitute.mutate()} disabled={!subForm.item_name || addSubstitute.isPending} className="flex-1 bg-teal-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-teal-700 disabled:opacity-40">
                {addSubstitute.isPending ? "Adding…" : "Add Substitute"}
              </button>
              <button onClick={() => setShowAddSub(false)} className="px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
        </PermissionGuard>
      )}

      {showRequest && selectedGroup && (
        <PermissionGuard permission="bom.edit">
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
            <div className="w-full max-w-xl space-y-3 rounded-2xl bg-white p-6 shadow-xl">
              <div className="flex items-center justify-between"><h2 className="text-lg font-semibold">Request Substitute Use</h2><button onClick={() => setShowRequest(false)} className="text-xl text-gray-400">×</button></div>
              <p className="text-xs text-gray-500">Policy: {selectedGroup.policy}. The request remains blocked from BOM explosion until all required approvals are recorded.</p>
              <select className="w-full rounded border px-3 py-2 text-sm" value={requestForm.bom_line_id} onChange={(e) => {
                const selectedLine = groupLines.find((line) => line.id === e.target.value);
                setRequestForm({ ...requestForm, bom_id: selectedLine?.bom_id ?? "", bom_line_id: e.target.value });
              }}>
                <option value="">Select BOM line *</option>
                {groupLines.map((line) => <option key={line.id} value={line.id}>{line.bom_code} · line {line.line_no} · {line.item_name || line.item_code} ({line.required_qty} {line.required_uom})</option>)}
              </select>
              <select className="w-full rounded border px-3 py-2 text-sm" value={requestSubstituteId} onChange={(e) => setRequestSubstituteId(e.target.value)}>
                <option value="">Select substitute *</option>
                {selectedGroup.substitutes.filter((s) => s.is_active).map((s) => <option key={s.id} value={s.id}>{s.item_name || s.item_code}</option>)}
              </select>
              <input type="number" min="0.0001" step="0.0001" className="w-full rounded border px-3 py-2 text-sm" placeholder="BOM target quantity *" value={requestForm.target_qty} onChange={(e) => setRequestForm({ ...requestForm, target_qty: e.target.value })} />
              <p className="text-xs text-gray-500">The system calculates substitute quantity from the BOM line basis, loss factors, and approved substitute ratio.</p>
              <input className="w-full rounded border px-3 py-2 text-sm" placeholder="Production/order trace reference (approvers verify it) *" value={requestForm.context_reference} onChange={(e) => setRequestForm({ ...requestForm, context_reference: e.target.value })} />
              <textarea className="w-full rounded border px-3 py-2 text-sm" rows={3} placeholder={selectedGroup.policy === "EMERGENCY_ONLY" ? "Why primary material cannot meet the scheduled quantity/date and routine procurement cannot meet schedule *" : "Reason for this substitution *"} value={requestForm.reason} onChange={(e) => setRequestForm({ ...requestForm, reason: e.target.value })} />
              {(selectedGroup.policy === "SHORTAGE_ONLY" || selectedGroup.policy === "EMERGENCY_ONLY") && <input className="w-full rounded border px-3 py-2 text-sm" placeholder="Traceable shortage evidence reference *" value={requestForm.shortage_evidence_reference} onChange={(e) => setRequestForm({ ...requestForm, shortage_evidence_reference: e.target.value })} />}
              <div className="flex gap-2"><button onClick={() => createRequest.mutate()} disabled={!requestForm.bom_id || !requestForm.bom_line_id || !requestSubstituteId || Number(requestForm.target_qty) <= 0 || requestForm.context_reference.trim().length < 1 || requestForm.reason.trim().length < 5 || (["SHORTAGE_ONLY", "EMERGENCY_ONLY"].includes(selectedGroup.policy) && !requestForm.shortage_evidence_reference.trim()) || createRequest.isPending} className="flex-1 rounded bg-amber-600 py-2 text-sm font-medium text-white disabled:opacity-40">{createRequest.isPending ? "Submitting…" : "Submit for approval"}</button><button onClick={() => setShowRequest(false)} className="rounded border px-4 text-sm">Cancel</button></div>
              {createRequest.isError && <p className="text-xs text-red-700">Request could not be submitted; check permissions and required policy evidence.</p>}
            </div>
          </div>
        </PermissionGuard>
      )}
    </div>
    </RequirePermission>
  );
}
