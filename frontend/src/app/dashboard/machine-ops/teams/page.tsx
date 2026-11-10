"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { moApi, ProductionTeam, OperatorProfile, ShiftTeamComparisonGroup } from "@/lib/machineOperator";

function utcDate(offsetDays = 0) {
  const value = new Date();
  value.setUTCDate(value.getUTCDate() + offsetDays);
  return value.toISOString().slice(0, 10);
}

function ComparisonTable({ title, groups }: { title: string; groups: ShiftTeamComparisonGroup[] }) {
  return (
    <section className="bg-white rounded-lg border p-5 space-y-3">
      <h2 className="font-semibold text-gray-900">{title}</h2>
      {!groups.length ? (
        <p className="text-sm text-gray-500">No recorded facts for this period.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-left text-xs text-gray-500 border-b">
              <tr>
                <th className="py-2 pr-4">Group</th>
                <th className="py-2 pr-4">Approved labor</th>
                <th className="py-2 pr-4">Unapproved logs</th>
                <th className="py-2 pr-4">Recorded runtime</th>
                <th className="py-2 pr-4">Completed output allocation</th>
                <th className="py-2">Source records</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {groups.map((group) => (
                <tr key={`${group.group_id ?? "unassigned"}-${group.group_code}`} className="align-top">
                  <td className="py-3 pr-4">
                    <div className="font-medium text-gray-900">{group.group_name}</div>
                    <div className="font-mono text-xs text-gray-500">{group.group_code}</div>
                  </td>
                  <td className="py-3 pr-4">
                    {group.approved_labor_hours.toFixed(2)} h
                    <div className="text-xs text-gray-500">{group.approved_labor_log_count} logs</div>
                  </td>
                  <td className="py-3 pr-4">{group.unapproved_labor_log_count}</td>
                  <td className="py-3 pr-4">
                    {group.recorded_runtime_minutes.toFixed(1)} min
                    <div className="text-xs text-gray-500">{group.runtime_log_count} logs</div>
                    {group.runtime_by_activity.map((activity) => (
                      <div key={activity.activity_type} className="text-xs text-gray-500">
                        {activity.activity_type}: {activity.duration_minutes.toFixed(1)} min
                      </div>
                    ))}
                    {!!group.unavailable_runtime_log_ids.length && (
                      <div className="text-xs text-amber-700">{group.unavailable_runtime_log_ids.length} open/invalid intervals unavailable</div>
                    )}
                  </td>
                  <td className="py-3 pr-4">
                    {group.output_by_uom.length ? group.output_by_uom.map((output) => (
                      <div key={output.uom}>
                        {output.allocated_output_quantity.toLocaleString()} {output.uom}
                        <div className="text-xs text-gray-500">allocated from {output.labor_minutes_for_completed_orders.toFixed(1)} approved labor min</div>
                      </div>
                    )) : <span className="text-gray-400">Unavailable / no attributable completed output</span>}
                  </td>
                  <td className="py-3">
                    <details>
                      <summary className="cursor-pointer text-indigo-700">View IDs</summary>
                      <div className="mt-2 max-w-sm space-y-1 break-all text-[11px] text-gray-500">
                        <div>Labor: {group.source_labor_log_ids.join(", ") || "none"}</div>
                        <div>Runtime: {group.source_runtime_log_ids.join(", ") || "none"}</div>
                        {group.output_by_uom.map((output) => (
                          <div key={`${output.uom}-orders`}>
                            {output.uom} work orders: {output.source_work_order_ids.join(", ") || "none"}
                            <br />Output labor logs: {output.source_labor_log_ids.join(", ") || "none"}
                            <br />Allocation denominator logs: {output.allocation_labor_log_ids.join(", ") || "none"}
                          </div>
                        ))}
                      </div>
                    </details>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default function TeamsPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState<ProductionTeam | null>(null);
  const [form, setForm] = useState({ team_code: "", team_name: "", notes: "" });
  const [addMemberForm, setAddMemberForm] = useState({ operator_id: "", role_in_team: "" });
  const [dateFrom, setDateFrom] = useState(() => utcDate(-29));
  const [dateTo, setDateTo] = useState(() => utcDate());

  const { data: teams } = useQuery<ProductionTeam[]>({
    queryKey: ["mo-teams"],
    queryFn: () => moApi.listTeams(),
  });

  const { data: operators } = useQuery<OperatorProfile[]>({
    queryKey: ["mo-operators"],
    queryFn: () => moApi.listOperators(),
  });

  const { data: comparisons, isLoading: comparisonsLoading, error: comparisonsError } = useQuery({
    queryKey: ["mo-shift-team-comparisons", dateFrom, dateTo],
    queryFn: () => moApi.getShiftTeamComparisons({ date_from: dateFrom, date_to: dateTo }),
  });

  const createTeam = useMutation({
    mutationFn: () => moApi.createTeam(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mo-teams"] });
      qc.invalidateQueries({ queryKey: ["mo-dashboard"] });
      setShowCreate(false);
    },
  });

  const addMember = useMutation({
    mutationFn: () => moApi.addTeamMember(selectedTeam!.id, addMemberForm),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mo-teams"] });
      setAddMemberForm({ operator_id: "", role_in_team: "" });
    },
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a href="/dashboard/machine-ops" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
          <h1 className="text-xl font-bold text-gray-900">Production Teams</h1>
        </div>
        <button onClick={() => setShowCreate(true)} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">+ Add Team</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {(teams || []).map((t) => (
          <div
            key={t.id}
            onClick={() => setSelectedTeam(selectedTeam?.id === t.id ? null : t)}
            className={`bg-white rounded-lg border p-4 cursor-pointer hover:border-indigo-300 ${selectedTeam?.id === t.id ? "border-indigo-500 bg-indigo-50" : ""}`}
          >
            <div className="flex justify-between items-start">
              <div>
                <p className="font-semibold text-gray-900">{t.team_name}</p>
                <p className="text-xs text-gray-500 font-mono">{t.team_code}</p>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full ${t.active_flag ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                {t.active_flag ? "Active" : "Inactive"}
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-2">{t.member_count ?? 0} members</p>
          </div>
        ))}
        {!(teams?.length) && <p className="col-span-3 text-sm text-gray-400 py-4">No teams configured yet.</p>}
      </div>

      <section className="space-y-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Shift &amp; team comparisons</h2>
            <p className="text-xs text-gray-500">Calculated from recorded production, labor and runtime facts; missing assignments stay unassigned.</p>
          </div>
          <div className="flex gap-3">
            <label className="text-xs text-gray-600">From
              <input type="date" value={dateFrom} max={dateTo} onChange={(event) => setDateFrom(event.target.value)} className="ml-2 rounded border px-2 py-1 text-sm" />
            </label>
            <label className="text-xs text-gray-600">To
              <input type="date" value={dateTo} min={dateFrom} onChange={(event) => setDateTo(event.target.value)} className="ml-2 rounded border px-2 py-1 text-sm" />
            </label>
          </div>
        </div>
        {comparisonsLoading && <p className="text-sm text-gray-500">Loading recorded comparisons…</p>}
        {comparisonsError && <p role="alert" className="text-sm text-red-700">Could not load comparisons. Check the selected date range and your production view access.</p>}
        {comparisons && (
          <>
            <div className="flex flex-wrap gap-4 text-xs text-gray-500">
              <span>UTC period: {comparisons.period_start} through {comparisons.period_end}</span>
              <span>{comparisons.unavailable_output_work_order_ids.length} completed work orders lack a usable output basis</span>
            </div>
            <ComparisonTable title="By team" groups={comparisons.teams} />
            <ComparisonTable title="By shift" groups={comparisons.shifts} />
            <details className="rounded-lg border bg-white p-4 text-xs text-gray-600">
              <summary className="cursor-pointer font-medium">Calculation and data notes</summary>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {comparisons.data_notes.map((note) => <li key={note}>{note}</li>)}
              </ul>
              {!!comparisons.unavailable_output_work_order_ids.length && (
                <p className="mt-2 break-all">Unavailable work-order IDs: {comparisons.unavailable_output_work_order_ids.join(", ")}</p>
              )}
            </details>
          </>
        )}
      </section>

      {selectedTeam && (
        <div className="bg-white rounded-lg border p-5 space-y-4">
          <div className="flex justify-between">
            <h2 className="font-semibold text-gray-900">Team: {selectedTeam.team_name}</h2>
            <button onClick={() => setSelectedTeam(null)} className="text-xs text-gray-400 hover:text-gray-600">✕</button>
          </div>
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">Add Operator</label>
              <select value={addMemberForm.operator_id} onChange={(e) => setAddMemberForm((p) => ({ ...p, operator_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">— select operator —</option>
                {(operators || []).map((op) => <option key={op.id} value={op.id}>{op.operator_code} — {op.full_name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Role</label>
              <input value={addMemberForm.role_in_team} onChange={(e) => setAddMemberForm((p) => ({ ...p, role_in_team: e.target.value }))} className="border rounded px-3 py-2 text-sm" placeholder="Operator / Lead" />
            </div>
            <button onClick={() => addMember.mutate()} disabled={!addMemberForm.operator_id} className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700 disabled:opacity-50">Add</button>
          </div>
        </div>
      )}

      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-96 space-y-4">
            <h2 className="font-bold text-gray-900">Create Production Team</h2>
            {[
              { label: "Team Code *", field: "team_code", placeholder: "TEAM-A" },
              { label: "Team Name *", field: "team_name", placeholder: "Morning Shift A" },
            ].map(({ label, field, placeholder }) => (
              <div key={field}>
                <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
                <input value={(form as Record<string, string>)[field]} onChange={(e) => setForm((p) => ({ ...p, [field]: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" placeholder={placeholder} />
              </div>
            ))}
            <div className="flex gap-2 justify-end pt-2">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-600 border rounded-lg hover:bg-gray-50">Cancel</button>
              <button onClick={() => createTeam.mutate()} disabled={!form.team_code || !form.team_name} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {createTeam.isPending ? "Saving…" : "Create Team"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
