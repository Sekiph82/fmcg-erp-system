"use client";
import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { spApi, SPUser, SPUserRole } from "@/lib/supplier_portal";

const ROLE_COLORS: Record<SPUserRole, string> = {
  OWNER: "bg-purple-100 text-purple-800",
  SALES: "bg-blue-100 text-blue-800",
  LOGISTICS: "bg-orange-100 text-orange-800",
  FINANCE: "bg-green-100 text-green-800",
  QUALITY: "bg-teal-100 text-teal-800",
  VIEWER: "bg-gray-100 text-gray-700",
  CUSTOM: "bg-pink-100 text-pink-800",
};

function UsersContent() {
  const sp = useSearchParams();
  const accountId = sp.get("account") || "";
  const [users, setUsers] = useState<SPUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviting, setInviting] = useState(false);
  const [form, setForm] = useState({ full_name: "", email: "", phone: "", role_type: "VIEWER" as SPUserRole, notes: "" });
  const [invitedBy, setInvitedBy] = useState("admin");

  const load = () => {
    if (!accountId) return;
    setLoading(true);
    spApi.listUsers(accountId).then(setUsers).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [accountId]);

  const invite = async () => {
    await spApi.inviteUser(accountId, form as any, invitedBy);
    setInviting(false);
    setForm({ full_name: "", email: "", phone: "", role_type: "VIEWER", notes: "" });
    load();
  };

  const deactivate = async (userId: string) => {
    if (!confirm("Deactivate this user?")) return;
    await spApi.deactivateUser(userId);
    load();
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Supplier Portal Users</h1>
          <p className="text-sm text-gray-500 mt-1">Manage users with access to this supplier's portal</p>
        </div>
        {accountId && (
          <button onClick={() => setInviting(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            + Invite User
          </button>
        )}
      </div>

      <div className="grid grid-cols-4 gap-4">
        {(["OWNER", "SALES", "LOGISTICS", "FINANCE", "QUALITY", "VIEWER"] as SPUserRole[]).slice(0, 4).map((r) => (
          <div key={r} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-xl font-bold text-gray-900">{users.filter((u) => u.role_type === r).length}</div>
            <div className="text-xs text-gray-500 mt-1">{r}</div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {["Name", "Email", "Phone", "Role", "Active", "Last Login", "Invited By", "Actions"].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : users.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No users yet. Invite the first supplier user above.</td></tr>
            ) : users.map((u) => (
              <tr key={u.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{u.full_name}</td>
                <td className="px-4 py-3 text-gray-600">{u.email}</td>
                <td className="px-4 py-3 text-gray-500">{u.phone || "—"}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${ROLE_COLORS[u.role_type]}`}>{u.role_type}</span>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${u.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                    {u.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">{u.last_login_at ? new Date(u.last_login_at).toLocaleDateString() : "Never"}</td>
                <td className="px-4 py-3 text-gray-500 text-xs">{u.invited_by || "—"}</td>
                <td className="px-4 py-3">
                  {u.is_active && (
                    <button onClick={() => deactivate(u.id)} className="text-red-600 hover:underline text-xs">Deactivate</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {inviting && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Invite Supplier User</h2>
            <div>
              <label className="text-xs font-medium text-gray-700">Full Name</label>
              <input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Email</label>
              <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Phone</label>
              <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Role</label>
              <select value={form.role_type} onChange={(e) => setForm({ ...form, role_type: e.target.value as SPUserRole })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                {(["OWNER", "SALES", "LOGISTICS", "FINANCE", "QUALITY", "VIEWER", "CUSTOM"] as SPUserRole[]).map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Invited By</label>
              <input value={invitedBy} onChange={(e) => setInvitedBy(e.target.value)}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setInviting(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button onClick={invite} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium">Invite</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function UsersPage() {
  return <Suspense fallback={<div className="p-6 text-gray-400">Loading…</div>}><UsersContent /></Suspense>;
}
