"use client";
import { useEffect, useState } from "react";
import { essApi, ESSProfile } from "@/lib/ess";

const DEMO_EMPLOYEE = "00000000-0000-0000-0000-000000000001";
const inputCls = "w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500";
const labelCls = "block text-[10px] text-slate-400 mb-1";

export default function ESSProfilePage() {
  const [profile, setProfile] = useState<ESSProfile | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ personal_email: "", phone: "", address: "", emergency_contact_name: "", emergency_contact_phone: "" });
  const [msg, setMsg] = useState("");

  const load = () => essApi.getProfile(DEMO_EMPLOYEE).then(setProfile).catch(console.error);
  useEffect(() => { load(); }, []);

  const startEdit = () => {
    if (!profile) return;
    setForm({ personal_email: profile.personal_email || "", phone: profile.phone || "", address: profile.address || "", emergency_contact_name: profile.emergency_contact_name || "", emergency_contact_phone: profile.emergency_contact_phone || "" });
    setEditing(true);
  };
  const handleSave = async () => { await essApi.updateProfile(DEMO_EMPLOYEE, form); await load(); setEditing(false); setMsg("Profile updated"); setTimeout(() => setMsg(""), 2000); };

  const Field = ({ label, value }: { label: string; value?: string }) => (
    <div><p className="text-[10px] text-slate-500 uppercase tracking-widest mb-0.5">{label}</p><p className="text-sm text-slate-300">{value || "—"}</p></div>
  );

  if (!profile) return (
    <div className="p-6 min-h-screen bg-[#060d18] text-slate-200 space-y-4">
      <h1 className="text-xl font-bold text-white">My Profile</h1>
      <p className="text-slate-500 text-sm">No profile found. Set up via HR Admin → Create Profile.</p>
    </div>
  );

  return (
    <div className="p-6 space-y-5 min-h-screen bg-[#060d18] text-slate-200 max-w-2xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">My Profile</h1>
        {!editing && <button onClick={startEdit} className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm">Edit</button>}
      </div>

      {msg && <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3 text-sm text-emerald-300">{msg}</div>}

      <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5 space-y-1">
        <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-3">Work Information</p>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Full Name" value={profile.full_name} />
          <Field label="Work Email" value={profile.email} />
          <Field label="Job Title" value={profile.job_title} />
          <Field label="Department" value={profile.department_name} />
          <Field label="Manager" value={profile.manager_name} />
          <Field label="Grade" value={profile.grade} />
          <Field label="Joining Date" value={profile.joining_date} />
          <Field label="Status" value={profile.employment_status} />
        </div>
      </div>

      <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5">
        <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-3">Personal Information</p>
        {!editing ? (
          <div className="grid grid-cols-2 gap-4">
            <Field label="Personal Email" value={profile.personal_email} />
            <Field label="Phone" value={profile.phone} />
            <Field label="National ID" value={profile.national_id} />
            <Field label="Address" value={profile.address} />
            <Field label="Emergency Contact" value={profile.emergency_contact_name} />
            <Field label="Emergency Phone" value={profile.emergency_contact_phone} />
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {(["personal_email", "phone", "address", "emergency_contact_name", "emergency_contact_phone"] as const).map((k) => (
              <div key={k}><label className={labelCls}>{k.replace(/_/g, " ")}</label>
                <input value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} className={inputCls} /></div>
            ))}
          </div>
        )}
      </div>

      {editing && (
        <div className="flex gap-2">
          <button onClick={handleSave} className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm">Save</button>
          <button onClick={() => setEditing(false)} className="px-4 py-2 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 text-sm">Cancel</button>
        </div>
      )}
    </div>
  );
}
