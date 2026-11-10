"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { moApi, OperatorProductivity, OperatorProfile, SkillLevel } from "@/lib/machineOperator";

const SKILL_COLORS: Record<SkillLevel, string> = {
  TRAINEE: "bg-gray-100 text-gray-600",
  BASIC: "bg-blue-100 text-blue-700",
  INTERMEDIATE: "bg-teal-100 text-teal-700",
  ADVANCED: "bg-purple-100 text-purple-700",
  EXPERT: "bg-amber-100 text-amber-700",
};

export default function OperatorsPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [productivityOperatorId, setProductivityOperatorId] = useState<string | null>(null);
  const [form, setForm] = useState({
    operator_code: "", full_name: "", department: "",
    skill_level: "BASIC" as SkillLevel,
    labor_rate_per_hour: "", notes: "",
  });

  const { data, isLoading } = useQuery<OperatorProfile[]>({
    queryKey: ["mo-operators"],
    queryFn: () => moApi.listOperators(),
  });

  const productivityQuery = useQuery<OperatorProductivity>({
    queryKey: ["mo-operator-productivity", productivityOperatorId],
    queryFn: () => moApi.getOperatorProductivity(productivityOperatorId!),
    enabled: Boolean(productivityOperatorId),
  });

  const create = useMutation({
    mutationFn: () => moApi.createOperator({
      ...form,
      labor_rate_per_hour: form.labor_rate_per_hour ? parseFloat(form.labor_rate_per_hour) : undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mo-operators"] });
      qc.invalidateQueries({ queryKey: ["mo-dashboard"] });
      setShowCreate(false);
    },
  });

  const ops = data || [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a href="/dashboard/machine-ops" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
          <h1 className="text-xl font-bold text-gray-900">Operator Profiles</h1>
        </div>
        <div className="flex gap-2">
          <a href="/dashboard/machine-ops/certs" className="text-sm text-yellow-600 border border-yellow-200 px-3 py-2 rounded-lg hover:bg-yellow-50">Cert Monitor</a>
          <button onClick={() => setShowCreate(true)} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">+ Add Operator</button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3">
        {(["EXPERT", "ADVANCED", "INTERMEDIATE", "BASIC"] as SkillLevel[]).map((sl) => (
          <div key={sl} className="bg-white rounded-lg border p-3 text-center">
            <p className="text-xs text-gray-500">{sl}</p>
            <p className="text-2xl font-bold text-gray-800">{ops.filter((o) => o.skill_level === sl).length}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-lg border overflow-x-auto">
        {isLoading && <div className="p-6 text-gray-400 text-sm">Loading…</div>}
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>{["Code", "Name", "Department", "Skill Level", "Labor Rate", "Certs", "Expiring", "Active", "Actions"].map((h) => (
              <th key={h} className="px-4 py-2 text-left text-xs font-medium text-gray-600">{h}</th>
            ))}</tr>
          </thead>
          <tbody className="divide-y">
            {ops.map((op) => (
              <tr key={op.id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 font-mono text-xs font-medium">{op.operator_code}</td>
                <td className="px-4 py-2.5 text-sm">{op.full_name}</td>
                <td className="px-4 py-2.5 text-xs">{op.department || "—"}</td>
                <td className="px-4 py-2.5">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SKILL_COLORS[op.skill_level]}`}>{op.skill_level}</span>
                </td>
                <td className="px-4 py-2.5 text-xs">{op.labor_rate_per_hour ? `KES ${Number(op.labor_rate_per_hour).toLocaleString()}/hr` : "—"}</td>
                <td className="px-4 py-2.5 text-xs">{op.cert_count ?? "—"}</td>
                <td className="px-4 py-2.5 text-xs">
                  {op.expiring_cert_count ? <span className="text-yellow-600 font-medium">{op.expiring_cert_count}</span> : "0"}
                </td>
                <td className="px-4 py-2.5">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${op.active_flag ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {op.active_flag ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="px-4 py-2.5">
                  <a href={`/dashboard/machine-ops/certs?operator_id=${op.id}`} className="text-xs text-indigo-600 hover:underline">Certs</a>
                  <button onClick={() => setProductivityOperatorId(op.id)} className="ml-3 text-xs text-teal-700 hover:underline">KPIs</button>
                </td>
              </tr>
            ))}
            {!isLoading && !ops.length && (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400 text-sm">No operators found.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {productivityOperatorId && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-40 p-4">
          <section className="bg-white rounded-xl shadow-xl p-6 w-full max-w-3xl max-h-[85vh] overflow-y-auto space-y-4" aria-label="Operator productivity KPIs">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="font-bold text-gray-900">Operator productivity KPIs</h2>
                <p className="text-xs text-gray-500">{productivityQuery.data?.period_start} – {productivityQuery.data?.period_end}</p>
              </div>
              <button onClick={() => setProductivityOperatorId(null)} className="text-sm text-gray-500 hover:text-gray-800">Close</button>
            </div>
            {productivityQuery.isLoading && <p className="text-sm text-gray-500">Loading KPI data…</p>}
            {productivityQuery.isError && <p className="text-sm text-red-600">KPI data could not be loaded.</p>}
            {productivityQuery.data && (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="rounded border p-3"><p className="text-xs text-gray-500">Approved labor</p><p className="font-semibold">{productivityQuery.data.approved_labor_hours} h</p></div>
                  <div className="rounded border p-3"><p className="text-xs text-gray-500">Approved logs</p><p className="font-semibold">{productivityQuery.data.approved_labor_log_count}</p></div>
                  <div className="rounded border p-3"><p className="text-xs text-gray-500">Pending logs</p><p className="font-semibold">{productivityQuery.data.unapproved_labor_log_count}</p></div>
                  <div className="rounded border p-3"><p className="text-xs text-gray-500">Completed work orders</p><p className="font-semibold">{productivityQuery.data.completed_work_order_count}</p></div>
                </div>
                <div className="overflow-x-auto rounded border">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50"><tr><th className="p-2 text-left">Output UOM</th><th className="p-2 text-right">Allocated output</th><th className="p-2 text-right">Lifetime labor h (linked orders)</th><th className="p-2 text-right">Output / linked labor h</th></tr></thead>
                    <tbody>
                      {productivityQuery.data.output_by_uom.map((row) => (
                        <tr key={row.uom} className="border-t"><td className="p-2">{row.uom}</td><td className="p-2 text-right">{row.allocated_output_quantity}</td><td className="p-2 text-right">{(row.operator_labor_minutes_for_completed_orders / 60).toFixed(2)}</td><td className="p-2 text-right">{row.output_quantity_per_operator_labor_hour ?? "—"}</td></tr>
                      ))}
                      {!productivityQuery.data.output_by_uom.length && <tr><td colSpan={4} className="p-4 text-center text-gray-500">No completed work-order output can be attributed from approved labor records in this period.</td></tr>}
                    </tbody>
                  </table>
                </div>
                {productivityQuery.data.unavailable_output_work_order_ids.length > 0 && <p className="text-xs text-amber-700">{productivityQuery.data.unavailable_output_work_order_ids.length} completed work order(s) lacked a usable quantity, UOM, or approved labor basis.</p>}
                <details className="text-xs text-gray-500"><summary className="cursor-pointer">Source IDs and calculation notes</summary><div className="mt-2 space-y-3">{productivityQuery.data.output_by_uom.map((row) => <div key={row.uom}><p className="font-medium">{row.uom} — work orders: {row.source_work_order_ids.join(", ") || "none"}</p><p>Operator labor logs: {row.source_labor_log_ids.join(", ") || "none"}</p><p>Allocation labor logs: {row.allocation_labor_log_ids.join(", ") || "none"}</p></div>)}<p>Period labor logs: {productivityQuery.data.period_labor_log_ids.join(", ") || "none"}</p><ul className="list-disc pl-5 space-y-1">{productivityQuery.data.data_notes.map((note) => <li key={note}>{note}</li>)}</ul></div></details>
              </>
            )}
          </section>
        </div>
      )}

      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-[480px] space-y-4">
            <h2 className="font-bold text-gray-900">Add Operator Profile</h2>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: "Operator Code *", field: "operator_code", placeholder: "OPR-001" },
                { label: "Full Name *", field: "full_name", placeholder: "John Doe" },
                { label: "Department", field: "department", placeholder: "Filling" },
                { label: "Labor Rate (KES/hr)", field: "labor_rate_per_hour", placeholder: "350" },
              ].map(({ label, field, placeholder }) => (
                <div key={field}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
                  <input value={(form as Record<string, string>)[field]} onChange={(e) => setForm((p) => ({ ...p, [field]: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" placeholder={placeholder} />
                </div>
              ))}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Skill Level</label>
                <select value={form.skill_level} onChange={(e) => setForm((p) => ({ ...p, skill_level: e.target.value as SkillLevel }))} className="w-full border rounded px-3 py-2 text-sm">
                  {["TRAINEE", "BASIC", "INTERMEDIATE", "ADVANCED", "EXPERT"].map((s) => <option key={s}>{s}</option>)}
                </select>
              </div>
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-600 border rounded-lg hover:bg-gray-50">Cancel</button>
              <button onClick={() => create.mutate()} disabled={!form.operator_code || !form.full_name} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {create.isPending ? "Saving…" : "Add Operator"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
