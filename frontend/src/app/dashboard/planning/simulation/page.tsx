"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  planningApi, ScenarioSummary, OpQueueOut, SimulationOut, fmtMins,
} from "@/lib/planning";

type Change = { op_id: string; field: string; new_value: string | number };

const FIELD_OPTIONS = [
  { value: "delay_days",    label: "Delay (days)", numeric: true },
  { value: "planned_qty",   label: "Planned Qty",  numeric: true },
  { value: "total_minutes", label: "Duration (min)", numeric: true },
  { value: "work_center_id", label: "Work Center ID", numeric: false },
];

export default function SimulationPage() {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [simName, setSimName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedOpIds, setSelectedOpIds] = useState<Set<string>>(new Set());
  const [field, setField] = useState("delay_days");
  const [fieldValue, setFieldValue] = useState("");
  const [changes, setChanges] = useState<Change[]>([]);
  const [viewSim, setViewSim] = useState<SimulationOut | null>(null);

  const { data: scenarios = [] } = useQuery<ScenarioSummary[]>({
    queryKey: ["planning-scenarios"],
    queryFn: () => planningApi.listScenarios(),
  });

  const { data: ops = [] } = useQuery<OpQueueOut[]>({
    queryKey: ["planning-ops", selectedId],
    queryFn: () => planningApi.listOps(selectedId!),
    enabled: !!selectedId,
  });

  const { data: sims = [] } = useQuery<SimulationOut[]>({
    queryKey: ["planning-sims", selectedId],
    queryFn: () => planningApi.listSims(selectedId!),
    enabled: !!selectedId,
  });

  const createSim = useMutation({
    mutationFn: () => planningApi.createSim(selectedId!, { sim_name: simName, description, changes: changes as any }),
    onSuccess: (sim) => {
      qc.invalidateQueries({ queryKey: ["planning-sims", selectedId] });
      setChanges([]);
      setSimName("");
      setDescription("");
      setSelectedOpIds(new Set());
      // auto-compute
      computeSim.mutate(sim.id);
    },
  });

  const computeSim = useMutation({
    mutationFn: (simId: string) => planningApi.computeSim(simId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["planning-sims", selectedId] }),
  });

  const publishSim = useMutation({
    mutationFn: (simId: string) => planningApi.publishSim(simId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["planning-sims", selectedId] }),
  });

  function addChange() {
    if (!fieldValue || selectedOpIds.size === 0) return;
    const fieldDef = FIELD_OPTIONS.find((f) => f.value === field);
    const newChanges: Change[] = Array.from(selectedOpIds).map((opId) => ({
      op_id: opId,
      field,
      new_value: fieldDef?.numeric ? Number(fieldValue) : fieldValue,
    }));
    setChanges((prev) => [...prev, ...newChanges]);
    setSelectedOpIds(new Set());
    setFieldValue("");
  }

  function toggleOp(id: string) {
    setSelectedOpIds((prev) => {
      const n = new Set(prev);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
  }

  const impactColor = (v: number | null, inverted = false) => {
    if (v == null) return "text-gray-400";
    const positive = inverted ? v < 0 : v > 0;
    return positive ? "text-green-600" : "text-red-600";
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Simulation Sandbox</h1>
        <a href="/dashboard/planning" className="text-xs text-blue-600 hover:underline">← Planning Dashboard</a>
      </div>

      {/* Scenario selector */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
        <select
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm min-w-64"
          value={selectedId || ""}
          onChange={(e) => setSelectedId(e.target.value || null)}
        >
          <option value="">-- select scenario --</option>
          {scenarios.map((s) => (
            <option key={s.id} value={s.id}>{s.scenario_no} — {s.scenario_name}</option>
          ))}
        </select>
      </div>

      {selectedId && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Builder */}
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
              <h2 className="text-sm font-semibold text-gray-700 mb-3">Build Simulation</h2>
              <div className="space-y-3">
                <input
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  placeholder="Simulation name *"
                  value={simName}
                  onChange={(e) => setSimName(e.target.value)}
                />
                <textarea
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  rows={2}
                  placeholder="Description (optional)"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>

              {/* Change builder */}
              <div className="mt-4 bg-gray-50 rounded-lg p-3 space-y-3">
                <p className="text-xs font-medium text-gray-600">Add Change</p>
                <div className="grid grid-cols-2 gap-2">
                  <select
                    className="border border-gray-200 rounded px-2 py-1.5 text-xs"
                    value={field}
                    onChange={(e) => setField(e.target.value)}
                  >
                    {FIELD_OPTIONS.map((f) => (
                      <option key={f.value} value={f.value}>{f.label}</option>
                    ))}
                  </select>
                  <input
                    className="border border-gray-200 rounded px-2 py-1.5 text-xs"
                    placeholder="New value"
                    value={fieldValue}
                    onChange={(e) => setFieldValue(e.target.value)}
                  />
                </div>
                <p className="text-xs text-gray-400">{selectedOpIds.size} operation(s) selected below</p>
                <button
                  onClick={addChange}
                  disabled={!fieldValue || selectedOpIds.size === 0}
                  className="w-full py-1.5 text-xs bg-indigo-600 text-white rounded-lg disabled:opacity-40 hover:bg-indigo-700"
                >
                  Stage Change
                </button>
              </div>

              {/* Staged changes */}
              {changes.length > 0 && (
                <div className="mt-3 space-y-1">
                  <p className="text-xs font-medium text-gray-500">{changes.length} change(s) staged:</p>
                  {changes.map((c, i) => (
                    <div key={i} className="flex items-center justify-between text-xs bg-blue-50 rounded px-2 py-1">
                      <span className="text-blue-700 font-mono">{c.op_id.slice(0, 8)}…</span>
                      <span className="text-indigo-600">{c.field}: {String(c.new_value)}</span>
                      <button
                        onClick={() => setChanges((prev) => prev.filter((_, j) => j !== i))}
                        className="text-gray-400 hover:text-red-500"
                      >×</button>
                    </div>
                  ))}
                </div>
              )}

              <button
                onClick={() => createSim.mutate()}
                disabled={!simName || changes.length === 0 || createSim.isPending}
                className="mt-4 w-full bg-teal-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-teal-700 disabled:opacity-40"
              >
                {createSim.isPending ? "Computing…" : "Compute Simulation"}
              </button>
            </div>

            {/* Ops selector */}
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-50">
                <p className="text-xs font-semibold text-gray-600">Select Operations for Change</p>
              </div>
              <div className="max-h-72 overflow-y-auto divide-y divide-gray-50">
                {ops.map((op) => (
                  <label key={op.id} className="flex items-center gap-3 px-4 py-2 hover:bg-gray-50 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedOpIds.has(op.id)}
                      onChange={() => toggleOp(op.id)}
                      className="rounded"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-gray-700 truncate">{op.product_name || op.op_no}</p>
                      <p className="text-xs text-gray-400">{op.work_center_name || "—"} · {fmtMins(op.total_minutes)}</p>
                    </div>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${op.status === "BLOCKED" ? "bg-red-100 text-red-600" : op.status === "SCHEDULED" ? "bg-green-100 text-green-600" : "bg-gray-100 text-gray-500"}`}>
                      {op.status}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* Simulations List */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-50">
              <h2 className="text-sm font-semibold text-gray-700">Simulations ({sims.length})</h2>
            </div>
            {sims.length === 0 ? (
              <div className="p-8 text-center text-sm text-gray-400">No simulations yet</div>
            ) : (
              <div className="divide-y divide-gray-50">
                {sims.map((s) => (
                  <div
                    key={s.id}
                    className="px-5 py-3 cursor-pointer hover:bg-gray-50"
                    onClick={() => setViewSim(s)}
                  >
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-gray-800">{s.sim_name}</p>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${s.status === "PUBLISHED" ? "bg-green-100 text-green-700" : s.status === "COMPUTED" ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-500"}`}>
                        {s.status}
                      </span>
                    </div>
                    {s.impact_summary && <p className="text-xs text-gray-500 mt-0.5 truncate">{s.impact_summary}</p>}
                    <div className="flex gap-4 mt-1 text-xs">
                      {s.ops_rescheduled != null && <span>Rescheduled: <b>{s.ops_rescheduled}</b></span>}
                      {s.ops_delayed != null && <span>Delayed: <span className={impactColor(s.ops_delayed, true)}>{s.ops_delayed}</span></span>}
                      {s.utilization_delta != null && <span>Util Δ: <span className={impactColor(Number(s.utilization_delta))}>{Number(s.utilization_delta).toFixed(1)}%</span></span>}
                    </div>
                    {s.status === "COMPUTED" && (
                      <button
                        onClick={(e) => { e.stopPropagation(); publishSim.mutate(s.id); }}
                        className="mt-2 text-xs px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200"
                      >
                        Publish
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Simulation detail modal */}
      {viewSim && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">{viewSim.sim_name}</h2>
              <button onClick={() => setViewSim(null)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-4">
              {[
                { label: "Rescheduled Ops", value: viewSim.ops_rescheduled ?? "—" },
                { label: "Delayed Ops", value: viewSim.ops_delayed ?? "—" },
                { label: "Util Δ", value: viewSim.utilization_delta != null ? `${Number(viewSim.utilization_delta).toFixed(1)}%` : "—" },
                { label: "CO Hours Δ", value: viewSim.changeover_delta_hrs != null ? `${Number(viewSim.changeover_delta_hrs).toFixed(1)}h` : "—" },
                { label: "Throughput Δ", value: viewSim.throughput_delta_pct != null ? `${Number(viewSim.throughput_delta_pct).toFixed(1)}%` : "—" },
                { label: "Status", value: viewSim.status },
              ].map((k) => (
                <div key={k.label} className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-400">{k.label}</p>
                  <p className="text-sm font-bold text-gray-800">{String(k.value)}</p>
                </div>
              ))}
            </div>
            {viewSim.impact_summary && (
              <div className="bg-blue-50 rounded-lg p-3 mb-4">
                <p className="text-sm text-blue-800">{viewSim.impact_summary}</p>
              </div>
            )}
            <p className="text-xs text-gray-400 text-right">
              {viewSim.changes?.length ?? 0} change(s) · {viewSim.sim_no}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
