"use client";
import { useEffect, useState } from "react";
import { qmsApi, CorrectiveAction, RISK_BG, STATUS_BG, CorrectiveActionStatus, RiskLevel } from "@/lib/qms";

export default function CorrectiveActionsPage() {
  const [cas, setCAs] = useState<CorrectiveAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<CorrectiveAction | null>(null);
  const [statusFilter, setStatusFilter] = useState<CorrectiveActionStatus | "">("");
  const [showNew, setShowNew] = useState(false);
  const [verifyText, setVerifyText] = useState("");
  const [form, setForm] = useState<Record<string, unknown>>({
    title: "", description: "", severity: "MEDIUM",
    steps: [],
  });
  const [stepsText, setStepsText] = useState("");

  const load = () => {
    setLoading(true);
    qmsApi.listCAs({ status: statusFilter || undefined }).then(setCAs).finally(() => setLoading(false));
  };

  useEffect(load, [statusFilter]);

  const handleCreate = async () => {
    const steps = stepsText.split("\n").filter(s => s.trim()).map((s, i) => ({
      step_no: i + 1, step_description: s.trim(),
    }));
    await qmsApi.createCA({ ...form, steps });
    setShowNew(false);
    setForm({ title: "", description: "", severity: "MEDIUM", steps: [] });
    setStepsText("");
    load();
  };

  const handleUpdateStatus = async (id: string, status: CorrectiveActionStatus) => {
    await qmsApi.updateCA(id, { status });
    load();
    if (selected?.id === id) {
      const updated = await qmsApi.getCA(id);
      setSelected(updated);
    }
  };

  const handleVerify = async () => {
    if (!selected) return;
    await qmsApi.verifyCA(selected.id, verifyText);
    setVerifyText("");
    load();
    const updated = await qmsApi.getCA(selected.id);
    setSelected(updated);
  };

  const handleCompleteStep = async (ca_id: string, step_id: string) => {
    await qmsApi.completeStep(ca_id, step_id);
    if (selected?.id === ca_id) {
      const updated = await qmsApi.getCA(ca_id);
      setSelected(updated);
    }
    load();
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Corrective Action Tracker</h1>
          <p className="text-sm text-gray-500 mt-0.5">Track and verify corrective actions for QC and CCP failures</p>
        </div>
        <button onClick={() => setShowNew(true)}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700">
          + New Corrective Action
        </button>
      </div>

      <div className="flex gap-3">
        <select className="border rounded-lg px-3 py-2 text-sm text-gray-700 bg-white"
          value={statusFilter} onChange={e => setStatusFilter(e.target.value as CorrectiveActionStatus | "")}>
          <option value="">All Statuses</option>
          <option value="OPEN">Open</option>
          <option value="IN_PROGRESS">In Progress</option>
          <option value="COMPLETED">Completed</option>
          <option value="VERIFIED">Verified</option>
          <option value="OVERDUE">Overdue</option>
        </select>
      </div>

      {showNew && (
        <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
          <h3 className="font-semibold text-gray-800">Create Corrective Action</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="text-xs text-gray-500 block mb-1">Title *</label>
              <input className="border rounded-lg px-3 py-2 text-sm w-full"
                value={form.title as string}
                onChange={e => setForm(p => ({ ...p, title: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Severity</label>
              <select className="border rounded-lg px-3 py-2 text-sm w-full"
                value={form.severity as string}
                onChange={e => setForm(p => ({ ...p, severity: e.target.value }))}>
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Due Date</label>
              <input type="date" className="border rounded-lg px-3 py-2 text-sm w-full"
                value={(form.due_date as string) || ""}
                onChange={e => setForm(p => ({ ...p, due_date: e.target.value }))} />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-500 block mb-1">Description *</label>
              <textarea className="border rounded-lg px-3 py-2 text-sm w-full" rows={2}
                value={form.description as string}
                onChange={e => setForm(p => ({ ...p, description: e.target.value }))} />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-500 block mb-1">
                Action Steps (one per line)
              </label>
              <textarea className="border rounded-lg px-3 py-2 text-sm w-full font-mono" rows={5}
                placeholder="1. Stop affected production line&#10;2. Quarantine affected lot&#10;3. Investigate root cause&#10;4. Implement fix&#10;5. Re-test and verify"
                value={stepsText}
                onChange={e => setStepsText(e.target.value)} />
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={handleCreate}
              className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700">
              Create
            </button>
            <button onClick={() => setShowNew(false)}
              className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200">
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* CA List */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {loading ? (
            <p className="px-5 py-8 text-gray-400 text-sm">Loading…</p>
          ) : cas.length === 0 ? (
            <p className="px-5 py-8 text-gray-400 text-sm">No corrective actions found</p>
          ) : (
            <div className="divide-y divide-gray-100">
              {cas.map(ca => (
                <div key={ca.id}
                  className={`px-5 py-4 hover:bg-gray-50 cursor-pointer ${selected?.id === ca.id ? "bg-indigo-50" : ""}`}
                  onClick={() => setSelected(selected?.id === ca.id ? null : ca)}>
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-medium text-gray-800 text-sm">{ca.ca_no}</span>
                      <p className="text-xs text-gray-600 mt-0.5">{ca.title}</p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span className={`px-2 py-0.5 rounded text-xs ${STATUS_BG[ca.status] || "bg-gray-100"}`}>
                        {ca.status.replace("_", " ")}
                      </span>
                      <span className={`px-1.5 py-0.5 rounded text-xs ${RISK_BG[ca.severity]}`}>
                        {ca.severity}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                    <span>{ca.trigger_type?.replace("_", " ") || "Manual"}</span>
                    {ca.assigned_to_name && <span>→ {ca.assigned_to_name}</span>}
                    {ca.due_date && (
                      <span className={new Date(ca.due_date) < new Date() && ca.status !== "COMPLETED" && ca.status !== "VERIFIED"
                        ? "text-red-600 font-medium" : ""}>
                        Due: {new Date(ca.due_date).toLocaleDateString()}
                      </span>
                    )}
                    <span className="ml-auto">{ca.steps_completed}/{ca.steps_total} steps</span>
                  </div>
                  <div className="mt-2 bg-gray-200 rounded-full h-1.5 w-full">
                    <div
                      className="bg-indigo-500 h-1.5 rounded-full"
                      style={{ width: ca.steps_total ? `${(ca.steps_completed / ca.steps_total) * 100}%` : "0%" }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* CA Detail */}
        {selected && (
          <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-gray-800">{selected.ca_no} — {selected.title}</h3>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <p className="text-sm text-gray-600">{selected.description}</p>

            {/* Status actions */}
            <div className="flex gap-2 flex-wrap">
              {selected.status === "OPEN" && (
                <button onClick={() => handleUpdateStatus(selected.id, "IN_PROGRESS")}
                  className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                  Start
                </button>
              )}
              {selected.status === "IN_PROGRESS" && selected.steps_completed === selected.steps_total && (
                <button onClick={() => handleUpdateStatus(selected.id, "COMPLETED")}
                  className="text-xs px-3 py-1.5 bg-green-600 text-white rounded-lg hover:bg-green-700">
                  Mark Completed
                </button>
              )}
            </div>

            {/* Steps */}
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Action Steps</h4>
              {(selected.steps || []).length === 0 ? (
                <p className="text-xs text-gray-400">No steps defined</p>
              ) : (
                <div className="space-y-2">
                  {selected.steps.map(step => (
                    <div key={step.id} className={`flex items-start gap-3 p-3 rounded-lg border ${step.is_completed ? "bg-green-50 border-green-200" : "bg-gray-50 border-gray-200"}`}>
                      <input type="checkbox" checked={step.is_completed} disabled={step.is_completed}
                        onChange={() => !step.is_completed && handleCompleteStep(selected.id, step.id)}
                        className="mt-0.5 cursor-pointer" />
                      <div>
                        <p className={`text-sm ${step.is_completed ? "line-through text-gray-400" : "text-gray-700"}`}>
                          {step.step_no}. {step.step_description}
                        </p>
                        {step.is_completed && step.completed_at && (
                          <p className="text-xs text-gray-400 mt-0.5">
                            Completed {new Date(step.completed_at).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Verify */}
            {selected.status === "COMPLETED" && (
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Effectiveness Check</h4>
                <textarea className="border rounded-lg px-3 py-2 text-sm w-full" rows={2}
                  placeholder="Describe how effectiveness was verified…"
                  value={verifyText} onChange={e => setVerifyText(e.target.value)} />
                <button onClick={handleVerify}
                  className="px-4 py-2 bg-teal-600 text-white text-sm rounded-lg hover:bg-teal-700">
                  Verify & Close
                </button>
              </div>
            )}

            {selected.effectiveness_check && (
              <div className="bg-teal-50 border border-teal-200 rounded-lg p-3">
                <p className="text-xs font-semibold text-teal-700 mb-1">Effectiveness Verified</p>
                <p className="text-sm text-teal-800">{selected.effectiveness_check}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
