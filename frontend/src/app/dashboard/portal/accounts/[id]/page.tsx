"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  portalApi, PortalAccount, PortalUser, PortalDashboard,
  fmtCurrency, ACCOUNT_TYPE_LABELS, ACCOUNT_STATUS_COLORS, USER_ROLE_LABELS, ORDER_MODE_LABELS,
} from "@/lib/portal";

type Tab = "overview" | "users" | "orders" | "invoices" | "claims" | "drafts";

export default function PortalAccountDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [account, setAccount] = useState<PortalAccount | null>(null);
  const [users, setUsers] = useState<PortalUser[]>([]);
  const [dashboard, setDashboard] = useState<PortalDashboard | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [loading, setLoading] = useState(true);

  // Invite form
  const [showInvite, setShowInvite] = useState(false);
  const [inviteForm, setInviteForm] = useState({ full_name: "", email: "", phone: "", role_type: "VIEWER" });
  const [inviteSaving, setInviteSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const [acc, usrs, dash] = await Promise.all([
        portalApi.getAccount(id),
        portalApi.getUsers(id),
        portalApi.getDashboard(id),
      ]);
      setAccount(acc as PortalAccount);
      setUsers(usrs as PortalUser[]);
      setDashboard(dash as PortalDashboard);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const handleInvite = async () => {
    setInviteSaving(true);
    try {
      await portalApi.inviteUser(id, inviteForm as unknown as Partial<PortalUser>);
      setShowInvite(false);
      setInviteForm({ full_name: "", email: "", phone: "", role_type: "VIEWER" });
      await load();
    } catch (e) { console.error(e); }
    setInviteSaving(false);
  };

  const handleDeactivateUser = async (userId: string) => {
    try { await portalApi.deactivateUser(userId); await load(); } catch (e) { console.error(e); }
  };

  if (loading) return <div className="p-6 text-gray-500">Loading…</div>;
  if (!account) return <div className="p-6 text-red-500">Account not found</div>;

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "users", label: `Users (${users.length})` },
    { id: "orders", label: "Orders" },
    { id: "invoices", label: "Invoices" },
    { id: "claims", label: "Claims" },
    { id: "drafts", label: "Draft Orders" },
  ];

  const agingItems = dashboard ? [
    { label: "Current", value: dashboard.current_due, color: "#10B981" },
    { label: "0-30 days", value: dashboard.aging_0_30, color: "#F59E0B" },
    { label: "31-60 days", value: dashboard.aging_31_60, color: "#F97316" },
    { label: "61-90 days", value: dashboard.aging_61_90, color: "#EF4444" },
    { label: "90+ days", value: dashboard.aging_90_plus, color: "#991B1B" },
  ] : [];

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <Link href="/dashboard/portal" className="hover:underline">Portal</Link>
            <span>/</span>
            <span>{account.account_code}</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mt-1">
            {account.primary_contact_name || account.account_code}
          </h1>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-xs text-gray-500">{ACCOUNT_TYPE_LABELS[account.account_type]}</span>
            <span className="px-2 py-0.5 rounded-full text-xs font-medium"
              style={{ background: ACCOUNT_STATUS_COLORS[account.portal_status] + "22", color: ACCOUNT_STATUS_COLORS[account.portal_status] }}>
              {account.portal_status}
            </span>
            <span className="text-xs text-gray-400">{ORDER_MODE_LABELS[account.order_mode]}</span>
          </div>
        </div>
        <div className="flex gap-2">
          {account.portal_status === "PENDING" && (
            <button onClick={() => portalApi.activateAccount(id).then(load)}
              className="px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700">
              Activate
            </button>
          )}
          {account.portal_status === "ACTIVE" && (
            <button onClick={() => portalApi.suspendAccount(id).then(load)}
              className="px-3 py-1.5 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700">
              Suspend
            </button>
          )}
          <Link href={`/dashboard/portal/accounts/${id}/view`}
            className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50">
            Portal View
          </Link>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === t.id ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Overview */}
      {tab === "overview" && dashboard && (
        <div className="space-y-4">
          {/* Balance cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="bg-white rounded-xl border shadow-sm p-4">
              <div className="text-xs text-gray-500">Outstanding Balance</div>
              <div className="text-xl font-bold text-gray-800">{fmtCurrency(dashboard.outstanding_balance)}</div>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-xl p-4">
              <div className="text-xs text-gray-500">Overdue</div>
              <div className="text-xl font-bold text-red-700">{fmtCurrency(dashboard.overdue_balance)}</div>
            </div>
            <div className="bg-white rounded-xl border shadow-sm p-4">
              <div className="text-xs text-gray-500">Open Orders</div>
              <div className="text-xl font-bold text-gray-800">{dashboard.open_orders}</div>
            </div>
          </div>

          {/* Aging */}
          <div className="bg-white rounded-xl border shadow-sm p-4">
            <h2 className="font-semibold text-gray-800 mb-3">Accounts Receivable Aging</h2>
            <div className="space-y-2">
              {agingItems.map(item => (
                <div key={item.label} className="flex items-center gap-3">
                  <div className="w-20 text-xs text-gray-600">{item.label}</div>
                  <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all"
                      style={{
                        width: `${dashboard.outstanding_balance > 0 ? (item.value / dashboard.outstanding_balance * 100) : 0}%`,
                        background: item.color,
                      }} />
                  </div>
                  <div className="w-28 text-right text-xs font-medium">{fmtCurrency(item.value)}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Contact details */}
          <div className="bg-white rounded-xl border shadow-sm p-4">
            <h2 className="font-semibold text-gray-800 mb-3">Account Details</h2>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="text-gray-500">Account Code</div><div className="font-mono">{account.account_code}</div>
              <div className="text-gray-500">Type</div><div>{ACCOUNT_TYPE_LABELS[account.account_type]}</div>
              <div className="text-gray-500">Contact Email</div><div>{account.primary_contact_email || "—"}</div>
              <div className="text-gray-500">Phone</div><div>{account.primary_contact_phone || "—"}</div>
              <div className="text-gray-500">Currency</div><div>{account.default_currency}</div>
              <div className="text-gray-500">Linked Customer</div><div className="font-mono text-xs">{account.linked_customer_id || "—"}</div>
              <div className="text-gray-500">Linked Distributor</div><div className="font-mono text-xs">{account.linked_distributor_id || "—"}</div>
              <div className="text-gray-500">Can View Prices</div><div>{account.can_view_prices ? "Yes" : "No"}</div>
              <div className="text-gray-500">Can View Promotions</div><div>{account.can_view_promotions ? "Yes" : "No"}</div>
              <div className="text-gray-500">Can Initiate Payment</div><div>{account.can_initiate_payment ? "Yes" : "No"}</div>
            </div>
          </div>
        </div>
      )}

      {/* Users */}
      {tab === "users" && (
        <div className="space-y-3">
          <button onClick={() => setShowInvite(true)}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            + Invite User
          </button>
          <div className="bg-white rounded-xl border shadow-sm overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-xs text-gray-600">
                  <th className="px-3 py-2 text-left">Name</th>
                  <th className="px-3 py-2 text-left">Email</th>
                  <th className="px-3 py-2 text-left">Role</th>
                  <th className="px-3 py-2 text-left">Status</th>
                  <th className="px-3 py-2 text-left">Last Login</th>
                  <th className="px-3 py-2 text-left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 && <tr><td colSpan={6} className="px-3 py-6 text-center text-gray-400">No users</td></tr>}
                {users.map(user => (
                  <tr key={user.id} className="border-b hover:bg-gray-50">
                    <td className="px-3 py-2 font-medium text-gray-800">{user.full_name}</td>
                    <td className="px-3 py-2 text-gray-600 text-xs">{user.email}</td>
                    <td className="px-3 py-2 text-xs text-gray-500">{USER_ROLE_LABELS[user.role_type]}</td>
                    <td className="px-3 py-2">
                      <span className={`px-2 py-0.5 rounded-full text-xs ${user.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                        {user.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-400">
                      {user.last_login_at ? new Date(user.last_login_at).toLocaleDateString() : "Never"}
                    </td>
                    <td className="px-3 py-2">
                      {user.is_active && (
                        <button onClick={() => handleDeactivateUser(user.id)}
                          className="text-xs text-red-600 hover:underline">Deactivate</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Orders */}
      {tab === "orders" && <PortalOrdersTab accountId={id} />}

      {/* Invoices */}
      {tab === "invoices" && <PortalInvoicesTab accountId={id} />}

      {/* Claims */}
      {tab === "claims" && <PortalClaimsAdminTab accountId={id} />}

      {/* Draft Orders */}
      {tab === "drafts" && <PortalDraftsAdminTab accountId={id} />}

      {/* Invite Modal */}
      {showInvite && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md space-y-3">
            <h2 className="font-semibold text-lg">Invite Portal User</h2>
            <input placeholder="Full Name *" value={inviteForm.full_name}
              onChange={e => setInviteForm(f => ({ ...f, full_name: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Email *" value={inviteForm.email}
              onChange={e => setInviteForm(f => ({ ...f, email: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Phone" value={inviteForm.phone}
              onChange={e => setInviteForm(f => ({ ...f, phone: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <select value={inviteForm.role_type} onChange={e => setInviteForm(f => ({ ...f, role_type: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm">
              {Object.entries(USER_ROLE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <div className="flex gap-2 pt-1">
              <button onClick={handleInvite} disabled={inviteSaving || !inviteForm.full_name || !inviteForm.email}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm disabled:opacity-50">
                {inviteSaving ? "Inviting…" : "Send Invitation"}
              </button>
              <button onClick={() => setShowInvite(false)} className="flex-1 border rounded-lg py-2 text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function PortalOrdersTab({ accountId }: { accountId: string }) {
  const [orders, setOrders] = useState<Record<string, unknown>[]>([]);
  useEffect(() => {
    portalApi.getOrders(accountId).then(d => setOrders(d as Record<string, unknown>[])).catch(console.error);
  }, [accountId]);
  return (
    <div className="bg-white rounded-xl border shadow-sm overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-gray-50 text-xs text-gray-600">
            <th className="px-3 py-2 text-left">Order No</th>
            <th className="px-3 py-2 text-left">Date</th>
            <th className="px-3 py-2 text-left">Status</th>
            <th className="px-3 py-2 text-left">Payment</th>
            <th className="px-3 py-2 text-left">Lines</th>
          </tr>
        </thead>
        <tbody>
          {orders.length === 0 && <tr><td colSpan={5} className="px-3 py-6 text-center text-gray-400">No orders</td></tr>}
          {orders.map((o, i) => (
            <tr key={i} className="border-b hover:bg-gray-50">
              <td className="px-3 py-2 font-mono text-xs text-blue-600">{o.order_no as string}</td>
              <td className="px-3 py-2 text-xs text-gray-600">{o.order_date as string}</td>
              <td className="px-3 py-2 text-xs text-gray-600">{o.status as string}</td>
              <td className="px-3 py-2 text-xs text-gray-600">{o.payment_status as string}</td>
              <td className="px-3 py-2 text-xs text-gray-500">{o.line_count as number} lines</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PortalInvoicesTab({ accountId }: { accountId: string }) {
  const [invoices, setInvoices] = useState<Record<string, unknown>[]>([]);
  useEffect(() => {
    portalApi.getInvoices(accountId).then(d => setInvoices(d as Record<string, unknown>[])).catch(console.error);
  }, [accountId]);
  return (
    <div className="bg-white rounded-xl border shadow-sm overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-gray-50 text-xs text-gray-600">
            <th className="px-3 py-2 text-left">Invoice No</th>
            <th className="px-3 py-2 text-left">Date</th>
            <th className="px-3 py-2 text-left">Due Date</th>
            <th className="px-3 py-2 text-left">Status</th>
            <th className="px-3 py-2 text-right">Total</th>
            <th className="px-3 py-2 text-right">Outstanding</th>
          </tr>
        </thead>
        <tbody>
          {invoices.length === 0 && <tr><td colSpan={6} className="px-3 py-6 text-center text-gray-400">No invoices</td></tr>}
          {invoices.map((inv, i) => (
            <tr key={i} className="border-b hover:bg-gray-50">
              <td className="px-3 py-2 font-mono text-xs text-blue-600">{inv.invoice_no as string}</td>
              <td className="px-3 py-2 text-xs text-gray-600">{inv.invoice_date as string}</td>
              <td className="px-3 py-2 text-xs text-gray-600">{inv.due_date as string}</td>
              <td className="px-3 py-2 text-xs text-gray-600">{inv.status as string}</td>
              <td className="px-3 py-2 text-xs text-right text-gray-800">{fmtCurrency(inv.total_amount as number, inv.currency as string)}</td>
              <td className="px-3 py-2 text-xs text-right font-semibold text-red-700">{fmtCurrency(inv.outstanding as number, inv.currency as string)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PortalClaimsAdminTab({ accountId }: { accountId: string }) {
  const [claims, setClaims] = useState<Record<string, unknown>[]>([]);
  useEffect(() => {
    portalApi.getClaims(accountId).then(d => setClaims(d as unknown as Record<string, unknown>[])).catch(console.error);
  }, [accountId]);
  return (
    <div className="bg-white rounded-xl border shadow-sm overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-gray-50 text-xs text-gray-600">
            <th className="px-3 py-2 text-left">Claim No</th>
            <th className="px-3 py-2 text-left">Type</th>
            <th className="px-3 py-2 text-left">Status</th>
            <th className="px-3 py-2 text-left">Submitted</th>
            <th className="px-3 py-2 text-left">Reason</th>
          </tr>
        </thead>
        <tbody>
          {claims.length === 0 && <tr><td colSpan={5} className="px-3 py-6 text-center text-gray-400">No claims</td></tr>}
          {claims.map((c, i) => (
            <tr key={i} className="border-b hover:bg-gray-50">
              <td className="px-3 py-2 font-mono text-xs">{c.claim_no as string}</td>
              <td className="px-3 py-2 text-xs text-gray-600">{c.claim_type as string}</td>
              <td className="px-3 py-2 text-xs text-gray-600">{c.status as string}</td>
              <td className="px-3 py-2 text-xs text-gray-400">{c.created_at ? new Date(c.created_at as string).toLocaleDateString() : "—"}</td>
              <td className="px-3 py-2 text-xs text-gray-600 max-w-xs truncate">{c.reason as string}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PortalDraftsAdminTab({ accountId }: { accountId: string }) {
  const [drafts, setDrafts] = useState<Record<string, unknown>[]>([]);
  useEffect(() => {
    portalApi.getDraftOrders(accountId).then(d => setDrafts(d as unknown as Record<string, unknown>[])).catch(console.error);
  }, [accountId]);

  const handleApprove = async (draftId: string) => {
    try {
      await portalApi.reviewDraftOrder(draftId, { status: "APPROVED", reviewed_by: "admin" });
      portalApi.getDraftOrders(accountId).then(d => setDrafts(d as unknown as Record<string, unknown>[]));
    } catch (e) { console.error(e); }
  };

  const handleReject = async (draftId: string) => {
    try {
      await portalApi.reviewDraftOrder(draftId, { status: "REJECTED", reviewed_by: "admin", review_notes: "Rejected by admin" });
      portalApi.getDraftOrders(accountId).then(d => setDrafts(d as unknown as Record<string, unknown>[]));
    } catch (e) { console.error(e); }
  };

  return (
    <div className="bg-white rounded-xl border shadow-sm overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-gray-50 text-xs text-gray-600">
            <th className="px-3 py-2 text-left">Draft No</th>
            <th className="px-3 py-2 text-left">Status</th>
            <th className="px-3 py-2 text-left">Submitted By</th>
            <th className="px-3 py-2 text-right">Total</th>
            <th className="px-3 py-2 text-left">Submitted</th>
            <th className="px-3 py-2 text-left">Actions</th>
          </tr>
        </thead>
        <tbody>
          {drafts.length === 0 && <tr><td colSpan={6} className="px-3 py-6 text-center text-gray-400">No draft orders</td></tr>}
          {drafts.map((d, i) => (
            <tr key={i} className="border-b hover:bg-gray-50">
              <td className="px-3 py-2 font-mono text-xs">{d.draft_no as string}</td>
              <td className="px-3 py-2 text-xs text-gray-600">{d.status as string}</td>
              <td className="px-3 py-2 text-xs text-gray-500">{d.submitted_by as string || "—"}</td>
              <td className="px-3 py-2 text-xs text-right text-gray-800">{fmtCurrency(d.total_amount as number, d.currency as string)}</td>
              <td className="px-3 py-2 text-xs text-gray-400">{d.created_at ? new Date(d.created_at as string).toLocaleDateString() : "—"}</td>
              <td className="px-3 py-2 flex gap-2">
                {d.status === "SUBMITTED" && (
                  <>
                    <button onClick={() => handleApprove(d.id as string)} className="text-xs text-green-600 hover:underline">Approve</button>
                    <button onClick={() => handleReject(d.id as string)} className="text-xs text-red-600 hover:underline">Reject</button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
