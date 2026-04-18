"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  mpsApi, MPSPlanSummary, MPSLine, MPSPlan,
  STATUS_COLOR, FEASIBILITY_COLOR,
} from "@/lib/mps";

function Badge({ label, color }: { label: string; color: string }) {
  return <span className={`px-2 py-0.5 rounded text-xs font-medium ${color}`}>{label}</span>;
}

export default function PlanningBoardPage() {
  const qc = useQueryClient();
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [editLine, setEditLine] = useState<MPSLine | null>(null);
  const [genForm, setGenForm] = useState({ mrp_run_id: "", period_type: "WEEKLY" });
  const [showGenModal, setShowGenModal] = useState(false);
  const [releaseWarehouseId, setReleaseWarehouseId] = useState("");
  const [showReleaseModal, setShowReleaseModal] = useState(false);

  const { data: plans = [] } = useQuery<MPSPlanSummary[]>({
    queryKey: ["mps-plans"],
    queryFn: () => mpsApi.listPlans(),
  });

  const { data: lines = [], isLoading: linesLoading } = useQuery<MPSLine[]>({
    queryKey: ["mps-lines", selectedPlanId],
    queryFn: () => mpsApi.listLines(selectedPlanId!),
    enabled: !!selectedPlanId,
  });

  const selectedPlan = plans.find((p) => p.id === selectedPlanId);

  const runCapacity = useMutation({
    mutationFn: () => mpsApi.runCapacity(selectedPlanId!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mps-lines", selectedPlanId] }),
  });

  const runCampaigns = useMutation({
    mutationFn: () => mpsApi.runCampaigns(selectedPlanId!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mps-lines", selectedPlanId] }),
  });

  const runAI = useMutation({
    mutationFn: () => mpsApi.runAI(selectedPlanId!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mps-plans"] }),
  });

  const approvePlan = useMutation({
    mutationFn: () => mpsApi.approvePlan(selectedPlanId!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mps-plans"] }),
  });

  const generateFromMrp = useMutation({
    mutationFn: () =>
      mpsApi.generateFromMrp(selectedPlanId!, {
        mrp_run_id: genForm.mrp_run_id,
        period_type: genForm.period_type,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mps-lines", selectedPlanId] });
      qc.invalidateQueries({ queryKey: ["mps-plans"] });
      setShowGenModal(false);
    },
  });

  const releasePlan = useMutation({
    mutationFn: () => mpsApi.releasePlan(selectedPlanId!, releaseWarehouseId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mps-plans"] });
      setShowReleaseModal(false);
    },
  });

  const updateLine = useMutation({
    mutationFn: (body: Partial<MPSLine>) =>
      mpsApi.updateLine(selectedPlanId!, editLine!.id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mps-lines", selectedPlanId] });
      setEditLine(null);
    },
  });

  const feasCounts = {
    total: lines.length,
    feasible: lines.filter((l) => l.feasibility_status === "FEASIBLE").length,
    overloaded: lines.filter((l) => l.feasibility_status === "OVERLOADED").length,
    pending: lines.filter((l) => l.feasibility_status === "PENDING").length,
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Production Planning Board</h1>
        <a href="/dashboard/mps" className="text-sm text-blue-600 hover:underline">← MPS Dashboard</a>
      </div>

      {/* Plan selector */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm font-medium text-gray-600">Select Plan:</label>
          <select
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm min-w-64"
            value={selectedPlanId || ""}
            onChange={(e) => setSelectedPlanId(e.target.value || null)}
          >
            <option value="">-- choose a plan --</option>
            {plans.map((p) => (
              <option key={p.id} value={p.id}>
                {p.plan_no} — {p.plan_name} [{p.status}]
              </option>
            ))}
          </select>

          {selectedPlanId && (
            <div className="flex flex-wrap gap-2 ml-auto">
              <button
                onClick={() => setShowGenModal(true)}
                className="px-3 py-1.5 text-xs font-medium bg-gray-100 hover:bg-gray-200 rounded-lg"
              >
                Generate from MRP
              </button>
              <button
                onClick={() => runCapacity.mutate()}
                disabled={runCapacity.isPending}
                className="px-3 py-1.5 text-xs font-medium bg-orange-100 text-orange-700 hover:bg-orange-200 rounded-lg"
              >
                {runCapacity.isPending ? "Running…" : "Run Capacity"}
              </button>
              <button
                onClick={() => runCampaigns.mutate()}
                disabled={runCampaigns.isPending}
                className="px-3 py-1.5 text-xs font-medium bg-purple-100 text-purple-700 hover:bg-purple-200 rounded-lg"
              >
                {runCampaigns.isPending ? "Running…" : "Group Campaigns"}
              </button>
              <button
                onClick={() => runAI.mutate()}
                disabled={runAI.isPending}
                className="px-3 py-1.5 text-xs font-medium bg-indigo-100 text-indigo-700 hover:bg-indigo-200 rounded-lg"
              >
                {runAI.isPending ? "Analyzing…" : "Run AI"}
              </button>
              {selectedPlan?.status === "DRAFT" && (
                <button
                  onClick={() => approvePlan.mutate()}
                  className="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 rounded-lg"
                >
                  Approve Plan
                </button>
              )}
              {selectedPlan?.status === "APPROVED" && (
                <button
                  onClick={() => setShowReleaseModal(true)}
                  className="px-3 py-1.5 text-xs font-medium bg-green-600 text-white hover:bg-green-700 rounded-lg"
                >
                  Release Plan
                </button>
              )}
            </div>
          )}
        </div>

        {/* Feasibility summary bar */}
        {selectedPlanId && lines.length > 0 && (
          <div className="mt-3 flex gap-4 text-xs text-gray-500">
            <span className="text-green-600 font-medium">{feasCounts.feasible} Feasible</span>
            <span className="text-red-600 font-medium">{feasCounts.overloaded} Overloaded</span>
            <span className="text-gray-400">{feasCounts.pending} Pending</span>
            <span className="ml-auto text-gray-400">{feasCounts.total} total lines</span>
          </div>
        )}
      </div>

      {/* Lines Table */}
      {selectedPlanId && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          {linesLoading ? (
            <div className="p-8 text-center text-gray-400 text-sm">Loading lines…</div>
          ) : lines.length === 0 ? (
            <div className="p-8 text-center text-gray-400 text-sm">
              No lines yet. Generate from MRP to populate.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {["Line No", "Product", "Period", "Net Req", "Planned Qty", "Work Center", "Req Hrs", "Start", "End", "Priority", "Status", ""].map((h) => (
                      <th key={h} className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 whitespace-nowrap">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {lines.map((l) => (
                    <tr
                      key={l.id}
                      className={`hover:bg-gray-50 ${l.feasibility_status === "OVERLOADED" ? "bg-red-50/40" : ""}`}
                    >
                      <td className="px-3 py-2 font-mono text-xs text-gray-500">{l.line_no}</td>
                      <td className="px-3 py-2">
                        <div className="font-medium text-gray-800 text-xs truncate max-w-[160px]">
                          {l.product_name || l.product_id.slice(0, 8)}
                        </div>
                        {l.product_code && <div className="text-gray-400 text-xs">{l.product_code}</div>}
                      </td>
                      <td className="px-3 py-2 text-xs text-gray-500 whitespace-nowrap">
                        {l.period_label || `${l.period_start} – ${l.period_end}`}
                      </td>
                      <td className="px-3 py-2 text-xs text-right">{Number(l.net_requirement_qty).toLocaleString()}</td>
                      <td className="px-3 py-2 text-xs font-medium text-right">{Number(l.planned_production_qty).toLocaleString()}</td>
                      <td className="px-3 py-2 text-xs text-gray-500">{l.work_center_name || "—"}</td>
                      <td className="px-3 py-2 text-xs text-right">{l.required_hours ? `${Number(l.required_hours).toFixed(1)}h` : "—"}</td>
                      <td className="px-3 py-2 text-xs whitespace-nowrap">{l.planned_start_date || "—"}</td>
                      <td className="px-3 py-2 text-xs whitespace-nowrap">{l.planned_end_date || "—"}</td>
                      <td className="px-3 py-2 text-xs text-center">{Number(l.priority_score).toFixed(0)}</td>
                      <td className="px-3 py-2">
                        <Badge label={l.feasibility_status} color={FEASIBILITY_COLOR[l.feasibility_status]} />
                      </td>
                      <td className="px-3 py-2">
                        <button
                          onClick={() => setEditLine(l)}
                          className="text-xs text-blue-600 hover:underline"
                        >
                          Edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Generate from MRP Modal */}
      {showGenModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold mb-4">Generate Lines from MRP</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">MRP Run ID *</label>
                <input
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  placeholder="Paste MRP run UUID"
                  value={genForm.mrp_run_id}
                  onChange={(e) => setGenForm({ ...genForm, mrp_run_id: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Period Type</label>
                <select
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  value={genForm.period_type}
                  onChange={(e) => setGenForm({ ...genForm, period_type: e.target.value })}
                >
                  <option value="WEEKLY">Weekly</option>
                  <option value="MONTHLY">Monthly</option>
                  <option value="DAILY">Daily</option>
                </select>
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button
                onClick={() => generateFromMrp.mutate()}
                disabled={!genForm.mrp_run_id || generateFromMrp.isPending}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm font-medium disabled:opacity-40"
              >
                {generateFromMrp.isPending ? "Generating…" : "Generate"}
              </button>
              <button onClick={() => setShowGenModal(false)} className="px-4 border border-gray-200 rounded-lg text-sm">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Release Modal */}
      {showReleaseModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold mb-2">Release Plan</h2>
            <p className="text-sm text-gray-500 mb-4">
              This will create Production Orders for all feasible lines. Enter the target warehouse ID.
            </p>
            <input
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
              placeholder="Target Warehouse UUID"
              value={releaseWarehouseId}
              onChange={(e) => setReleaseWarehouseId(e.target.value)}
            />
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => releasePlan.mutate()}
                disabled={!releaseWarehouseId || releasePlan.isPending}
                className="flex-1 bg-green-600 text-white py-2 rounded-lg text-sm font-medium disabled:opacity-40"
              >
                {releasePlan.isPending ? "Releasing…" : "Release Plan"}
              </button>
              <button onClick={() => setShowReleaseModal(false)} className="px-4 border border-gray-200 rounded-lg text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Line Modal */}
      {editLine && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold mb-1">Override Line</h2>
            <p className="text-xs text-gray-400 mb-4">{editLine.line_no} — {editLine.product_name}</p>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Planned Qty</label>
                <input
                  type="number"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  defaultValue={editLine.planned_production_qty}
                  id="edit-qty"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Priority Score (0–100)</label>
                <input
                  type="number"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  defaultValue={editLine.priority_score}
                  id="edit-priority"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Start Date</label>
                <input
                  type="date"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  defaultValue={editLine.planned_start_date || ""}
                  id="edit-start"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Remarks</label>
                <textarea
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  rows={2}
                  defaultValue={editLine.remarks || ""}
                  id="edit-remarks"
                />
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button
                onClick={() => {
                  const qty = (document.getElementById("edit-qty") as HTMLInputElement).value;
                  const pri = (document.getElementById("edit-priority") as HTMLInputElement).value;
                  const start = (document.getElementById("edit-start") as HTMLInputElement).value;
                  const rem = (document.getElementById("edit-remarks") as HTMLTextAreaElement).value;
                  updateLine.mutate({
                    planned_production_qty: Number(qty),
                    priority_score: Number(pri),
                    planned_start_date: start || undefined,
                    remarks: rem || undefined,
                  } as Partial<MPSLine>);
                }}
                disabled={updateLine.isPending}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm font-medium disabled:opacity-40"
              >
                {updateLine.isPending ? "Saving…" : "Save Override"}
              </button>
              <button onClick={() => setEditLine(null)} className="px-4 border border-gray-200 rounded-lg text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
