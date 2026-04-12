"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { hrApi, Employee, EmployeeStatus } from "@/lib/hr";
import { ImportModal } from "@/components/import/ImportModal";
import { RequirePermission } from "@/components/PermissionGuard";
import { Badge } from "@/components/ui/Badge";

const STATUS_VARIANT: Record<EmployeeStatus, "green" | "gray" | "yellow" | "red"> = {
  ACTIVE: "green",
  INACTIVE: "gray",
  ON_LEAVE: "yellow",
  TERMINATED: "red",
};

function EmployeeForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: Partial<Employee>;
  onSave: (data: Record<string, unknown>) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState({
    employee_code: initial?.employee_code ?? "",
    full_name: initial?.full_name ?? "",
    department: initial?.department ?? "",
    role: initial?.role ?? "",
    phone: initial?.phone ?? "",
    email: initial?.email ?? "",
    hire_date: initial?.hire_date ?? "",
    status: initial?.status ?? "ACTIVE",
    salary_grade: initial?.salary_grade ?? "",
    payment_method: initial?.payment_method ?? "",
    mpesa_number: initial?.mpesa_number ?? "",
    bank_account: initial?.bank_account ?? "",
  });

  const field = (key: string) => ({
    value: (form as Record<string, string>)[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value })),
  });

  return (
    <div className="bg-white border rounded-lg p-6 space-y-4">
      <h3 className="font-semibold text-gray-800">{initial?.id ? "Edit Employee" : "New Employee"}</h3>
      <div className="grid grid-cols-2 gap-4">
        {[
          ["employee_code", "Employee Code"],
          ["full_name", "Full Name"],
          ["department", "Department"],
          ["role", "Role / Job Title"],
          ["phone", "Phone"],
          ["email", "Email"],
          ["hire_date", "Hire Date"],
          ["salary_grade", "Salary Grade"],
          ["mpesa_number", "M-Pesa Number"],
          ["bank_account", "Bank Account"],
        ].map(([key, label]) => (
          <div key={key}>
            <label className="block text-xs text-gray-500 mb-1">{label}</label>
            <input
              type={key === "hire_date" ? "date" : "text"}
              className="w-full border rounded px-3 py-2 text-sm"
              {...field(key)}
            />
          </div>
        ))}
        <div>
          <label className="block text-xs text-gray-500 mb-1">Status</label>
          <select className="w-full border rounded px-3 py-2 text-sm" {...field("status")}>
            {["ACTIVE", "INACTIVE", "ON_LEAVE", "TERMINATED"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Payment Method</label>
          <select className="w-full border rounded px-3 py-2 text-sm" {...field("payment_method")}>
            <option value="">— none —</option>
            {["MPESA", "BANK", "CASH"].map((m) => (
              <option key={m}>{m}</option>
            ))}
          </select>
        </div>
      </div>
      <div className="flex gap-3 pt-2">
        <button
          onClick={() => onSave(Object.fromEntries(Object.entries(form).filter(([, v]) => v !== "")))}
          className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700"
        >
          Save
        </button>
        <button onClick={onCancel} className="px-4 py-2 border rounded text-sm hover:bg-gray-50">
          Cancel
        </button>
      </div>
    </div>
  );
}

function EmployeesContent() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [dept, setDept] = useState("");
  const [status, setStatus] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Employee | null>(null);

  const { data: employees = [], isLoading } = useQuery({
    queryKey: ["hr-employees", dept, status, search],
    queryFn: () => hrApi.listEmployees({ department: dept || undefined, status: status || undefined, search: search || undefined }),
  });

  const createMutation = useMutation({
    mutationFn: hrApi.createEmployee,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["hr-employees"] }); setShowForm(false); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) => hrApi.updateEmployee(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["hr-employees"] }); setEditing(null); },
  });

  const departments = Array.from(new Set(employees.map((e) => e.department))).sort();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Employees</h1>
          <p className="text-sm text-gray-500 mt-1">{employees.length} records</p>
        </div>
        <div className="flex items-center gap-2">
          <ImportModal module="employees" onSuccess={() => qc.invalidateQueries({ queryKey: ["hr-employees"] })} />
          <button
            onClick={() => setShowForm(true)}
            className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700"
          >
            + New Employee
          </button>
        </div>
      </div>

      {(showForm || editing) && (
        <EmployeeForm
          initial={editing ?? undefined}
          onSave={(data) => {
            if (editing) {
              updateMutation.mutate({ id: editing.id, data });
            } else {
              createMutation.mutate(data);
            }
          }}
          onCancel={() => { setShowForm(false); setEditing(null); }}
        />
      )}

      <div className="flex gap-3">
        <input
          placeholder="Search name or code..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border rounded px-3 py-2 text-sm w-56"
        />
        <select value={dept} onChange={(e) => setDept(e.target.value)} className="border rounded px-3 py-2 text-sm">
          <option value="">All Departments</option>
          {departments.map((d) => <option key={d}>{d}</option>)}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)} className="border rounded px-3 py-2 text-sm">
          <option value="">All Statuses</option>
          {["ACTIVE", "INACTIVE", "ON_LEAVE", "TERMINATED"].map((s) => <option key={s}>{s}</option>)}
        </select>
      </div>

      <div className="bg-white border rounded-lg overflow-hidden">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-400 text-center">Loading...</p>
        ) : employees.length === 0 ? (
          <p className="p-6 text-sm text-gray-400 text-center">No employees found</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-4 py-2 text-left">Code</th>
                <th className="px-4 py-2 text-left">Name</th>
                <th className="px-4 py-2 text-left">Department</th>
                <th className="px-4 py-2 text-left">Role</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {employees.map((emp) => (
                <tr key={emp.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-gray-600">{emp.employee_code}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{emp.full_name}</td>
                  <td className="px-4 py-3 text-gray-600">{emp.department}</td>
                  <td className="px-4 py-3 text-gray-600">{emp.role}</td>
                  <td className="px-4 py-3">
                    <Badge label={emp.status} variant={STATUS_VARIANT[emp.status]} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => setEditing(emp as unknown as Employee)}
                      className="text-xs text-indigo-600 hover:underline"
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default function EmployeesPage() {
  return (
    <RequirePermission permission="hr.view">
      <EmployeesContent />
    </RequirePermission>
  );
}
