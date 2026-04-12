"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { hrApi, ShiftTemplate, ShiftAssignment } from "@/lib/hr";
import { RequirePermission } from "@/components/PermissionGuard";

function ShiftTemplateForm({ onSave, onCancel }: { onSave: (d: Record<string, unknown>) => void; onCancel: () => void }) {
  const [form, setForm] = useState({ name: "", start_time: "06:00", end_time: "14:00", department: "", notes: "" });
  const f = (k: string) => ({
    value: (form as Record<string, string>)[k],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm((p) => ({ ...p, [k]: e.target.value })),
  });
  return (
    <div className="bg-white border rounded-lg p-4 space-y-3">
      <h3 className="font-semibold text-sm text-gray-800">New Shift Template</h3>
      <div className="grid grid-cols-2 gap-3">
        <div><label className="text-xs text-gray-500">Name</label><input className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("name")} /></div>
        <div><label className="text-xs text-gray-500">Department (optional)</label><input className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("department")} /></div>
        <div><label className="text-xs text-gray-500">Start Time</label><input type="time" className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("start_time")} /></div>
        <div><label className="text-xs text-gray-500">End Time</label><input type="time" className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("end_time")} /></div>
      </div>
      <div><label className="text-xs text-gray-500">Notes</label><textarea className="w-full border rounded px-2 py-1.5 text-sm mt-1" rows={2} {...f("notes")} /></div>
      <div className="flex gap-2">
        <button onClick={() => onSave(Object.fromEntries(Object.entries(form).filter(([, v]) => v !== "")))} className="px-3 py-1.5 bg-indigo-600 text-white rounded text-sm">Save</button>
        <button onClick={onCancel} className="px-3 py-1.5 border rounded text-sm">Cancel</button>
      </div>
    </div>
  );
}

function AssignmentForm({
  employees,
  templates,
  onSave,
  onCancel,
}: {
  employees: { id: string; full_name: string; department: string }[];
  templates: ShiftTemplate[];
  onSave: (d: Record<string, unknown>) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState({ employee_id: "", shift_template_id: "", effective_from: "", effective_to: "", supervisor_id: "", notes: "" });
  const f = (k: string) => ({
    value: (form as Record<string, string>)[k],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm((p) => ({ ...p, [k]: e.target.value })),
  });
  return (
    <div className="bg-white border rounded-lg p-4 space-y-3">
      <h3 className="font-semibold text-sm text-gray-800">Assign Shift</h3>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-gray-500">Employee</label>
          <select className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("employee_id")}>
            <option value="">— select —</option>
            {employees.map((e) => <option key={e.id} value={e.id}>{e.full_name} ({e.department})</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500">Shift Template</label>
          <select className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("shift_template_id")}>
            <option value="">— select —</option>
            {templates.map((t) => <option key={t.id} value={t.id}>{t.name} ({t.start_time} – {t.end_time})</option>)}
          </select>
        </div>
        <div><label className="text-xs text-gray-500">Effective From</label><input type="date" className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("effective_from")} /></div>
        <div><label className="text-xs text-gray-500">Effective To (optional)</label><input type="date" className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("effective_to")} /></div>
        <div>
          <label className="text-xs text-gray-500">Supervisor (optional)</label>
          <select className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("supervisor_id")}>
            <option value="">— none —</option>
            {employees.map((e) => <option key={e.id} value={e.id}>{e.full_name}</option>)}
          </select>
        </div>
      </div>
      <div className="flex gap-2">
        <button onClick={() => onSave(Object.fromEntries(Object.entries(form).filter(([, v]) => v !== "")))} className="px-3 py-1.5 bg-indigo-600 text-white rounded text-sm">Assign</button>
        <button onClick={onCancel} className="px-3 py-1.5 border rounded text-sm">Cancel</button>
      </div>
    </div>
  );
}

function ShiftsContent() {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [showTmpl, setShowTmpl] = useState(false);
  const [showAssign, setShowAssign] = useState(false);

  const { data: templates = [] } = useQuery({ queryKey: ["hr-shift-templates"], queryFn: () => hrApi.listShiftTemplates(false) });
  const { data: assignments = [] } = useQuery({ queryKey: ["hr-shift-assignments", today], queryFn: () => hrApi.listShiftAssignments({ as_of: today }) });
  const { data: employees = [] } = useQuery({ queryKey: ["hr-employees"], queryFn: () => hrApi.listEmployees() });

  const createTemplate = useMutation({ mutationFn: hrApi.createShiftTemplate, onSuccess: () => { qc.invalidateQueries({ queryKey: ["hr-shift-templates"] }); setShowTmpl(false); } });
  const createAssignment = useMutation({ mutationFn: hrApi.createShiftAssignment, onSuccess: () => { qc.invalidateQueries({ queryKey: ["hr-shift-assignments"] }); setShowAssign(false); } });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Shift Planning</h1>
          <p className="text-sm text-gray-500 mt-1">Active assignments as of today</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowTmpl(true)} className="px-3 py-2 border rounded text-sm hover:bg-gray-50">+ Template</button>
          <button onClick={() => setShowAssign(true)} className="px-3 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">+ Assign Shift</button>
        </div>
      </div>

      {showTmpl && <ShiftTemplateForm onSave={(d) => createTemplate.mutate(d)} onCancel={() => setShowTmpl(false)} />}
      {showAssign && <AssignmentForm employees={employees} templates={templates.filter((t) => t.is_active)} onSave={(d) => createAssignment.mutate(d)} onCancel={() => setShowAssign(false)} />}

      {/* Templates */}
      <div className="bg-white border rounded-lg">
        <div className="px-4 py-3 border-b"><h2 className="font-semibold text-gray-800 text-sm">Shift Templates</h2></div>
        {templates.length === 0 ? (
          <p className="p-6 text-sm text-gray-400 text-center">No templates defined</p>
        ) : (
          <table className="w-full text-sm">
            <thead><tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase"><th className="px-4 py-2 text-left">Name</th><th className="px-4 py-2 text-left">Hours</th><th className="px-4 py-2 text-left">Department</th><th className="px-4 py-2 text-left">Active</th></tr></thead>
            <tbody className="divide-y">
              {templates.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{t.name}</td>
                  <td className="px-4 py-3 text-gray-600">{t.start_time} – {t.end_time}</td>
                  <td className="px-4 py-3 text-gray-600">{t.department ?? "All"}</td>
                  <td className="px-4 py-3">{t.is_active ? <span className="text-green-600 text-xs font-medium">Yes</span> : <span className="text-gray-400 text-xs">No</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Active Assignments */}
      <div className="bg-white border rounded-lg">
        <div className="px-4 py-3 border-b"><h2 className="font-semibold text-gray-800 text-sm">Active Assignments</h2></div>
        {assignments.length === 0 ? (
          <p className="p-6 text-sm text-gray-400 text-center">No active assignments</p>
        ) : (
          <table className="w-full text-sm">
            <thead><tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase"><th className="px-4 py-2 text-left">Employee</th><th className="px-4 py-2 text-left">Dept</th><th className="px-4 py-2 text-left">Shift</th><th className="px-4 py-2 text-left">Hours</th><th className="px-4 py-2 text-left">From</th><th className="px-4 py-2 text-left">To</th></tr></thead>
            <tbody className="divide-y">
              {assignments.map((a) => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{a.employee?.full_name ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-500">{a.employee?.department ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-700">{a.shift_template?.name ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{a.shift_template ? `${a.shift_template.start_time} – ${a.shift_template.end_time}` : "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{a.effective_from}</td>
                  <td className="px-4 py-3 text-gray-600">{a.effective_to ?? "Open"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default function ShiftsPage() {
  return (
    <RequirePermission permission="hr.view">
      <ShiftsContent />
    </RequirePermission>
  );
}
