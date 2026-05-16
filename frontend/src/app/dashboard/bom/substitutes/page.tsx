"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { bomApi, SubstGroupOut, SubstituteOut, SubstitutionPolicy } from "@/lib/bom";
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
  const [groupForm, setGroupForm] = useState({ group_name: "", policy: "PLANNER_APPROVAL" as SubstitutionPolicy, notes: "" });
  const [subForm, setSubForm] = useState<Partial<SubstituteOut & { group_id: string }>>({
    item_type: "MATERIAL", priority: 1, qty_ratio: 1, is_active: true,
  });

  const { data: groups = [] } = useQuery<SubstGroupOut[]>({
    queryKey: ["bom-subst-groups"],
    queryFn: () => bomApi.listGroups(),
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
                <PermissionGuard permission="bom.create">
                  <button onClick={() => setShowAddSub(true)} className="px-3 py-1.5 text-xs bg-teal-600 text-white rounded-lg hover:bg-teal-700">
                    + Add Substitute
                  </button>
                </PermissionGuard>
              </div>

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
    </div>
    </RequirePermission>
  );
}
