"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { hrApi, ShiftTemplate, ShiftAssignment } from "@/lib/hr";
import { RequirePermission } from "@/components/PermissionGuard";
import { tx } from "@/lib/i18n/core";

function ShiftTemplateForm({ onSave, onCancel }: { onSave: (d: Record<string, unknown>) => void; onCancel: () => void }) {
  const [form, setForm] = useState({ name: "", start_time: "06:00", end_time: "14:00", department: "", notes: "" });
  const f = (k: string) => ({
    value: (form as Record<string, string>)[k],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm((p) => ({ ...p, [k]: e.target.value })),
  });
  return (
    <div className="bg-white border rounded-lg p-4 space-y-3">
      <h3 className="font-semibold text-sm text-gray-800">{tx("New Shift Template")}</h3>
      <div className="grid grid-cols-2 gap-3">
        <div><label className="text-xs text-gray-500">{tx("Name")}</label><input className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("name")} /></div>
        <div><label className="text-xs text-gray-500">{tx("Department (optional)")}</label><input className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("department")} /></div>
        <div><label className="text-xs text-gray-500">{tx("Start Time")}</label><input type="time" className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("start_time")} /></div>
        <div><label className="text-xs text-gray-500">{tx("End Time")}</label><input type="time" className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("end_time")} /></div>
      </div>
      <div><label className="text-xs text-gray-500">{tx("Notes")}</label><textarea className="w-full border rounded px-2 py-1.5 text-sm mt-1" rows={2} {...f("notes")} /></div>
      <div className="flex gap-2">
        <button onClick={() => onSave(Object.fromEntries(Object.entries(form).filter(([, v]) => v !== "")))} className="px-3 py-1.5 bg-indigo-600 text-white rounded text-sm">{tx("Save")}</button>
        <button onClick={onCancel} className="px-3 py-1.5 border rounded text-sm">{tx("Cancel")}</button>
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
      <h3 className="font-semibold text-sm text-gray-800">{tx("Assign Shift")}</h3>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-gray-500">{tx("Employee")}</label>
          <select className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("employee_id")}>
            <option value="">{tx("— select —")}</option>
            {employees.map((e) => <option key={e.id} value={e.id}>{e.full_name} ({e.department})</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500">{tx("Shift Template")}</label>
          <select className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("shift_template_id")}>
            <option value="">{tx("— select —")}</option>
            {templates.map((t) => <option key={t.id} value={t.id}>{t.name} ({t.start_time} – {t.end_time})</option>)}
          </select>
        </div>
        <div><label className="text-xs text-gray-500">{tx("Effective From")}</label><input type="date" className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("effective_from")} /></div>
        <div><label className="text-xs text-gray-500">{tx("Effective To (optional)")}</label><input type="date" className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("effective_to")} /></div>
        <div>
          <label className="text-xs text-gray-500">{tx("Supervisor (optional)")}</label>
          <select className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("supervisor_id")}>
            <option value="">{tx("— none —")}</option>
            {employees.map((e) => <option key={e.id} value={e.id}>{e.full_name}</option>)}
          </select>
        </div>
      </div>
      <div className="flex gap-2">
        <button onClick={() => onSave(Object.fromEntries(Object.entries(form).filter(([, v]) => v !== "")))} className="px-3 py-1.5 bg-indigo-600 text-white rounded text-sm">{tx("Assign")}</button>
        <button onClick={onCancel} className="px-3 py-1.5 border rounded text-sm">{tx("Cancel")}</button>
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
          <h1 className="text-2xl font-bold text-gray-900">{tx("Shift Planning")}</h1>
          <p className="text-sm text-gray-500 mt-1">{tx("Active assignments as of today")}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowTmpl(true)} className="px-3 py-2 border rounded text-sm hover:bg-gray-50">{tx("+ Template")}</button>
          <button onClick={() => setShowAssign(true)} className="px-3 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">{tx("+ Assign Shift")}</button>
        </div>
      </div>

      {showTmpl && <ShiftTemplateForm onSave={(d) => createTemplate.mutate(d)} onCancel={() => setShowTmpl(false)} />}
      {showAssign && <AssignmentForm employees={employees} templates={templates.filter((t) => t.is_active)} onSave={(d) => createAssignment.mutate(d)} onCancel={() => setShowAssign(false)} />}

      {/* Templates */}
      <div className="bg-white border rounded-lg">
        <div className="px-4 py-3 border-b"><h2 className="font-semibold text-gray-800 text-sm">{tx("Shift Templates")}</h2></div>
        {templates.length === 0 ? (
          <p className="p-6 text-sm text-gray-400 text-center">{tx("No templates defined")}</p>
        ) : (
          <table className="w-full text-sm">
            <thead><tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase"><th className="px-4 py-2 text-left">{tx("Name")}</th><th className="px-4 py-2 text-left">{tx("Hours")}</th><th className="px-4 py-2 text-left">{tx("Department")}</th><th className="px-4 py-2 text-left">{tx("Active")}</th></tr></thead>
            <tbody className="divide-y">
              {templates.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{t.name}</td>
                  <td className="px-4 py-3 text-gray-600">{t.start_time} – {t.end_time}</td>
                  <td className="px-4 py-3 text-gray-600">{t.department ?? tx("All")}</td>
                  <td className="px-4 py-3">{t.is_active ? <span className="text-green-600 text-xs font-medium">{tx("Yes")}</span> : <span className="text-gray-400 text-xs">{tx("No")}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Active Assignments */}
      <div className="bg-white border rounded-lg">
        <div className="px-4 py-3 border-b"><h2 className="font-semibold text-gray-800 text-sm">{tx("Active Assignments")}</h2></div>
        {assignments.length === 0 ? (
          <p className="p-6 text-sm text-gray-400 text-center">{tx("No active assignments")}</p>
        ) : (
          <table className="w-full text-sm">
            <thead><tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase"><th className="px-4 py-2 text-left">{tx("Employee")}</th><th className="px-4 py-2 text-left">{tx("Dept")}</th><th className="px-4 py-2 text-left">{tx("Shift")}</th><th className="px-4 py-2 text-left">{tx("Hours")}</th><th className="px-4 py-2 text-left">{tx("From")}</th><th className="px-4 py-2 text-left">{tx("To")}</th></tr></thead>
            <tbody className="divide-y">
              {assignments.map((a) => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{a.employee?.full_name ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-500">{a.employee?.department ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-700">{a.shift_template?.name ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{a.shift_template ? `${a.shift_template.start_time} – ${a.shift_template.end_time}` : "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{a.effective_from}</td>
                  <td className="px-4 py-3 text-gray-600">{a.effective_to ?? tx("Open")}</td>
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
