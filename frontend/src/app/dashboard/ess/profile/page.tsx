"use client";
import { useEffect, useState } from "react";
import { essApi, ESSProfile } from "@/lib/ess";

const DEMO_EMPLOYEE = "00000000-0000-0000-0000-000000000001";

export default function ESSProfilePage() {
  const [profile, setProfile] = useState<ESSProfile | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ personal_email: "", phone: "", address: "", emergency_contact_name: "", emergency_contact_phone: "" });
  const [msg, setMsg] = useState("");

  const load = () => essApi.getProfile(DEMO_EMPLOYEE).then(setProfile).catch(console.error);
  useEffect(() => { load(); }, []);

  const startEdit = () => {
    if (!profile) return;
    setForm({
      personal_email: profile.personal_email || "",
      phone: profile.phone || "",
      address: profile.address || "",
      emergency_contact_name: profile.emergency_contact_name || "",
      emergency_contact_phone: profile.emergency_contact_phone || "",
    });
    setEditing(true);
  };

  const handleSave = async () => {
    await essApi.updateProfile(DEMO_EMPLOYEE, form);
    await load();
    setEditing(false);
    setMsg("Profile updated"); setTimeout(() => setMsg(""), 2000);
  };

  if (!profile) return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold">My Profile</h1>
      <p className="text-gray-500 text-sm">No profile found. Set up via HR Admin → Create Profile.</p>
    </div>
  );

  const field = (label: string, value: string | undefined) => (
    <div>
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-sm font-medium mt-0.5">{value || "—"}</p>
    </div>
  );

  return (
    <div className="p-6 space-y-5 max-w-2xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">My Profile</h1>
        {!editing && (
          <button onClick={startEdit} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">Edit</button>
        )}
      </div>

      {msg && <div className="bg-green-50 text-green-700 text-sm px-4 py-2 rounded">{msg}</div>}

      {/* Read-only fields */}
      <div className="bg-white border rounded-xl p-5">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Work Information</h2>
        <div className="grid grid-cols-2 gap-4">
          {field("Full Name", profile.full_name)}
          {field("Work Email", profile.email)}
          {field("Job Title", profile.job_title)}
          {field("Department", profile.department_name)}
          {field("Manager", profile.manager_name)}
          {field("Grade", profile.grade)}
          {field("Joining Date", profile.joining_date)}
          {field("Status", profile.employment_status)}
        </div>
      </div>

      {/* Editable fields */}
      <div className="bg-white border rounded-xl p-5">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Personal Information</h2>
        {!editing ? (
          <div className="grid grid-cols-2 gap-4">
            {field("Personal Email", profile.personal_email)}
            {field("Phone", profile.phone)}
            {field("National ID", profile.national_id)}
            {field("Address", profile.address)}
            {field("Emergency Contact", profile.emergency_contact_name)}
            {field("Emergency Phone", profile.emergency_contact_phone)}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {(["personal_email", "phone", "address", "emergency_contact_name", "emergency_contact_phone"] as const).map((k) => (
              <div key={k}>
                <label className="block text-xs text-gray-500 mb-1">{k.replace(/_/g, " ")}</label>
                <input value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })}
                  className="w-full border rounded p-2 text-sm" />
              </div>
            ))}
          </div>
        )}
      </div>

      {editing && (
        <div className="flex gap-2">
          <button onClick={handleSave} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">Save</button>
          <button onClick={() => setEditing(false)} className="border px-4 py-2 rounded text-sm">Cancel</button>
        </div>
      )}
    </div>
  );
}
