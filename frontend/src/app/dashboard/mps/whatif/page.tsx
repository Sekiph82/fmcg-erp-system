"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import {
  mpsApi, MPSPlanSummary, MPSLine, MPSWhatIf, MPSScenarioComparison,
  WhatIfChange, MPSChangeType,
} from "@/lib/mps";

const CHANGE_TYPES: { value: MPSChangeType; label: string; desc: string }[] = [
  { value: "DELAY",      label: "Delay",        desc: "Shift dates forward (days)" },
  { value: "QTY_ADJUST", label: "Adjust Qty",   desc: "Set new planned quantity" },
  { value: "BATCH_SIZE", label: "Batch Size",   desc: "Change batch size (units)" },
  { value: "LINE_CHANGE",label: "Change Line",  desc: "Move to different work center ID" },
  { value: "SPLIT",      label: "Split Batch",  desc: "Split into two exact quantities; total must be conserved" },
  { value: "MERGE",      label: "Merge Lines",  desc: "Combine two equivalent scheduled lines" },
  { value: "SHIFT_ADD",  label: "Add Shift",    desc: "Add a specific non-overlapping shift interval" },
];

export default function WhatIfPage() {
  const qc = useQueryClient();
  const { hasPermission } = useAuth();
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [selectedLines, setSelectedLines] = useState<Set<string>>(new Set());
  const [changeType, setChangeType] = useState<MPSChangeType>("DELAY");
  const [changeValue, setChangeValue] = useState("");
  const [changeSecondaryValue, setChangeSecondaryValue] = useState("");
  const [shiftDate, setShiftDate] = useState("");
  const [shiftStartTime, setShiftStartTime] = useState("");
  const [shiftEndTime, setShiftEndTime] = useState("");
  const [mergeLineId, setMergeLineId] = useState("");
  const [scenarioName, setScenarioName] = useState("");
  const [description, setDescription] = useState("");
  const [changes, setChanges] = useState<WhatIfChange[]>([]);
  const [viewScenario, setViewScenario] = useState<MPSWhatIf | null>(null);
  const [baselineId, setBaselineId] = useState("");
  const [candidateId, setCandidateId] = useState("");
  const [comparison, setComparison] = useState<MPSScenarioComparison | null>(null);

  function shiftDurationHours(): number | null {
    if (!shiftStartTime || !shiftEndTime) return null;
    const minuteOfDay = (value: string) => {
      const [hours, minutes] = value.split(":").map(Number);
      return hours * 60 + minutes;
    };
    const start = minuteOfDay(shiftStartTime);
    const rawEnd = minuteOfDay(shiftEndTime);
    const end = rawEnd === 0 && start > 0 ? 24 * 60 : rawEnd;
    return end > start ? (end - start) / 60 : null;
  }

  const { data: plans = [], isLoading: plansLoading, error: plansError } = useQuery<MPSPlanSummary[]>({
    queryKey: ["mps-plans"],
    queryFn: () => mpsApi.listPlans(),
  });

  const { data: lines = [], isLoading: linesLoading, error: linesError } = useQuery<MPSLine[]>({
    queryKey: ["mps-lines", selectedPlanId],
    queryFn: () => mpsApi.listLines(selectedPlanId!),
    enabled: !!selectedPlanId,
  });

  const { data: scenarios = [], isLoading: scenariosLoading, error: scenariosError } = useQuery<MPSWhatIf[]>({
    queryKey: ["mps-whatif", selectedPlanId],
    queryFn: () => mpsApi.listWhatIf(selectedPlanId!),
    enabled: !!selectedPlanId,
  });

  const createScenario = useMutation({
    mutationFn: () =>
      mpsApi.createWhatIf(selectedPlanId!, {
        scenario_name: scenarioName,
        description,
        changes,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mps-whatif", selectedPlanId] });
      setChanges([]);
      setSelectedLines(new Set());
      setScenarioName("");
      setDescription("");
    },
  });

  const compareScenarios = useMutation({
    mutationFn: () => mpsApi.compareWhatIf(selectedPlanId!, baselineId, candidateId),
    onSuccess: setComparison,
  });

  function canStageChange() {
    if (selectedLines.size === 0) return false;
    if (["SPLIT", "MERGE", "SHIFT_ADD"].includes(changeType) && selectedLines.size !== 1) return false;
    if (changeType === "SPLIT") return Boolean(changeValue && changeSecondaryValue);
    if (changeType === "MERGE") return Boolean(mergeLineId);
    if (changeType === "SHIFT_ADD") return Boolean(shiftDate && shiftDurationHours() != null);
    return Boolean(changeValue);
  }

  function addChange() {
    if (!canStageChange()) return;
    const selected = Array.from(selectedLines);
    if (["SPLIT", "MERGE", "SHIFT_ADD"].includes(changeType) && selected.length !== 1) return;
    const newChanges: WhatIfChange[] = selected.map((lid) => ({
      line_id: lid,
      change_type: changeType,
      new_value: changeType === "DELAY" || changeType === "QTY_ADJUST" || changeType === "BATCH_SIZE"
        ? Number(changeValue)
        : changeType === "SPLIT"
          ? { quantities: [changeValue, changeSecondaryValue] }
          : changeType === "MERGE"
            ? mergeLineId
            : changeType === "SHIFT_ADD"
              ? { date: shiftDate, start_time: shiftStartTime, end_time: shiftEndTime, hours: String(shiftDurationHours()) }
              : changeValue,
    }));
    setChanges((prev) => [...prev, ...newChanges]);
    setSelectedLines(new Set());
    setChangeValue("");
    setChangeSecondaryValue("");
    setShiftDate("");
    setShiftStartTime("");
    setShiftEndTime("");
    setMergeLineId("");
  }

  function toggleLine(id: string) {
    setSelectedLines((prev) => {
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
  const finiteMetric = (value: number | string | null | undefined) => {
    if (value == null || value === "") return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">What-If Simulation</h1>
        <a href="/dashboard/mps" className="text-xs text-blue-600 hover:underline">← MPS Dashboard</a>
      </div>
      {plansLoading && <p role="status" aria-live="polite" className="text-sm text-gray-500">Loading plans…</p>}
      {plansError && <p role="alert" className="text-sm text-red-700">Could not load MPS plans: {(plansError as Error).message}</p>}
      {createScenario.error && <p role="alert" className="text-sm text-red-700">Scenario creation failed: {(createScenario.error as Error).message}</p>}

      {/* Plan selector */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
        <label htmlFor="whatif-plan" className="sr-only">Select MPS plan</label>
        <select
          id="whatif-plan"
          aria-label="Select MPS plan"
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm min-w-64"
          value={selectedPlanId || ""}
          onChange={(e) => setSelectedPlanId(e.target.value || null)}
        >
          <option value="">-- select plan --</option>
          {plans.map((p) => (
            <option key={p.id} value={p.id}>{p.plan_no} — {p.plan_name}</option>
          ))}
        </select>
      </div>

      {selectedPlanId && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Builder */}
          {hasPermission("mps.simulate") && <div className="space-y-4">
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
              <h2 className="text-sm font-semibold text-gray-700 mb-3">Build Scenario</h2>
              <div className="space-y-3">
                <input
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  placeholder="Scenario name *"
                  value={scenarioName}
                  onChange={(e) => setScenarioName(e.target.value)}
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
                    value={changeType}
                    onChange={(e) => setChangeType(e.target.value as MPSChangeType)}
                  >
                    {CHANGE_TYPES.map((ct) => (
                      <option key={ct.value} value={ct.value}>{ct.label} — {ct.desc}</option>
                    ))}
                  </select>
                  {changeType === "MERGE" ? (
                    <select className="border border-gray-200 rounded px-2 py-1.5 text-xs" value={mergeLineId} onChange={(e) => setMergeLineId(e.target.value)}>
                      <option value="">Select line to merge into selected line</option>
                      {lines.filter((line) => !selectedLines.has(line.id)).map((line) => (
                        <option key={line.id} value={line.id}>{line.line_no} — {line.product_name || line.product_id.slice(0, 12)}</option>
                      ))}
                    </select>
                  ) : changeType === "SPLIT" ? (
                    <>
                      <input aria-label="First split quantity" className="border border-gray-200 rounded px-2 py-1.5 text-xs" placeholder="First exact quantity" value={changeValue} onChange={(e) => setChangeValue(e.target.value)} />
                      <input aria-label="Second split quantity" className="border border-gray-200 rounded px-2 py-1.5 text-xs" placeholder="Second exact quantity" value={changeSecondaryValue} onChange={(e) => setChangeSecondaryValue(e.target.value)} />
                    </>
                  ) : changeType === "SHIFT_ADD" ? (
                    <>
                      <input aria-label="Shift date" type="date" className="border border-gray-200 rounded px-2 py-1.5 text-xs" value={shiftDate} onChange={(e) => setShiftDate(e.target.value)} />
                      <input aria-label="Additional shift start time" type="time" className="border border-gray-200 rounded px-2 py-1.5 text-xs" value={shiftStartTime} onChange={(e) => setShiftStartTime(e.target.value)} />
                      <input aria-label="Additional shift end time" type="time" className="border border-gray-200 rounded px-2 py-1.5 text-xs" value={shiftEndTime} onChange={(e) => setShiftEndTime(e.target.value)} />
                      <span className="col-span-2 text-xs text-gray-500">Added time: {shiftDurationHours() == null ? "choose a valid interval" : `${shiftDurationHours()} hours`}</span>
                    </>
                  ) : (
                    <input
                      className="border border-gray-200 rounded px-2 py-1.5 text-xs"
                      placeholder={changeType === "DELAY" ? "Days to delay" : changeType === "LINE_CHANGE" ? "Work center UUID" : "New value"}
                      value={changeValue}
                      onChange={(e) => setChangeValue(e.target.value)}
                    />
                  )}
                </div>
                {["SPLIT", "MERGE", "SHIFT_ADD"].includes(changeType) && (
                  <p className="text-xs text-gray-500">Choose exactly one target line. {changeType === "MERGE" ? "Both lines must share source, product, batch, campaign, feasibility, period, dates and work center." : changeType === "SPLIT" ? "Enter two positive quantities (up to 3 decimals) whose sum exactly equals the line quantity." : "Use a FINITE plan and a date inside the line schedule. The added start/end interval must not overlap configured shifts or another addition."}</p>
                )}
                <p className="text-xs text-gray-400">
                  {selectedLines.size} line(s) selected below
                </p>
                <button
                  onClick={addChange}
                  disabled={!canStageChange()}
                  className="w-full py-1.5 text-xs bg-indigo-600 text-white rounded-lg disabled:opacity-40 hover:bg-indigo-700"
                >
                  Add Change to Scenario
                </button>
              </div>

              {/* Changes list */}
              {changes.length > 0 && (
                <div className="mt-3 space-y-1">
                  <p className="text-xs font-medium text-gray-500 mb-1">{changes.length} change(s) staged:</p>
                  {changes.map((c, i) => (
                    <div key={i} className="flex items-center justify-between text-xs bg-blue-50 rounded px-2 py-1">
                      <span className="text-blue-700">{c.change_type}: {typeof c.new_value === "object" ? JSON.stringify(c.new_value) : String(c.new_value)}</span>
                      <button
                        onClick={() => setChanges((prev) => prev.filter((_, j) => j !== i))}
                        className="text-gray-400 hover:text-red-500"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <button
                onClick={() => createScenario.mutate()}
                disabled={!scenarioName || changes.length === 0 || createScenario.isPending}
                className="mt-4 w-full bg-teal-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-teal-700 disabled:opacity-40"
              >
                {createScenario.isPending ? "Computing…" : "Compute Impact"}
              </button>
            </div>

            {/* Lines selector */}
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-50">
                <p className="text-xs font-semibold text-gray-600">Select Lines for Change</p>
              </div>
              <div className="max-h-64 overflow-y-auto divide-y divide-gray-50">
                {linesLoading ? (
                  <p role="status" aria-live="polite" className="p-5 text-center text-sm text-gray-400">Loading lines…</p>
                ) : linesError ? (
                  <p role="alert" className="p-5 text-center text-sm text-red-700">Could not load plan lines: {(linesError as Error).message}</p>
                ) : lines.length === 0 ? (
                  <p className="p-5 text-center text-sm text-gray-400">No lines available for this plan.</p>
                ) : lines.map((l) => (
                  <label
                    key={l.id}
                    className="flex items-center gap-3 px-4 py-2 hover:bg-gray-50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedLines.has(l.id)}
                      onChange={() => toggleLine(l.id)}
                      className="rounded"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-gray-700 truncate">
                        {l.product_name || l.product_id.slice(0, 12)}
                      </p>
                      <p className="text-xs text-gray-400">{l.line_no} · {l.period_label || l.period_start}</p>
                    </div>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                      l.feasibility_status === "OVERLOADED" ? "bg-red-100 text-red-600" :
                      l.feasibility_status === "FEASIBLE" ? "bg-green-100 text-green-600" :
                      "bg-gray-100 text-gray-500"
                    }`}>
                      {l.feasibility_status}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </div>}

          {/* Scenarios list */}
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 space-y-3">
              <h2 className="text-sm font-semibold text-gray-700">Compare saved snapshots</h2>
              <div className="flex flex-wrap gap-2">
                <select aria-label="Baseline scenario" className="border rounded px-2 py-1 text-sm" value={baselineId} onChange={(e) => setBaselineId(e.target.value)}>
                  <option value="">Baseline</option>{scenarios.map((s) => <option key={s.id} value={s.id}>{s.scenario_name}</option>)}
                </select>
                <select aria-label="Candidate scenario" className="border rounded px-2 py-1 text-sm" value={candidateId} onChange={(e) => setCandidateId(e.target.value)}>
                  <option value="">Candidate</option>{scenarios.map((s) => <option key={s.id} value={s.id}>{s.scenario_name}</option>)}
                </select>
                <button disabled={!baselineId || !candidateId || baselineId === candidateId || compareScenarios.isPending} onClick={() => compareScenarios.mutate()} className="rounded bg-indigo-700 px-3 py-1 text-sm text-white disabled:opacity-50">Compare</button>
              </div>
              {comparison && <div role="status" aria-live="polite" className="space-y-2 text-xs text-gray-600">
                <p>Service level Δ {comparison.service_level_pct_delta.toFixed(1)} pp · Delayed lines Δ {comparison.delay_count_delta} lines</p>
                <p>Material shortages Δ {comparison.material_status === "COMPLETE" && comparison.material_shortage_count_delta != null ? `${comparison.material_shortage_count_delta} lines` : "incomplete inputs"}
                  {comparison.material_shortage_quantity_by_uom_delta && ` · Quantity Δ ${Object.entries(comparison.material_shortage_quantity_by_uom_delta).map(([uom, quantity]) => `${quantity} ${uom}`).join(", ") || "0 by source UOM"}`}
                </p>
                <p>Capacity overload Δ {comparison.capacity_status === "COMPLETE" && comparison.capacity_overload_hours_delta != null ? `${comparison.capacity_overload_hours_delta.toFixed(3)} hours` : "incomplete inputs"}
                  · Changeover Δ {comparison.changeover_status === "COMPLETE" && comparison.changeover_hours_delta != null ? `${comparison.changeover_hours_delta.toFixed(3)} hours` : "incomplete inputs"}
                  · CIP Δ {comparison.cip_status === "COMPLETE" && comparison.cip_hours_delta != null ? `${comparison.cip_hours_delta.toFixed(3)} hours` : "incomplete inputs"}
                </p>
                <p>Estimated cost Δ {comparison.cost_delta_status === "COMPLETE" && comparison.cost_delta != null && comparison.cost_currency
                  ? `${comparison.cost_currency} ${comparison.cost_delta.toFixed(4)}`
                  : `unknown (${comparison.cost_delta_status.replaceAll("_", " ").toLowerCase()})`} · Confidence: {comparison.confidence_status.replaceAll("_", " ").toLowerCase()}</p>
                {comparison.unknowns.length > 0 && <p>Unknown inputs: {comparison.unknowns.join("; ")}</p>}
                <details>
                  <summary className="cursor-pointer">KPI sources</summary>
                  <ul className="list-disc pl-5">
                    {Object.entries(comparison.metric_sources).map(([metric, source]) => <li key={metric}>{metric.replaceAll("_", " ")}: {source}</li>)}
                  </ul>
                </details>
              </div>}
              {compareScenarios.isError && <p role="alert" className="text-xs text-red-700">{(compareScenarios.error as Error).message}</p>}
            </div>
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-50">
                <h2 className="text-sm font-semibold text-gray-700">Scenarios ({scenarios.length})</h2>
              </div>
              {scenariosLoading ? (
                <div role="status" aria-live="polite" className="p-8 text-center text-sm text-gray-400">Loading scenarios…</div>
              ) : scenariosError ? (
                <div role="alert" className="p-8 text-center text-sm text-red-700">Could not load scenarios: {(scenariosError as Error).message}</div>
              ) : scenarios.length === 0 ? (
                <div className="p-8 text-center text-sm text-gray-400">No scenarios yet</div>
              ) : (
                <div className="divide-y divide-gray-50">
                  {scenarios.map((s) => (
                    <div
                      key={s.id}
                      className="px-5 py-3 cursor-pointer hover:bg-gray-50"
                      onClick={() => setViewScenario(s)}
                    >
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-gray-800">{s.scenario_name}</p>
                        <span className="text-xs text-gray-400">{s.scenario_no}</span>
                      </div>
                      {s.impact_summary && (
                        <p className="text-xs text-gray-500 mt-0.5 truncate">{s.impact_summary}</p>
                      )}
                      <div className="flex gap-4 mt-1 text-xs">
                        <span>
                          SL: <span className={impactColor(finiteMetric(s.impact_service_level_pct))}>
                            {finiteMetric(s.impact_service_level_pct)?.toFixed(1) ?? "—"}%
                          </span>
                        </span>
                        <span>
                          Delays: <span className={impactColor(finiteMetric(s.impact_delay_count), true)}>
                            {finiteMetric(s.impact_delay_count) ?? "—"}
                          </span>
                        </span>
                        <span>
                          Cost Δ: <span className={impactColor(finiteMetric(s.impact_cost_delta), true)}>
                            {finiteMetric(s.impact_cost_delta) != null
                              ? `${s.impact_cost_currency ? `${s.impact_cost_currency} ` : ""}${finiteMetric(s.impact_cost_delta)!.toLocaleString()}`
                              : "—"}
                          </span>
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Scenario detail modal */}
      {viewScenario && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">{viewScenario.scenario_name}</h2>
              <button onClick={() => setViewScenario(null)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>

            <div className="grid grid-cols-3 gap-3 mb-4">
              {[
                { label: "Service Level", value: `${finiteMetric(viewScenario.impact_service_level_pct)?.toFixed(1) ?? "—"}%`, color: "text-blue-700" },
                { label: "Delayed Lines", value: finiteMetric(viewScenario.impact_delay_count) ?? "—", color: Number(viewScenario.impact_delay_count) > 0 ? "text-red-600" : "text-green-600" },
                { label: "Cost Delta", value: finiteMetric(viewScenario.impact_cost_delta) != null ? `${viewScenario.impact_cost_currency ? `${viewScenario.impact_cost_currency} ` : ""}${finiteMetric(viewScenario.impact_cost_delta)!.toLocaleString()}` : "—", color: Number(viewScenario.impact_cost_delta) > 0 ? "text-red-600" : "text-green-600" },
              ].map((k) => (
                <div key={k.label} className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-400">{k.label}</p>
                  <p className={`text-lg font-bold ${k.color}`}>{k.value}</p>
                </div>
              ))}
            </div>

            {viewScenario.impact_summary && (
              <p className="text-sm text-gray-600 bg-blue-50 rounded-lg p-3 mb-4">{viewScenario.impact_summary}</p>
            )}

            <div>
              <p className="text-xs font-semibold text-gray-500 mb-2">Changes ({viewScenario.changes.length})</p>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {(viewScenario.changes as WhatIfChange[]).map((c, i) => (
                  <div key={i} className="flex items-center justify-between text-xs bg-gray-50 rounded px-2 py-1.5">
                    <span className="text-gray-500 font-mono">{c.line_id.slice(0, 8)}…</span>
                    <span className="text-indigo-600 font-medium">{c.change_type}</span>
                    <span className="text-gray-700">{typeof c.new_value === "object" ? JSON.stringify(c.new_value) : String(c.new_value)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
