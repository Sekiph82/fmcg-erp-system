"use client";
import { useEffect, useState } from "react";
import {
  trainingApi, TrainingAssignment, TrainingProgram, TrainingSession, AssignmentStatus,
  ASSIGNMENT_STATUS_COLOR,
} from "@/lib/training";

const STATUSES: AssignmentStatus[] = ["assigned","in_progress","completed","overdue","waived"];

export default function AssignmentsPage() {
  const [assignments, setAssignments] = useState<TrainingAssignment[]>([]);
  const [programs, setPrograms] = useState<TrainingProgram[]>([]);
  const [sessions, setSessions] = useState<TrainingSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [empFilter, setEmpFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    employee_id: "", employee_name: "", department_id: "",
    training_id: "", session_id: "", assigned_by: "", due_date: "", notes: "",
  });
  const [completing, setCompleting] = useState<string | null>(null);
  const [completeForm, setCompleteForm] = useState({ completion_date: "", score: "", notes: "" });

  const load = () =>
    Promise.all([
      trainingApi.listAssignments({ status: statusFilter || undefined, employee_id: empFilter || undefined }),
      trainingApi.listPrograms(),
      trainingApi.listSessions(),
    ]).then(([a, p, s]) => { setAssignments(a); setPrograms(p); setSessions(s); }).finally(() => setLoading(false));
  useEffect(() => { load(); }, [statusFilter, empFilter]);

  const submit = async () => {
    await trainingApi.createAssignment({
      ...form,
      session_id: form.session_id || undefined,
      assigned_by: form.assigned_by || undefined,
      due_date: form.due_date || undefined,
      notes: form.notes || undefined,
    });
    setShowForm(false);
    load();
  };

  const completeAssignment = async () => {
    if (!completing) return;
    await trainingApi.completeAssignment(completing, {
      completion_date: completeForm.completion_date || undefined,
      score: completeForm.score ? Number(completeForm.score) : undefined,
      notes: completeForm.notes || undefined,
    });
    setCompleting(null);
    load();
  };

  const markOverdue = async () => {
    const result = await trainingApi.markOverdue();
    alert(`Marked ${result.marked_overdue} assignments as overdue.`);
    load();
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-xl font-bold text-gray-900">Training Assignments</h1>
        <div className="flex gap-2">
          <button onClick={markOverdue} className="rounded border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50">
            Mark Overdue
          </button>
          <button onClick={() => setShowForm(true)} className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            + Assign Training
          </button>
        </div>
      </div>

      <div className="flex gap-3 flex-wrap">
        <select className="border rounded px-2 py-1 text-sm" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All Statuses</option>
          {STATUSES.map(s => <option key={s} value={s}>{s.replace(/_/g," ")}</option>)}
        </select>
        <input className="border rounded px-2 py-1 text-sm w-40" placeholder="Employee ID…"
          value={empFilter} onChange={(e) => setEmpFilter(e.target.value)} />
      </div>

      {showForm && (
        <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
          <h2 className="font-semibold text-gray-800">Assign Training</h2>
          <div className="grid grid-cols-2 gap-3">
            {(["employee_id","employee_name","department_id","assigned_by"] as const).map((f) => (
              <div key={f}>
                <label className="text-xs text-gray-500 capitalize">{f.replace(/_/g," ")}</label>
                <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={form[f]}
                  onChange={(e) => setForm({ ...form, [f]: e.target.value })} />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500">Training Program *</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.training_id}
                onChange={(e) => setForm({ ...form, training_id: e.target.value })}>
                <option value="">Select…</option>
                {programs.map(p => <option key={p.training_id} value={p.training_id}>{p.training_name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Session (optional)</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.session_id}
                onChange={(e) => setForm({ ...form, session_id: e.target.value })}>
                <option value="">No specific session</option>
                {sessions.filter(s => s.status === "planned").map(s => (
                  <option key={s.session_id} value={s.session_id}>{s.training_name} — {s.session_date}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Due Date</label>
              <input type="date" className="w-full border rounded px-2 py-1 text-sm mt-1"
                value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={submit} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">Assign</button>
            <button onClick={() => setShowForm(false)} className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Employee","Training","Dept","Assigned By","Due","Status","Score","Actions"].map(h=>(
                  <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {assignments.map(a => (
                <tr key={a.assignment_id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium text-gray-800">{a.employee_name ?? a.employee_id}</td>
                  <td className="px-3 py-2 text-gray-700">{a.training_name ?? a.training_id}</td>
                  <td className="px-3 py-2 text-gray-500">{a.department_id ?? "—"}</td>
                  <td className="px-3 py-2 text-gray-500">{a.assigned_by ?? "—"}</td>
                  <td className="px-3 py-2 text-gray-500">{a.due_date ?? "—"}</td>
                  <td className="px-3 py-2">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${ASSIGNMENT_STATUS_COLOR[a.status]}`}>
                      {a.status.replace(/_/g," ")}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">{a.score ?? "—"}</td>
                  <td className="px-3 py-2">
                    {(a.status === "assigned" || a.status === "in_progress") && (
                      <button
                        onClick={() => { setCompleting(a.assignment_id); setCompleteForm({ completion_date: "", score: "", notes: "" }); }}
                        className="text-xs text-green-600 hover:underline"
                      >
                        Complete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {assignments.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">No assignments found.</p>}
        </div>
      )}

      {completing && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-sm p-6 space-y-3">
            <h2 className="font-bold text-gray-900">Mark Complete</h2>
            <div>
              <label className="text-xs text-gray-500">Completion Date</label>
              <input type="date" className="w-full border rounded px-2 py-1 text-sm mt-1"
                value={completeForm.completion_date} onChange={(e) => setCompleteForm({ ...completeForm, completion_date: e.target.value })} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Score (0–100)</label>
              <input type="number" min={0} max={100} className="w-full border rounded px-2 py-1 text-sm mt-1"
                value={completeForm.score} onChange={(e) => setCompleteForm({ ...completeForm, score: e.target.value })} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Notes</label>
              <textarea className="w-full border rounded px-2 py-1 text-sm mt-1" rows={2}
                value={completeForm.notes} onChange={(e) => setCompleteForm({ ...completeForm, notes: e.target.value })} />
            </div>
            <div className="flex gap-2">
              <button onClick={completeAssignment} className="rounded bg-green-600 px-4 py-1.5 text-sm text-white hover:bg-green-700">Mark Complete</button>
              <button onClick={() => setCompleting(null)} className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
