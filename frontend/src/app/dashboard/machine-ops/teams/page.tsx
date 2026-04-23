"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { moApi, ProductionTeam, OperatorProfile } from "@/lib/machineOperator";

export default function TeamsPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState<ProductionTeam | null>(null);
  const [form, setForm] = useState({ team_code: "", team_name: "", notes: "" });
  const [addMemberForm, setAddMemberForm] = useState({ operator_id: "", role_in_team: "" });

  const { data: teams } = useQuery<ProductionTeam[]>({
    queryKey: ["mo-teams"],
    queryFn: () => moApi.listTeams().then((r) => r.data),
  });

  const { data: operators } = useQuery<OperatorProfile[]>({
    queryKey: ["mo-operators"],
    queryFn: () => moApi.listOperators().then((r) => r.data),
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
