"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { moApi, PerformanceSnapshot, Machine, MachineRuntimeKpis, PerformanceAnomalyReport, DowntimeProductionCorrelationReport } from "@/lib/machineOperator";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";

function OEEBadge({ oee }: { oee?: number | null }) {
  if (oee == null) return <span className="text-xs text-gray-400">—</span>;
  const pct = Number(oee) * 100;
  const cls = pct >= 85 ? "bg-green-100 text-green-700" : pct >= 65 ? "bg-yellow-100 text-yellow-700" : "bg-red-100 text-red-700";
  return <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>{pct.toFixed(1)}%</span>;
}

export default function PerformancePage() {
  const qc = useQueryClient();
  const [machineId, setMachineId] = useState("");
  const [dateFrom, setDateFrom] = useState(() => new Date(Date.now() - 29 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10));
  const [dateTo, setDateTo] = useState(() => new Date().toISOString().slice(0, 10));

  const { data: machines } = useQuery<Machine[]>({
    queryKey: ["mo-machines"],
    queryFn: () => moApi.listMachines(),
  });

  const { data: snapshots, isLoading } = useQuery<PerformanceSnapshot[]>({
    queryKey: ["mo-performance", machineId],
    queryFn: () => moApi.listPerformance(machineId ? { machine_id: machineId } : {}),
  });

  const runtimeKpisQuery = useQuery<MachineRuntimeKpis>({
    queryKey: ["mo-runtime-kpis", machineId, dateFrom, dateTo],
    queryFn: () => moApi.getMachineRuntimeKpis(machineId, { date_from: dateFrom, date_to: dateTo }),
    enabled: Boolean(machineId && dateFrom && dateTo),
  });

  const anomaliesQuery = useQuery<PerformanceAnomalyReport>({
    queryKey: ["mo-performance-anomalies", dateFrom, dateTo],
    queryFn: () => moApi.getPerformanceAnomalies({ date_from: dateFrom, date_to: dateTo }),
    enabled: Boolean(dateFrom && dateTo),
  });

  const correlationsQuery = useQuery<DowntimeProductionCorrelationReport>({
    queryKey: ["mo-downtime-production-correlations", dateFrom, dateTo],
    queryFn: () => moApi.getDowntimeProductionCorrelations({ date_from: dateFrom, date_to: dateTo }),
    enabled: Boolean(dateFrom && dateTo),
  });

  const compute = useMutation({
    mutationFn: () => moApi.computePerformance(machineId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mo-performance"] }),
  });

  const snaps = (snapshots || []).slice(0, 30).reverse();
  const chartData = snaps.map((s) => ({
    date: s.snapshot_date,
    oee: s.oee != null ? +(Number(s.oee) * 100).toFixed(1) : null,
    availability: s.availability != null ? +(Number(s.availability) * 100).toFixed(1) : null,
    performance: s.performance != null ? +(Number(s.performance) * 100).toFixed(1) : null,
    quality: s.quality_rate != null ? +(Number(s.quality_rate) * 100).toFixed(1) : null,
  }));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <a href="/dashboard/machine-ops" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
        <h1 className="text-xl font-bold text-gray-900">Machine Runtime and Performance</h1>
      </div>

      <p className="text-xs text-amber-700">Availability and OEE require an authoritative machine schedule and production-quality inputs. Cost attribution is pending its dedicated milestone task. The runtime panel below reports timestamp-backed activity logs only; missing inputs are not estimated.</p>

      <div className="bg-white rounded-lg border p-4 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Machine</label>
          <select value={machineId} onChange={(e) => setMachineId(e.target.value)} className="border rounded px-3 py-2 text-sm w-64">
            <option value="">All Machines</option>
            {(machines || []).map((m) => <option key={m.id} value={m.id}>{m.machine_code} — {m.machine_name}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">From (UTC)</label>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="border rounded px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">To (UTC)</label>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="border rounded px-3 py-2 text-sm" />
        </div>
        {machineId && (
          <button onClick={() => compute.mutate()} disabled={compute.isPending} className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50">
            {compute.isPending ? "Computing…" : "Compute Today"}
          </button>
        )}
      </div>

      <section className="bg-white rounded-lg border p-4 space-y-3" aria-label="Recorded machine runtime KPIs">
        <div>
          <h2 className="font-semibold text-gray-800">Recorded Runtime KPIs</h2>
          <p className="text-xs text-gray-500">Durations are clipped to the selected UTC dates and grouped by recorded activity. Select a machine to view its source logs.</p>
        </div>
        {!machineId && <p className="text-sm text-gray-500">Select a machine to load runtime evidence.</p>}
        {machineId && runtimeKpisQuery.isLoading && <p className="text-sm text-gray-500">Loading runtime evidence…</p>}
        {machineId && runtimeKpisQuery.isError && <p className="text-sm text-red-600">Runtime KPIs could not be loaded for this date range.</p>}
        {runtimeKpisQuery.data && (
          <>
            <p className="text-xs text-gray-500">{runtimeKpisQuery.data.machine_code} — {runtimeKpisQuery.data.machine_name}; {runtimeKpisQuery.data.period_start} to {runtimeKpisQuery.data.period_end} UTC. Sum of activity-log durations: {(runtimeKpisQuery.data.recorded_activity_log_minutes / 60).toFixed(2)} h.</p>
            <div className="overflow-x-auto rounded border">
              <table className="w-full text-sm">
                <thead className="bg-gray-50"><tr><th className="p-2 text-left">Recorded activity</th><th className="p-2 text-right">Log minutes</th><th className="p-2 text-right">Logs</th></tr></thead>
                <tbody>
                  {runtimeKpisQuery.data.activities.map((row) => (
                    <tr key={row.activity_type} className="border-t"><td className="p-2">{row.activity_type}</td><td className="p-2 text-right">{Number(row.duration_minutes).toFixed(2)}</td><td className="p-2 text-right">{row.log_count}</td></tr>
                  ))}
                  {!runtimeKpisQuery.data.activities.length && <tr><td colSpan={3} className="p-4 text-center text-gray-500">No completed runtime intervals were recorded in this period.</td></tr>}
                </tbody>
              </table>
            </div>
            {runtimeKpisQuery.data.unavailable_runtime_log_ids.length > 0 && <p className="text-xs text-amber-700">{runtimeKpisQuery.data.unavailable_runtime_log_ids.length} open or invalid runtime interval(s) were excluded from duration totals.</p>}
            <details className="text-xs text-gray-500"><summary className="cursor-pointer">Source IDs and calculation notes</summary><div className="mt-2 space-y-2">{runtimeKpisQuery.data.activities.map((row) => <p key={row.activity_type}>{row.activity_type}: {row.source_runtime_log_ids.join(", ") || "none"}</p>)}<p>Unavailable: {runtimeKpisQuery.data.unavailable_runtime_log_ids.join(", ") || "none"}</p><ul className="list-disc pl-5 space-y-1">{runtimeKpisQuery.data.data_notes.map((note) => <li key={note}>{note}</li>)}</ul></div></details>
          </>
        )}
      </section>

      <section className="bg-white rounded-lg border p-4 space-y-3" aria-label="Recorded performance anomalies">
        <div>
          <h2 className="font-semibold text-gray-800">Recorded Downtime Anomalies</h2>
          <p className="text-xs text-gray-500">Deterministic, machine-specific comparison against prior recorded downtime; this does not predict failures or claim live IoT alerts.</p>
        </div>
        {anomaliesQuery.isLoading && <p className="text-sm text-gray-500">Reviewing downtime history…</p>}
        {anomaliesQuery.isError && <p role="alert" className="text-sm text-red-600">Downtime anomaly analysis could not be loaded for this date range.</p>}
        {anomaliesQuery.data && (
          <>
            <p className="text-xs text-gray-500">Target period: {anomaliesQuery.data.period_start} to {anomaliesQuery.data.period_end} UTC; baseline begins {anomaliesQuery.data.baseline_start} UTC.</p>
            {anomaliesQuery.data.anomalies.length ? (
              <div className="overflow-x-auto rounded border">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50"><tr><th className="p-2 text-left">Machine</th><th className="p-2 text-left">Downtime interval (UTC)</th><th className="p-2 text-right">Observed</th><th className="p-2 text-right">Baseline</th><th className="p-2 text-right">Rule limit</th><th className="p-2">Evidence</th></tr></thead>
                  <tbody className="divide-y">
                    {anomaliesQuery.data.anomalies.map((anomaly) => (
                      <tr key={anomaly.runtime_log_id}>
                        <td className="p-2"><div className="font-medium">{anomaly.machine_code}</div><div className="text-xs text-gray-500">{anomaly.machine_name}</div></td>
                        <td className="p-2 text-xs">{anomaly.event_start.slice(0, 16).replace("T", " ")} — {anomaly.event_end.slice(0, 16).replace("T", " ")}</td>
                        <td className="p-2 text-right">{anomaly.observed_downtime_minutes.toFixed(1)} min</td>
                        <td className="p-2 text-right text-xs">median {anomaly.baseline_median_minutes.toFixed(1)} min<br />{anomaly.baseline_event_count} events</td>
                        <td className="p-2 text-right">&gt; {anomaly.alert_threshold_minutes.toFixed(1)} min</td>
                        <td className="p-2 text-xs"><details><summary className="cursor-pointer text-indigo-700">Source IDs</summary><div className="mt-1 max-w-sm break-all text-gray-500">Event: {anomaly.runtime_log_id}<br />Baseline: {anomaly.source_baseline_runtime_log_ids.join(", ")}</div></details></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <p className="text-sm text-gray-500">No downtime interval crossed the recorded-history rule in this period.</p>}
            {!!anomaliesQuery.data.insufficient_baseline_machine_ids.length && <p className="text-xs text-amber-700">Insufficient history for {anomaliesQuery.data.insufficient_baseline_machine_ids.length} machine(s); at least five valid prior downtime events are required. IDs: {anomaliesQuery.data.insufficient_baseline_machine_ids.join(", ")}</p>}
            {(anomaliesQuery.data.unavailable_runtime_log_ids.length > 0 || anomaliesQuery.data.overlapping_runtime_log_ids.length > 0) && <p className="text-xs text-amber-700">Excluded from the rule: {anomaliesQuery.data.unavailable_runtime_log_ids.length} open/invalid interval(s), {anomaliesQuery.data.overlapping_runtime_log_ids.length} overlapping interval(s).</p>}
            <details className="text-xs text-gray-500"><summary className="cursor-pointer">Rule and scope notes</summary><ul className="mt-2 list-disc space-y-1 pl-5">{anomaliesQuery.data.data_notes.map((note) => <li key={note}>{note}</li>)}</ul></details>
          </>
        )}
      </section>

      <section className="bg-white rounded-lg border p-4 space-y-3" aria-label="Downtime production correlations">
        <div>
          <h2 className="font-semibold text-gray-800">Downtime, Operator, Quality &amp; Waste Correlations</h2>
          <p className="text-xs text-gray-500">Shows explicit order links and same-machine/time overlap. Correlation does not establish cause.</p>
        </div>
        {correlationsQuery.isLoading && <p className="text-sm text-gray-500">Loading linked production evidence…</p>}
        {correlationsQuery.isError && <p role="alert" className="text-sm text-red-600">Downtime correlations could not be loaded for this date range.</p>}
        {correlationsQuery.data && (
          <>
            <p className="text-xs text-gray-500">UTC period: {correlationsQuery.data.period_start} to {correlationsQuery.data.period_end}</p>
            {!correlationsQuery.data.events.length ? <p className="text-sm text-gray-500">No recorded downtime events in this period.</p> : (
              <div className="space-y-3">
                {correlationsQuery.data.events.map((event) => (
                  <article key={event.downtime_id} className="rounded border p-3">
                    <div className="font-medium text-sm">{event.machine_code} — {event.downtime_class}</div>
                    <div className="text-xs text-gray-500">{event.start_time.slice(0, 16).replace("T", " ")}{event.end_time ? " — " + event.end_time.slice(0, 16).replace("T", " ") : " — open"} · {event.duration_minutes == null ? "duration unavailable" : Number(event.duration_minutes).toFixed(1) + " min"}</div>
                    <div className="break-all text-[10px] text-gray-400">WO {event.work_order_id || "unlinked"} · PO {event.production_order_id || "unlinked"}</div>
                    <div className="mt-2 grid gap-3 md:grid-cols-3 text-xs">
                      <div><strong>Observed operators</strong><div className="break-all">{event.observed_operator_ids.join(", ") || "No overlapping operator logs"}</div><div className="text-gray-500">{event.runtime_log_ids.length} runtime · {event.labor_logs.length} labor records</div>{event.labor_logs.some((log) => !log.approved_flag) && <div className="text-amber-700">Includes unapproved labor logs</div>}</div>
                      <div><strong>QC</strong>{event.quality_inspections.length ? event.quality_inspections.map((qc) => <div key={qc.inspection_id} className="mt-1">{qc.qc_id}: {qc.status}{qc.results.map((result) => <div key={result.result_id} className="text-gray-500">{result.test_type}: {result.result}{result.actual_value == null ? "" : " (" + result.actual_value + (result.unit ? " " + result.unit : "") + ")"}</div>)}</div>) : <div className="text-gray-500">No same-order QC link</div>}</div>
                      <div><strong>Waste</strong>{event.waste_records.length ? event.waste_records.map((waste) => <div key={waste.waste_record_id} className="mt-1">{waste.waste_id}: loss {Number(waste.loss_qty).toLocaleString()} {waste.uom || "unit not recorded"}{waste.is_anomaly ? " · flagged" : ""}</div>) : <div className="text-gray-500">No same-order waste link</div>}</div>
                    </div>
                    <details className="mt-2 text-xs"><summary className="cursor-pointer text-indigo-700">Source IDs and correlation basis</summary><div className="mt-1 break-all text-gray-500">Downtime: {event.downtime_id}<br />Runtime: {event.runtime_log_ids.join(", ") || "none"}<br />Labor: {event.labor_logs.map((log) => log.labor_log_id).join(", ") || "none"}<br />QC: {event.quality_inspections.map((qc) => qc.inspection_id).join(", ") || "none"}<br />Waste: {event.waste_records.map((waste) => waste.waste_record_id).join(", ") || "none"}<br />Basis: {event.correlation_basis.join(", ") || "no linked evidence"}</div></details>
                  </article>
                ))}
              </div>
            )}
            <div className="rounded border border-indigo-100 bg-indigo-50 p-3 space-y-2" aria-label="Evidence-backed follow-up handoffs">
              <h3 className="text-sm font-semibold text-indigo-950">Evidence-backed follow-up</h3>
              <p className="text-xs text-indigo-900">Review suggestions are routed to existing modules. They do not create maintenance, training, or schedule records and do not assign fault.</p>
              {!correlationsQuery.data.follow_up_handoffs.length ? <p className="text-xs text-gray-600">No handoff met the recorded evidence rules for this period.</p> : (
                <div className="space-y-2">
                  {correlationsQuery.data.follow_up_handoffs.map((handoff) => (
                    <article key={handoff.handoff_id} className="rounded border bg-white p-3 text-xs">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <strong>{handoff.title} · {handoff.machine_code}</strong>
                        <a href={handoff.destination_path} className="text-indigo-700 underline">Open {handoff.destination} module</a>
                      </div>
                      <p className="mt-1 text-gray-700">{handoff.rationale}</p>
                      <p className="mt-1 break-all text-gray-500">WO {handoff.work_order_id || "unlinked"} · PO {handoff.production_order_id || "unlinked"} · downtime {handoff.downtime_id}</p>
                      <details className="mt-1">
                        <summary className="cursor-pointer text-indigo-700">Evidence IDs and scope</summary>
                        <p className="mt-1 break-all text-gray-500">Sources: {handoff.source_ids.join(", ") || "none"}</p>
                        <p className="mt-1 text-gray-500">{handoff.attribution_note}</p>
                      </details>
                    </article>
                  ))}
                </div>
              )}
            </div>
            <details className="text-xs text-gray-500"><summary className="cursor-pointer">Correlation and scope notes</summary><ul className="mt-2 list-disc space-y-1 pl-5">{correlationsQuery.data.data_notes.map((note) => <li key={note}>{note}</li>)}</ul></details>
          </>
        )}
      </section>

      {/* OEE Trend Chart */}
      {chartData.length > 0 && (
        <div className="bg-white rounded-lg border p-5">
          <h2 className="font-semibold text-gray-800 mb-4">Stored OEE snapshots (last 30 days)</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} margin={{ top: 0, right: 10, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} unit="%" />
              <Tooltip formatter={((v: number) => `${v}%`) as never} />
              <ReferenceLine y={85} stroke="#22c55e" strokeDasharray="4 4" label={{ value: "World Class 85%", fill: "#22c55e", fontSize: 10 }} />
              <ReferenceLine y={65} stroke="#f59e0b" strokeDasharray="4 4" />
              <Bar dataKey="oee" name="OEE" fill="#6366f1" radius={[3, 3, 0, 0]} />
              <Bar dataKey="availability" name="Availability" fill="#22c55e" radius={[3, 3, 0, 0]} />
              <Bar dataKey="performance" name="Performance" fill="#f59e0b" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-lg border overflow-x-auto">
        {isLoading && <div className="p-6 text-gray-400 text-sm">Loading…</div>}
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>{["Date", "Machine", "Planned", "Run", "Setup", "Downtime", "Changeover", "Units", "Good", "Avail", "Perf", "Quality", "OEE", "Cost", "Flags"].map((h) => (
              <th key={h} className="px-3 py-2 text-left text-xs font-medium text-gray-600 whitespace-nowrap">{h}</th>
            ))}</tr>
          </thead>
          <tbody className="divide-y">
            {(snapshots || []).map((s) => (
              <tr key={s.id} className={`hover:bg-gray-50 ${s.anomaly_flag ? "bg-red-50" : ""}`}>
                <td className="px-3 py-2 text-xs font-medium">{s.snapshot_date}</td>
                <td className="px-3 py-2 text-xs font-mono">{s.machine_code || s.machine_id?.slice(0, 8)}</td>
                <td className="px-3 py-2 text-xs">{s.planned_time_min > 0 ? `${s.planned_time_min} min` : "Not recorded"}</td>
                <td className="px-3 py-2 text-xs">{Number(s.run_time_min).toFixed(0)} min</td>
                <td className="px-3 py-2 text-xs">{Number(s.setup_time_min).toFixed(0)} min</td>
                <td className={`px-3 py-2 text-xs font-medium ${s.high_downtime_flag ? "text-red-600" : ""}`}>{Number(s.downtime_min).toFixed(0)} min</td>
                <td className="px-3 py-2 text-xs">{Number(s.changeover_time_min).toFixed(0)} min</td>
                <td className="px-3 py-2 text-xs">{Number(s.units_produced).toLocaleString()}</td>
                <td className="px-3 py-2 text-xs">{Number(s.good_units).toLocaleString()}</td>
                <td className="px-3 py-2 text-xs">{s.availability != null ? `${(Number(s.availability) * 100).toFixed(1)}%` : "—"}</td>
                <td className="px-3 py-2 text-xs">{s.performance != null ? `${(Number(s.performance) * 100).toFixed(1)}%` : "—"}</td>
                <td className="px-3 py-2 text-xs">{s.quality_rate != null ? `${(Number(s.quality_rate) * 100).toFixed(1)}%` : "—"}</td>
                <td className="px-3 py-2"><OEEBadge oee={s.oee} /></td>
                <td className="px-3 py-2 text-xs">{s.machine_cost_actual != null ? `KES ${Number(s.machine_cost_actual).toLocaleString()}` : "—"}</td>
                <td className="px-3 py-2 text-xs">
                  {s.low_oee_flag && <span className="bg-red-100 text-red-700 text-xs px-1.5 py-0.5 rounded mr-1">Low OEE</span>}
                  {s.high_downtime_flag && <span className="bg-orange-100 text-orange-700 text-xs px-1.5 py-0.5 rounded">Hi DT</span>}
                </td>
              </tr>
            ))}
            {!isLoading && !(snapshots?.length) && (
              <tr><td colSpan={15} className="px-4 py-8 text-center text-gray-400 text-sm">No performance snapshots. Select a machine and click &ldquo;Compute Today&rdquo;.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
