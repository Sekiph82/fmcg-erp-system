"use client";
// Account-based marketing (M36.S05.T005): target-account groups, buying committees, recorded engagement,
// coordinated consent-aware campaigns and influenced revenue.
import { Fragment, useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { EntityPicker } from "@/components/EntityPicker";
import { SendApprovalsPanel } from "@/components/SendApprovalsPanel";
import { getActiveCompanyId } from "@/lib/company";
import { sendApprovalsApi, type SendPolicy } from "@/lib/send_approvals";

interface Group { id: string; name: string; description: string | null; accounts: number; campaign_started_at: string | null }
interface Account { customer_id: string; name: string; code: string; tier: number; contacts: number; contacts_engaged: number;
  key_roles_missing: string[]; activities: number; meetings: number; emails_sent: number; emails_received: number; tickets: number; orders: number; order_value: number }
interface Overview { id: string; name: string; accounts: Account[]; totals: Record<string, number>; attribution: { since: string; orders: number; order_value: number; note: string } | null }
interface Contact { id: string; full_name: string; title: string | null; email: string | null; committee_role: string }
const ROLES = ["DECISION_MAKER", "BUYER", "CHAMPION", "INFLUENCER", "USER", "BLOCKER"];
const kes = (n: number) => `KES ${Math.round(n).toLocaleString()}`;
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail; return typeof d === "string" ? d : "Request failed."; };

export default function ABMPage() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [sel, setSel] = useState<string | null>(null);
  const [ov, setOv] = useState<Overview | null>(null);
  const [name, setName] = useState("");
  const [member, setMember] = useState({ customer_id: "", tier: "2" });
  const [open, setOpen] = useState<string | null>(null);
  const [camp, setCamp] = useState({ subject: "", body: "Hello {contact_name},\n\n" });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  // M48.S01.T023 send controls: one company per campaign, approval by a second editor, daily cap
  const [useActiveCompany, setUseActiveCompany] = useState(false);
  const [approvalId, setApprovalId] = useState<string | null>(null);
  const [policy, setPolicy] = useState<SendPolicy | null>(null);
  const [approvalsKey, setApprovalsKey] = useState(0);
  const say = (ok: boolean, text: string) => setMsg({ ok, text });

  const loadGroups = useCallback(() => apiClient.get<Group[]>("/api/v1/abm/groups").then((r) => setGroups(r.data)).catch((e) => say(false, err(e))), []);
  const loadOv = useCallback((id: string) => apiClient.get<Overview>(`/api/v1/abm/groups/${id}`).then((r) => setOv(r.data)).catch((e) => say(false, err(e))), []);
  useEffect(() => { loadGroups(); }, [loadGroups]);
  useEffect(() => { if (sel) loadOv(sel); else setOv(null); }, [sel, loadOv]);

  const act = async (fn: () => Promise<unknown>, ok: string) => { try { await fn(); say(true, ok); loadGroups(); if (sel) loadOv(sel); } catch (e) { say(false, err(e)); setApprovalsKey((k) => k + 1); } };
  return (
    <div className="p-4 sm:p-6 space-y-4">
      <div><h1 className="text-xl font-bold text-gray-900">Key accounts</h1>
        <p className="text-xs text-gray-500">Target-account groups, buying committees and what has really happened with each account.</p></div>
      {msg && <p role="status" className={`text-sm rounded px-3 py-2 ${msg.ok ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-700"}`}>{msg.text}</p>}
      <div className="flex flex-wrap gap-2 items-end">
        <select aria-label="Account group" value={sel ?? ""} onChange={(e) => setSel(e.target.value || null)} className="border rounded px-3 py-2 text-sm">
          <option value="">Choose a group…</option>
          {groups.map((g) => <option key={g.id} value={g.id}>{g.name} ({g.accounts})</option>)}
        </select>
        <input aria-label="New group name" placeholder="New group name" value={name} onChange={(e) => setName(e.target.value)} className="border rounded px-3 py-2 text-sm" />
        <button disabled={name.trim().length < 2} onClick={() => act(async () => { const r = await apiClient.post<{ id: string }>("/api/v1/abm/groups", { name }); setSel(r.data.id); setName(""); }, "Group created.")}
          className="rounded bg-blue-600 px-3 py-2 text-sm text-white disabled:opacity-50">Create group</button>
      </div>

      {ov && (<>
        <div className="bg-white border rounded-xl p-3 flex flex-wrap gap-2 items-end">
          <div className="min-w-[240px] flex-1"><label className="block text-xs text-gray-500 mb-1">Add account</label>
            <EntityPicker kind="customer" label="Account to add" value={member.customer_id} onChange={(id) => setMember({ ...member, customer_id: id })} /></div>
          <select aria-label="Tier" value={member.tier} onChange={(e) => setMember({ ...member, tier: e.target.value })} className="border rounded px-2 py-2 text-sm">
            <option value="1">Tier 1 — strategic</option><option value="2">Tier 2 — core</option><option value="3">Tier 3 — watch</option></select>
          <button disabled={!member.customer_id} onClick={() => act(() => apiClient.post(`/api/v1/abm/groups/${ov.id}/members`, { customer_id: member.customer_id, tier: Number(member.tier) }).then(() => setMember({ customer_id: "", tier: "2" })), "Account added.")}
            className="rounded bg-blue-600 px-3 py-2 text-sm text-white disabled:opacity-50">Add</button>
        </div>

        <div className="bg-white border rounded-xl overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-600"><tr>{["Account", "Tier", "Committee", "Activities", "Meetings", "E-mails out / in", "Tickets", "Orders (90 d)", ""].map((h) => <th key={h} className="px-3 py-2 text-left">{h}</th>)}</tr></thead>
            <tbody className="divide-y">
              {ov.accounts.length === 0 ? <tr><td colSpan={9} className="px-3 py-6 text-center text-gray-400">No accounts in this group yet.</td></tr> : ov.accounts.map((a) => (<Fragment key={a.customer_id}>
                <tr key={a.customer_id}>
                  <td className="px-3 py-2"><button onClick={() => setOpen(open === a.customer_id ? null : a.customer_id)} className="text-blue-700 underline text-left">{a.name}</button><span className="block text-xs text-gray-500">{a.code}</span></td>
                  <td className="px-3 py-2">{a.tier}</td>
                  <td className="px-3 py-2">{a.contacts} ({a.contacts_engaged} replied){a.key_roles_missing.length > 0 && <span className="block text-xs text-amber-700">missing: {a.key_roles_missing.join(", ").toLowerCase().replace(/_/g, " ")}</span>}</td>
                  <td className="px-3 py-2">{a.activities}</td><td className="px-3 py-2">{a.meetings}</td>
                  <td className="px-3 py-2">{a.emails_sent} / {a.emails_received}</td><td className="px-3 py-2">{a.tickets}</td>
                  <td className="px-3 py-2">{a.orders} · {kes(a.order_value)}</td>
                  <td className="px-3 py-2"><button onClick={() => act(() => apiClient.delete(`/api/v1/abm/groups/${ov.id}/members/${a.customer_id}`), "Account removed.")} className="text-xs text-red-700">Remove</button></td>
                </tr>
                {open === a.customer_id && <tr key={a.customer_id + "-c"}><td colSpan={9} className="bg-gray-50 px-3 py-3"><Committee customerId={a.customer_id} onChange={() => loadOv(ov.id)} say={say} /></td></tr>}
              </Fragment>))}
            </tbody>
          </table>
        </div>

        {ov.attribution && <p className="text-sm text-gray-700">Since the campaign started ({ov.attribution.since}): {ov.attribution.orders} orders · {kes(ov.attribution.order_value)} <span className="text-xs text-gray-500">— {ov.attribution.note}</span></p>}

        <div className="bg-white border rounded-xl p-3 space-y-2">
          <p className="font-medium text-sm">Coordinated campaign to every committee member</p>
          <p className="text-xs text-gray-500">Sent through the outbox: people without marketing consent are suppressed automatically. Placeholders: {"{contact_name}"}, {"{company_name}"}.</p>
          <input aria-label="Campaign subject" placeholder="Subject" value={camp.subject} onChange={(e) => setCamp({ ...camp, subject: e.target.value })} className="w-full border rounded px-3 py-2 text-sm" />
          <textarea aria-label="Campaign message" rows={4} value={camp.body} onChange={(e) => setCamp({ ...camp, body: e.target.value })} className="w-full border rounded px-3 py-2 text-sm" />
          {(() => {
            const activeCompany = getActiveCompanyId();
            const payload = { ...camp, company_id: useActiveCompany ? activeCompany : null };
            const contentReason = camp.subject.length < 3 ? "Write a subject (3+ characters)." : camp.body.length < 10 ? "Write a message (10+ characters)." : null;
            const companyReason = useActiveCompany && !activeCompany ? "No active company is selected in the company switcher." : null;
            const capReason = policy && policy.used_today >= policy.daily_cap ? `Daily limit reached (${policy.used_today} of ${policy.daily_cap} direct marketing sends today).` : null;
            const approvalReason = policy?.approval_required && !approvalId ? "Approval required: request it, have a second editor approve, then pick the approval below." : null;
            const sendReason = contentReason ?? companyReason ?? capReason ?? approvalReason;
            const requestReason = contentReason ?? companyReason;
            return (<>
              <label className="flex items-center gap-2 text-xs text-gray-600">
                <input type="checkbox" checked={useActiveCompany} onChange={(e) => { setUseActiveCompany(e.target.checked); setApprovalId(null); }} />
                Send only to accounts of the active company (needed when the group has accounts of several companies)</label>
              <div className="flex flex-wrap gap-2 items-center">
                <button disabled={!!sendReason} title={sendReason ?? undefined}
                  onClick={async () => {
                    try { const r = await apiClient.post<{ queued: number; suppressed: number }>(`/api/v1/abm/groups/${ov.id}/campaign`, { ...payload, approval_id: approvalId });
                      say(true, `${r.data.queued} messages queued, ${r.data.suppressed} suppressed (no consent).`); loadOv(ov.id); }
                    catch (e) { say(false, err(e)); }
                    setApprovalId(null); setApprovalsKey((k) => k + 1);
                  }}
                  className="rounded bg-indigo-600 px-3 py-2 text-sm text-white disabled:opacity-50">{approvalId ? "Queue campaign with approval" : "Queue campaign"}</button>
                <button disabled={!!requestReason} title={requestReason ?? undefined}
                  onClick={() => act(async () => { await sendApprovalsApi.requestAbm(ov.id, payload); setApprovalsKey((k) => k + 1); }, "Approval requested; another editor must approve it.")}
                  className="rounded border px-3 py-2 text-sm disabled:opacity-50">Request approval</button>
                {sendReason && <span className="text-xs text-amber-700">{sendReason}</span>}
              </div>
            </>);
          })()}
          <SendApprovalsPanel kind="abm" targetId={ov.id} picked={approvalId} onPick={setApprovalId} refresh={approvalsKey} onPolicy={setPolicy} />
        </div>
      </>)}
    </div>
  );
}

function Committee({ customerId, onChange, say }: { customerId: string; onChange: () => void; say: (ok: boolean, t: string) => void }) {
  const [rows, setRows] = useState<Contact[]>([]);
  const [f, setF] = useState({ full_name: "", title: "", email: "", committee_role: "BUYER" });
  const load = useCallback(() => apiClient.get<{ contacts: Contact[] }>(`/api/v1/abm/accounts/${customerId}/committee`).then((r) => setRows(r.data.contacts)), [customerId]);
  useEffect(() => { load(); }, [load]);
  const add = async () => {
    try { await apiClient.post(`/api/v1/abm/accounts/${customerId}/committee`, { ...f, email: f.email || null, title: f.title || null }); setF({ full_name: "", title: "", email: "", committee_role: "BUYER" }); load(); onChange(); say(true, "Contact added."); }
    catch (e) { say(false, err(e)); }
  };
  return (
    <div className="space-y-2 text-sm">
      <p className="font-medium">Buying committee</p>
      <ul className="divide-y">{rows.map((c) => <li key={c.id} className="py-1 flex justify-between gap-2"><span>{c.full_name}{c.title ? ` — ${c.title}` : ""} <span className="text-xs text-gray-500">{c.email}</span></span>
        <span className="text-xs">{c.committee_role.toLowerCase().replace("_", " ")} <button onClick={async () => { await apiClient.delete(`/api/v1/abm/contacts/${c.id}`); load(); onChange(); }} className="ml-2 text-red-700">×</button></span></li>)}</ul>
      <div className="grid gap-2 sm:grid-cols-5">
        <input aria-label="Contact name" placeholder="Name" value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} className="border rounded px-2 py-1.5" />
        <input aria-label="Contact title" placeholder="Title" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} className="border rounded px-2 py-1.5" />
        <input aria-label="Contact e-mail" placeholder="E-mail" type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} className="border rounded px-2 py-1.5" />
        <select aria-label="Committee role" value={f.committee_role} onChange={(e) => setF({ ...f, committee_role: e.target.value })} className="border rounded px-2 py-1.5">{ROLES.map((r) => <option key={r} value={r}>{r.toLowerCase().replace("_", " ")}</option>)}</select>
        <button disabled={f.full_name.length < 2} onClick={add} className="rounded bg-blue-600 text-white disabled:opacity-50">Add</button>
      </div>
    </div>
  );
}
