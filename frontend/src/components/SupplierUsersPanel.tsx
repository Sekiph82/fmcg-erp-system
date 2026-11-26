"use client";
// Staff panel on a supplier account: who can sign in to the supplier portal, invite, sign-in links, deactivate.
import { useCallback, useEffect, useState } from "react";
import { spApi, type SPUser, type SPUserRole } from "@/lib/supplier_portal";
import { AccessLinkNotice } from "@/components/AccessLinkNotice";
import { tx } from "@/lib/i18n/core";

const ROLES: SPUserRole[] = ["OWNER", "SALES", "LOGISTICS", "FINANCE", "QUALITY", "VIEWER"];
// spApi errors carry the raw response body; show the server's message
const msg = (e: unknown) => { const t = (e as Error).message; try { const d = JSON.parse(t).detail; return typeof d === "string" ? d : t; } catch { return t; } };

export function SupplierUsersPanel({ accountId }: { accountId: string }) {
  const [users, setUsers] = useState<SPUser[]>([]);
  const [form, setForm] = useState<{ full_name: string; email: string; role_type: SPUserRole }>({ full_name: "", email: "", role_type: "SALES" });
  const [link, setLink] = useState<{ link: string; who: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => { spApi.listUsers(accountId).then(setUsers).catch((e) => setError(msg(e))); }, [accountId]);
  useEffect(load, [load]);
  const run = async (fn: () => Promise<{ activation_link?: string; email: string } | unknown>) => {
    try {
      const r = (await fn()) as { activation_link?: string; email?: string };
      if (r?.activation_link) setLink({ link: r.activation_link, who: r.email ?? "" });
      setError(null); load();
    } catch (e) { setError(msg(e)); }
  };

  const input = "text-sm border rounded-lg px-2 py-1.5";
  return (
    <section aria-label={tx("Supplier portal users")} className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
      <h2 className="text-base font-semibold text-gray-900">{tx("Supplier portal users")}</h2>
      {error && <p role="alert" className="rounded-lg p-2 text-sm bg-red-50 border border-red-200 text-red-700">{error}</p>}
      {link && <AccessLinkNotice link={link.link} who={link.who} onClose={() => setLink(null)} />}
      <form className="grid sm:grid-cols-4 gap-2" onSubmit={(e) => { e.preventDefault(); run(() => spApi.inviteUser(accountId, form)); setForm({ ...form, full_name: "", email: "" }); }}>
        <input aria-label={tx("Full name")} required placeholder={tx("Full name")} value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} className={input} />
        <input aria-label={tx("E-mail")} required type="email" placeholder={tx("E-mail")} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className={input} />
        <select aria-label={tx("Portal role")} value={form.role_type} onChange={(e) => setForm({ ...form, role_type: e.target.value as SPUserRole })} className={input}>
          {ROLES.map((r) => <option key={r}>{r}</option>)}
        </select>
        <button className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg">{tx("Invite")}</button>
      </form>
      <table className="w-full text-sm">
        <thead><tr className="text-left text-xs text-gray-500"><th>{tx("Name")}</th><th>{tx("E-mail")}</th><th>{tx("Role")}</th><th>{tx("Status")}</th><th /></tr></thead>
        <tbody>{users.map((u) => (
          <tr key={u.id} className="border-t">
            <td className="py-1.5">{u.full_name}</td><td className="text-xs">{u.email}</td><td className="text-xs">{u.role_type}</td>
            <td className="text-xs">{u.is_active ? tx("Active") : tx("Deactivated")}{u.last_login_at ? "" : tx(" · never signed in")}</td>
            <td className="text-right space-x-3">
              {u.is_active && <button onClick={() => run(() => spApi.passwordLink(u.id))} className="text-xs text-blue-600 underline">{tx("Sign-in link")}</button>}
              {u.is_active && <button onClick={() => run(() => spApi.deactivateUser(u.id))} className="text-xs text-red-600 underline">{tx("Deactivate")}</button>}
            </td>
          </tr>))}
          {users.length === 0 && <tr><td colSpan={5} className="py-3 text-center text-gray-400">{tx("No portal users yet.")}</td></tr>}
        </tbody>
      </table>
    </section>
  );
}
