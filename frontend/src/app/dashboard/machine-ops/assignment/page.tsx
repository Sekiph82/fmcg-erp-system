"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { moApi, WorkOrderAssignment, AssignmentValidateResult, Machine, OperatorProfile, ProductionTeam } from "@/lib/machineOperator";

export default function AssignmentPage() {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    work_order_id: "", machine_id: "", operator_id: "",
    team_id: "", cert_override_flag: false, notes: "",
  });
  const [validation, setValidation] = useState<AssignmentValidateResult | null>(null);
  const [created, setCreated] = useState<WorkOrderAssignment | null>(null);

  const { data: machines } = useQuery<Machine[]>({ queryKey: ["mo-machines"], queryFn: () => moApi.listMachines() });
  const { data: operators } = useQuery<OperatorProfile[]>({ queryKey: ["mo-operators"], queryFn: () => moApi.listOperators() });
  const { data: teams } = useQuery<ProductionTeam[]>({ queryKey: ["mo-teams"], queryFn: () => moApi.listTeams() });

  const validate = useMutation({
    mutationFn: () => moApi.validateAssignment({
      work_order_id: form.work_order_id,
      machine_id: form.machine_id || undefined,
      operator_id: form.operator_id || undefined,
    }),
    onSuccess: (r) => setValidation(r),
  });

  const assign = useMutation({
    mutationFn: () => moApi.createAssignment({
      ...form,
      machine_id: form.machine_id || undefined,
      operator_id: form.operator_id || undefined,
      team_id: form.team_id || undefined,
    }),
    onSuccess: (r) => {
      setCreated(r);
      qc.invalidateQueries({ queryKey: ["mo-dashboard"] });
    },
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <a href="/dashboard/machine-ops" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
        <h1 className="text-xl font-bold text-gray-900">Work Order Assignment Board</h1>
      </div>

      <div className="bg-white rounded-lg border p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">Assign Machine + Operator to Work Order</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Work Order ID *</label>
            <input value={form.work_order_id} onChange={(e) => setForm((p) => ({ ...p, work_order_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" placeholder="UUID" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Machine</label>
            <select value={form.machine_id} onChange={(e) => setForm((p) => ({ ...p, machine_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">— select machine —</option>
              {(machines || []).map((m) => <option key={m.id} value={m.id}>{m.machine_code} — {m.status}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Operator</label>
            <select value={form.operator_id} onChange={(e) => setForm((p) => ({ ...p, operator_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">— select operator —</option>
              {(operators || []).map((op) => <option key={op.id} value={op.id}>{op.operator_code} — {op.full_name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Team (optional)</label>
            <select value={form.team_id} onChange={(e) => setForm((p) => ({ ...p, team_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">— no team —</option>
              {(teams || []).map((t) => <option key={t.id} value={t.id}>{t.team_name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
            <input value={form.notes} onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" placeholder="Optional" />
          </div>
        </div>

        {/* Validation Result */}
        {validation && (
          <div className={`rounded-lg p-3 text-sm ${validation.valid ? "bg-green-50 border border-green-200 text-green-800" : "bg-red-50 border border-red-200 text-red-800"}`}>
            <p className="font-medium">{validation.valid ? "✓ Assignment valid" : "✗ Assignment blocked"}</p>
            {validation.blocks.map((b, i) => <p key={i} className="text-xs mt-1">Block: {b}</p>)}
            {validation.warnings.map((w, i) => <p key={i} className="text-xs mt-1 text-yellow-700">Warning: {w}</p>)}
            {!validation.valid && (
              <label className="flex items-center gap-2 mt-2 cursor-pointer">
                <input type="checkbox" checked={form.cert_override_flag} onChange={(e) => setForm((p) => ({ ...p, cert_override_flag: e.target.checked }))} className="rounded" />
                <span className="text-xs">Override cert block (supervisor approval)</span>
              </label>
            )}
          </div>
        )}

        <div className="flex gap-2">
          <button onClick={() => validate.mutate()} disabled={!form.work_order_id || validate.isPending} className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50">
            {validate.isPending ? "Validating…" : "Validate"}
          </button>
          <button
            onClick={() => assign.mutate()}
            disabled={assign.isPending || !form.work_order_id || (!validation?.valid && !form.cert_override_flag)}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50"
          >
            {assign.isPending ? "Assigning…" : "Confirm Assignment"}
          </button>
        </div>
      </div>

      {created && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="font-semibold text-green-800">Assignment Created</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-2 text-sm text-green-700">
            <div><span className="text-xs text-gray-500">Machine</span><p>{created.machine_name || "—"}</p></div>
            <div><span className="text-xs text-gray-500">Operator</span><p>{created.operator_name || "—"}</p></div>
            <div><span className="text-xs text-gray-500">Team</span><p>{created.team_name || "—"}</p></div>
            <div><span className="text-xs text-gray-500">Cert Valid</span><p>{created.cert_validation_passed ? "Yes" : "Override"}</p></div>
          </div>
        </div>
      )}
    </div>
  );
}
