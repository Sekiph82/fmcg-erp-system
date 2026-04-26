"use client";
import { useEffect, useState } from "react";
import { portalApi, PortalUser, USER_ROLE_LABELS } from "@/lib/portal";

export default function PortalUsersPage() {
  const [accounts, setAccounts] = useState<{ id: string; account_code: string; primary_contact_name?: string }[]>([]);
  const [allUsers, setAllUsers] = useState<(PortalUser & { account_code: string })[]>([]);
  const [loading, setLoading] = useState(true);
  const [roleFilter, setRoleFilter] = useState("");
  const [activeFilter, setActiveFilter] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const accs = await portalApi.getAccounts();
      const accountList = accs as { id: string; account_code: string; primary_contact_name?: string }[];
      setAccounts(accountList);
      const usersAll: (PortalUser & { account_code: string })[] = [];
      for (const acc of accountList.slice(0, 30)) {
        const users = await portalApi.getUsers(acc.id);
        for (const u of (users as PortalUser[])) {
          usersAll.push({ ...u, account_code: acc.account_code });
        }
      }
      setAllUsers(usersAll);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const filtered = allUsers.filter(u => {
    if (roleFilter && u.role_type !== roleFilter) return false;
    if (activeFilter === "active" && !u.is_active) return false;
    if (activeFilter === "inactive" && u.is_active) return false;
    return true;
  });

  const handleDeactivate = async (userId: string) => {
    try { await portalApi.deactivateUser(userId); load(); } catch (e) { console.error(e); }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Portal Users</h1>
        <div className="text-sm text-gray-500">{filtered.length} users</div>
      </div>

      <div className="flex flex-wrap gap-3 items-center">
        <select value={roleFilter} onChange={e => setRoleFilter(e.target.value)}
          className="text-sm border rounded-lg px-2 py-1.5">
          <option value="">All Roles</option>
          {Object.entries(USER_ROLE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={activeFilter} onChange={e => setActiveFilter(e.target.value)}
          className="text-sm border rounded-lg px-2 py-1.5">
          <option value="">All Status</option>
          <option value="active">Active Only</option>
          <option value="inactive">Inactive Only</option>
        </select>
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-xs text-gray-600">
              <th className="px-3 py-2 text-left">Name</th>
              <th className="px-3 py-2 text-left">Email</th>
              <th className="px-3 py-2 text-left">Account</th>
              <th className="px-3 py-2 text-left">Role</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Last Login</th>
              <th className="px-3 py-2 text-left">Invited By</th>
              <th className="px-3 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={8} className="px-3 py-6 text-center text-gray-400">Loading…</td></tr>}
            {!loading && filtered.length === 0 && <tr><td colSpan={8} className="px-3 py-6 text-center text-gray-400">No users found</td></tr>}
            {filtered.map(user => (
              <tr key={user.id} className="border-b hover:bg-gray-50">
                <td className="px-3 py-2 font-medium text-gray-800">{user.full_name}</td>
                <td className="px-3 py-2 text-xs text-gray-600">{user.email}</td>
                <td className="px-3 py-2 text-xs font-mono text-gray-500">{user.account_code}</td>
                <td className="px-3 py-2 text-xs text-gray-500">{USER_ROLE_LABELS[user.role_type]}</td>
                <td className="px-3 py-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${user.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                    {user.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="px-3 py-2 text-xs text-gray-400">
                  {user.last_login_at ? new Date(user.last_login_at).toLocaleDateString() : "Never"}
                </td>
                <td className="px-3 py-2 text-xs text-gray-400">{user.invited_by || "—"}</td>
                <td className="px-3 py-2">
                  {user.is_active && (
                    <button onClick={() => handleDeactivate(user.id)}
                      className="text-xs text-red-600 hover:underline">Deactivate</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
