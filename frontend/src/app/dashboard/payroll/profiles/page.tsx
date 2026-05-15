"use client";

import { useState, useEffect } from "react";
import { payrollKeApi, PayrollProfile } from "@/lib/payrollKe";
import { RequirePermission } from "@/components/PermissionGuard";
import { useAuth } from "@/context/AuthContext";

export default function PayrollProfilesPage() {
  return (
    <RequirePermission permission="payroll_ke.view">
      <PayrollProfilesContent />
    </RequirePermission>
  );
}

function PayrollProfilesContent() {
  const { hasPermission } = useAuth();
  const [profiles, setProfiles] = useState<PayrollProfile[]>([]);
  const [employees, setEmployees] = useState<{ id: string; full_name: string; employee_code: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editProfile, setEditProfile] = useState<PayrollProfile | null>(null);
  const [form, setForm] = useState({
    employee_id: "",
    basic_salary: "",
    housing_allowance: "0",
    transport_allowance: "0",
    tax_pin: "",
    nhif_no: "",
    nssf_no: "",
    bank_name: "",
    bank_account_no: "",
    bank_branch: "",
    notes: "",
    is_active: true,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      setProfiles(await payrollKeApi.listProfiles());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    import("@/lib/api").then(({ apiClient }) => {
      apiClient.get("/api/v1/hr/employees/", { params: { limit: 500 } }).then((res) => {
        const data = res.data?.data ?? res.data;
        setEmployees((data || []).map((e: any) => ({ id: e.id, full_name: e.full_name, employee_code: e.employee_code })));
      });
    });
  }, []);

  const openCreate = () => {
    setEditProfile(null);
    setForm({ employee_id: "", basic_salary: "", housing_allowance: "0", transport_allowance: "0", tax_pin: "", nhif_no: "", nssf_no: "", bank_name: "", bank_account_no: "", bank_branch: "", notes: "", is_active: true });
    setError("");
    setShowModal(true);
  };

  const openEdit = (p: PayrollProfile) => {
    setEditProfile(p);
    setForm({
      employee_id: p.employee_id,
      basic_salary: String(p.basic_salary),
      housing_allowance: String(p.housing_allowance),
      transport_allowance: String(p.transport_allowance),
      tax_pin: p.tax_pin || "",
      nhif_no: p.nhif_no || "",
      nssf_no: p.nssf_no || "",
      bank_name: p.bank_name || "",
      bank_account_no: p.bank_account_no || "",
      bank_branch: p.bank_branch || "",
      notes: p.notes || "",
      is_active: p.is_active,
    });
    setError("");
    setShowModal(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = {
        ...form,
        basic_salary: parseFloat(form.basic_salary),
        housing_allowance: parseFloat(form.housing_allowance) || 0,
        transport_allowance: parseFloat(form.transport_allowance) || 0,
        tax_pin: form.tax_pin || undefined,
        nhif_no: form.nhif_no || undefined,
        nssf_no: form.nssf_no || undefined,
        bank_name: form.bank_name || undefined,
        bank_account_no: form.bank_account_no || undefined,
        bank_branch: form.bank_branch || undefined,
        notes: form.notes || undefined,
      };
      if (editProfile) {
        await payrollKeApi.updateProfile(editProfile.id, payload);
      } else {
        await payrollKeApi.createProfile(payload as any);
      }
      setShowModal(false);
      load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };
  const canManageProfiles = hasPermission("payroll_ke.create");

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Payroll Profiles</h1>
          <p className="text-sm text-gray-500 mt-1">Kenya statutory data per employee — KRA PIN, NHIF, NSSF, salary structure</p>
        </div>
        {canManageProfiles && (
          <button onClick={openCreate} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">+ New Profile</button>
        )}
      </div>

      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
            <tr>
              <th className="px-4 py-3 text-left">Employee</th>
              <th className="px-4 py-3 text-right">Basic Salary</th>
              <th className="px-4 py-3 text-right">Housing Allow.</th>
              <th className="px-4 py-3 text-right">Transport Allow.</th>
              <th className="px-4 py-3 text-left">KRA PIN</th>
              <th className="px-4 py-3 text-left">NHIF No</th>
              <th className="px-4 py-3 text-left">NSSF No</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : profiles.length === 0 ? (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">No payroll profiles. Create one per employee to enable payroll calculations.</td></tr>
            ) : (
              profiles.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <p className="font-medium">{p.employee_name || "—"}</p>
                    <p className="text-xs text-gray-400">{p.employee_code}</p>
                  </td>
                  <td className="px-4 py-2 text-right font-semibold">KES {Number(p.basic_salary).toLocaleString()}</td>
                  <td className="px-4 py-2 text-right">{Number(p.housing_allowance).toLocaleString()}</td>
                  <td className="px-4 py-2 text-right">{Number(p.transport_allowance).toLocaleString()}</td>
                  <td className="px-4 py-2 font-mono text-xs">{p.tax_pin || <span className="text-red-400">Missing</span>}</td>
                  <td className="px-4 py-2 text-xs">{p.nhif_no || <span className="text-red-400">Missing</span>}</td>
                  <td className="px-4 py-2 text-xs">{p.nssf_no || <span className="text-red-400">Missing</span>}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${p.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-400"}`}>
                      {p.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    {canManageProfiles ? (
                      <button onClick={() => openEdit(p)} className="text-blue-600 hover:underline text-xs">Edit</button>
                    ) : (
                      <span className="text-xs text-gray-400">View only</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl p-6 max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-semibold mb-4">{editProfile ? "Edit Payroll Profile" : "New Payroll Profile"}</h2>
            <form onSubmit={handleSave} className="space-y-4">
              {!editProfile && (
                <div>
                  <label className="block text-sm font-medium mb-1">Employee *</label>
                  <select required value={form.employee_id} onChange={(e) => setForm({ ...form, employee_id: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm">
                    <option value="">Select employee…</option>
                    {employees.map((e) => (<option key={e.id} value={e.id}>{e.employee_code} — {e.full_name}</option>))}
                  </select>
                </div>
              )}
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Basic Salary (KES) *</label>
                  <input required type="number" step="0.01" value={form.basic_salary} onChange={(e) => setForm({ ...form, basic_salary: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Housing Allow.</label>
                  <input type="number" step="0.01" value={form.housing_allowance} onChange={(e) => setForm({ ...form, housing_allowance: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Transport Allow.</label>
                  <input type="number" step="0.01" value={form.transport_allowance} onChange={(e) => setForm({ ...form, transport_allowance: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium mb-1">KRA PIN</label>
                  <input value={form.tax_pin} onChange={(e) => setForm({ ...form, tax_pin: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="A00XXXXXXX" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">NHIF No</label>
                  <input value={form.nhif_no} onChange={(e) => setForm({ ...form, nhif_no: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">NSSF No</label>
                  <input value={form.nssf_no} onChange={(e) => setForm({ ...form, nssf_no: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Bank Name</label>
                  <input value={form.bank_name} onChange={(e) => setForm({ ...form, bank_name: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Account No</label>
                  <input value={form.bank_account_no} onChange={(e) => setForm({ ...form, bank_account_no: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Branch</label>
                  <input value={form.bank_branch} onChange={(e) => setForm({ ...form, bank_branch: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="prof_active" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} className="rounded" />
                <label htmlFor="prof_active" className="text-sm">Active</label>
              </div>
              {error && <p className="text-red-600 text-sm">{error}</p>}
              <div className="flex gap-2 pt-1">
                <button type="button" onClick={() => setShowModal(false)} className="flex-1 py-2 border rounded-lg text-sm hover:bg-gray-50">Cancel</button>
                <button type="submit" disabled={saving} className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm disabled:opacity-50">
                  {saving ? "Saving…" : editProfile ? "Update Profile" : "Create Profile"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
