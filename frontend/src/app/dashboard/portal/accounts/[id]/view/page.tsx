"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  portalApi, PortalAccount, PortalDashboard, PortalClaim, PortalDraftOrder,
  fmtCurrency, CLAIM_TYPE_LABELS, CLAIM_STATUS_COLORS, DRAFT_STATUS_COLORS,
} from "@/lib/portal";

type Tab = "dashboard" | "orders" | "shipments" | "invoices" | "payments" | "statement" | "claims" | "orders-new";

export default function PortalCustomerViewPage() {
  const { id } = useParams<{ id: string }>();
  const [account, setAccount] = useState<PortalAccount | null>(null);
  const [dashboard, setDashboard] = useState<PortalDashboard | null>(null);
  const [tab, setTab] = useState<Tab>("dashboard");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([portalApi.getAccount(id), portalApi.getDashboard(id)])
      .then(([acc, dash]) => {
        setAccount(acc as PortalAccount);
        setDashboard(dash as PortalDashboard);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="p-6 text-gray-500">Loading portal…</div>;
  if (!account) return <div className="p-6 text-red-500">Account not found</div>;

  const tabs: { id: Tab; label: string }[] = [
    { id: "dashboard", label: "Dashboard" },
    { id: "orders", label: "Orders" },
    { id: "shipments", label: "Shipments" },
    { id: "invoices", label: "Invoices" },
    { id: "payments", label: "Payments" },
    { id: "statement", label: "Statement" },
    { id: "claims", label: "Claims" },
    { id: "orders-new", label: "Place Order" },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Portal Header */}
      <div className="bg-white border-b shadow-sm px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white text-sm font-bold">P</div>
          <div>
            <div className="font-semibold text-gray-800">{account.primary_contact_name || account.account_code}</div>
            <div className="text-xs text-gray-400">{account.account_code} · Customer Portal</div>
          </div>
        </div>
        <Link href={`/dashboard/portal/accounts/${id}`}
          className="text-sm text-gray-500 hover:underline">← Admin View</Link>
      </div>

      {/* Tab Nav */}
      <div className="bg-white border-b px-6">
        <div className="flex gap-1 overflow-x-auto">
          {tabs.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px whitespace-nowrap transition-colors ${
                tab === t.id ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"
              }`}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-6 space-y-4">
        {/* Dashboard Tab */}
        {tab === "dashboard" && dashboard && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: "Outstanding Balance", value: fmtCurrency(dashboard.outstanding_balance), color: "text-gray-800" },
                { label: "Overdue", value: fmtCurrency(dashboard.overdue_balance), color: "text-red-700" },
                { label: "Open Orders", value: dashboard.open_orders, color: "text-blue-700" },
                { label: "Open Claims", value: dashboard.open_claims, color: "text-orange-700" },
              ].map(k => (
                <div key={k.label} className="bg-white rounded-xl border shadow-sm p-4">
                  <div className="text-xs text-gray-500">{k.label}</div>
                  <div className={`text-xl font-bold mt-1 ${k.color}`}>{k.value}</div>
                </div>
              ))}
            </div>

            {/* Aging */}
            <div className="bg-white rounded-xl border shadow-sm p-4">
              <h2 className="font-semibold text-gray-800 mb-3 text-sm">Invoice Aging</h2>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {[
                  { label: "Current", value: dashboard.current_due, color: "#10B981" },
                  { label: "0-30 Days", value: dashboard.aging_0_30, color: "#F59E0B" },
                  { label: "31-60 Days", value: dashboard.aging_31_60, color: "#F97316" },
                  { label: "61-90 Days", value: dashboard.aging_61_90, color: "#EF4444" },
                  { label: "90+ Days", value: dashboard.aging_90_plus, color: "#991B1B" },
                ].map(a => (
                  <div key={a.label} className="text-center p-3 rounded-xl border">
                    <div className="text-xs text-gray-500">{a.label}</div>
                    <div className="font-bold mt-0.5" style={{ color: a.color }}>{fmtCurrency(a.value)}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent Invoices */}
            {dashboard.recent_invoices.length > 0 && (
              <div className="bg-white rounded-xl border shadow-sm p-4">
                <h2 className="font-semibold text-gray-800 mb-3 text-sm">Recent Invoices</h2>
                <div className="space-y-2">
                  {dashboard.recent_invoices.map((inv, i) => (
                    <div key={i} className="flex items-center justify-between text-sm py-1 border-b last:border-0">
                      <div>
                        <span className="font-mono text-xs text-blue-600">{inv.invoice_no as string}</span>
                        <span className="text-gray-400 text-xs ml-2">{inv.invoice_date as string}</span>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-gray-600">{inv.status as string}</div>
                        <div className="font-semibold text-red-700 text-xs">{fmtCurrency(inv.outstanding as number)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Orders Tab */}
        {tab === "orders" && <PortalOrdersView accountId={id} />}

        {/* Shipments Tab */}
        {tab === "shipments" && <PortalShipmentsView accountId={id} />}

        {/* Invoices Tab */}
        {tab === "invoices" && <PortalInvoicesView accountId={id} />}

        {/* Payments Tab */}
        {tab === "payments" && <PortalPaymentsView accountId={id} account={account} />}

        {/* Statement Tab */}
        {tab === "statement" && <PortalStatementView accountId={id} />}

        {/* Claims Tab */}
        {tab === "claims" && <PortalClaimsView accountId={id} />}

        {/* Place Order Tab */}
        {tab === "orders-new" && <PortalNewOrderView accountId={id} />}
      </div>
    </div>
  );
}

function PortalOrdersView({ accountId }: { accountId: string }) {
  const [orders, setOrders] = useState<Record<string, unknown>[]>([]);
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    portalApi.getOrders(accountId, { status: statusFilter || undefined })
      .then(d => setOrders(d as Record<string, unknown>[])).catch(console.error);
  }, [accountId, statusFilter]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="text-sm border rounded-lg px-2 py-1.5 bg-white">
          <option value="">All Statuses</option>
          {["DRAFT","CONFIRMED","ALLOCATED","PICKING","SHIPPED","INVOICED","CANCELLED"].map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>
      <div className="bg-white rounded-xl border shadow-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-xs text-gray-600">
              <th className="px-3 py-2 text-left">Order No</th>
              <th className="px-3 py-2 text-left">Date</th>
              <th className="px-3 py-2 text-left">Delivery Date</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Payment</th>
              <th className="px-3 py-2 text-left">Lines</th>
            </tr>
          </thead>
          <tbody>
            {orders.length === 0 && <tr><td colSpan={6} className="px-3 py-6 text-center text-gray-400">No orders found</td></tr>}
            {orders.map((o, i) => (
              <tr key={i} className="border-b hover:bg-gray-50">
                <td className="px-3 py-2 font-mono text-xs text-blue-600">{o.order_no as string}</td>
                <td className="px-3 py-2 text-xs text-gray-600">{o.order_date as string}</td>
                <td className="px-3 py-2 text-xs text-gray-600">{o.requested_delivery_date as string}</td>
                <td className="px-3 py-2 text-xs"><span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">{o.status as string}</span></td>
                <td className="px-3 py-2 text-xs text-gray-500">{o.payment_status as string}</td>
                <td className="px-3 py-2 text-xs text-gray-500">{o.line_count as number}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PortalShipmentsView({ accountId }: { accountId: string }) {
  const [shipments, setShipments] = useState<Record<string, unknown>[]>([]);
  useEffect(() => {
    portalApi.getShipments(accountId).then(d => setShipments(d as Record<string, unknown>[])).catch(console.error);
  }, [accountId]);

  const statusColors: Record<string, string> = {
    PENDING: "#F59E0B", PICKING: "#3B82F6", PACKED: "#8B5CF6",
    DISPATCHED: "#F97316", DELIVERED: "#10B981", CANCELLED: "#EF4444",
  };

  return (
    <div className="bg-white rounded-xl border shadow-sm overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-gray-50 text-xs text-gray-600">
            <th className="px-3 py-2 text-left">Shipment No</th>
            <th className="px-3 py-2 text-left">Status</th>
            <th className="px-3 py-2 text-left">Scheduled</th>
            <th className="px-3 py-2 text-left">Dispatched</th>
            <th className="px-3 py-2 text-left">Carrier</th>
            <th className="px-3 py-2 text-left">Tracking</th>
          </tr>
        </thead>
        <tbody>
          {shipments.length === 0 && <tr><td colSpan={6} className="px-3 py-6 text-center text-gray-400">No shipments</td></tr>}
          {shipments.map((s, i) => (
            <tr key={i} className="border-b hover:bg-gray-50">
              <td className="px-3 py-2 font-mono text-xs text-blue-600">{s.shipment_no as string}</td>
              <td className="px-3 py-2">
                <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                  style={{ background: (statusColors[s.status as string] || "#6B7280") + "22", color: statusColors[s.status as string] || "#6B7280" }}>
                  {s.status as string}
                </span>
              </td>
              <td className="px-3 py-2 text-xs text-gray-600">{s.scheduled_date as string}</td>
              <td className="px-3 py-2 text-xs text-gray-600">{s.dispatched_date as string || "—"}</td>
              <td className="px-3 py-2 text-xs text-gray-500">{s.carrier as string || "—"}</td>
              <td className="px-3 py-2 text-xs text-gray-500">{s.tracking_number as string || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PortalInvoicesView({ accountId }: { accountId: string }) {
  const [invoices, setInvoices] = useState<Record<string, unknown>[]>([]);
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    portalApi.getInvoices(accountId, { status: statusFilter || undefined })
      .then(d => setInvoices(d as Record<string, unknown>[])).catch(console.error);
  }, [accountId, statusFilter]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="text-sm border rounded-lg px-2 py-1.5 bg-white">
          <option value="">All Statuses</option>
          {["DRAFT","ISSUED","PARTIALLY_PAID","PAID","OVERDUE","CANCELLED"].map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>
      <div className="bg-white rounded-xl border shadow-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-xs text-gray-600">
              <th className="px-3 py-2 text-left">Invoice No</th>
              <th className="px-3 py-2 text-left">Date</th>
              <th className="px-3 py-2 text-left">Due</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-right">Total</th>
              <th className="px-3 py-2 text-right">Paid</th>
              <th className="px-3 py-2 text-right">Outstanding</th>
            </tr>
          </thead>
          <tbody>
            {invoices.length === 0 && <tr><td colSpan={7} className="px-3 py-6 text-center text-gray-400">No invoices</td></tr>}
            {invoices.map((inv, i) => (
              <tr key={i} className="border-b hover:bg-gray-50">
                <td className="px-3 py-2 font-mono text-xs text-blue-600">{inv.invoice_no as string}</td>
                <td className="px-3 py-2 text-xs text-gray-600">{inv.invoice_date as string}</td>
                <td className="px-3 py-2 text-xs text-gray-600">{inv.due_date as string}</td>
                <td className="px-3 py-2 text-xs text-gray-600">{inv.status as string}</td>
                <td className="px-3 py-2 text-xs text-right text-gray-800">{fmtCurrency(inv.total_amount as number)}</td>
                <td className="px-3 py-2 text-xs text-right text-green-700">{fmtCurrency(inv.paid_amount as number)}</td>
                <td className="px-3 py-2 text-xs text-right font-semibold text-red-700">{fmtCurrency(inv.outstanding as number)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PortalPaymentsView({ accountId, account }: { accountId: string; account: PortalAccount }) {
  const [payments, setPayments] = useState<Record<string, unknown>[]>([]);
  useEffect(() => {
    portalApi.getPayments(accountId).then(d => setPayments(d as Record<string, unknown>[])).catch(console.error);
  }, [accountId]);

  return (
    <div className="space-y-4">
      {account.can_initiate_payment && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <div className="font-medium text-blue-800 text-sm">Initiate Payment</div>
          <p className="text-xs text-blue-600 mt-1">Payment initiation is enabled for this account. Contact your account manager for payment instructions or use M-Pesa/bank transfer.</p>
        </div>
      )}
      <div className="bg-white rounded-xl border shadow-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-xs text-gray-600">
              <th className="px-3 py-2 text-left">Date</th>
              <th className="px-3 py-2 text-left">Method</th>
              <th className="px-3 py-2 text-left">Reference</th>
              <th className="px-3 py-2 text-right">Amount</th>
            </tr>
          </thead>
          <tbody>
            {payments.length === 0 && <tr><td colSpan={4} className="px-3 py-6 text-center text-gray-400">No payment history</td></tr>}
            {payments.map((p, i) => (
              <tr key={i} className="border-b hover:bg-gray-50">
                <td className="px-3 py-2 text-xs text-gray-600">{p.payment_date as string}</td>
                <td className="px-3 py-2 text-xs text-gray-600 capitalize">{p.method as string}</td>
                <td className="px-3 py-2 font-mono text-xs text-gray-500">{p.reference as string || "—"}</td>
                <td className="px-3 py-2 text-xs text-right font-semibold text-green-700">{fmtCurrency(p.amount as number)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PortalStatementView({ accountId }: { accountId: string }) {
  const [statement, setStatement] = useState<Record<string, unknown> | null>(null);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const load = () => {
    portalApi.getStatement(accountId, {
      from_date: from || undefined,
      to_date: to || undefined,
    }).then(d => setStatement(d as Record<string, unknown>)).catch(console.error);
  };

  useEffect(() => { load(); }, [accountId]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <input type="date" value={from} onChange={e => setFrom(e.target.value)}
          className="text-sm border rounded-lg px-2 py-1.5 bg-white" />
        <span className="text-gray-400 text-sm">to</span>
        <input type="date" value={to} onChange={e => setTo(e.target.value)}
          className="text-sm border rounded-lg px-2 py-1.5 bg-white" />
        <button onClick={load} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          Generate Statement
        </button>
      </div>

      {statement && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-white rounded-xl border shadow-sm p-4">
              <div className="text-xs text-gray-500">Total Invoiced</div>
              <div className="text-xl font-bold text-gray-800">{fmtCurrency(statement.total_invoiced as number)}</div>
            </div>
            <div className="bg-white rounded-xl border shadow-sm p-4">
              <div className="text-xs text-gray-500">Total Paid</div>
              <div className="text-xl font-bold text-green-700">{fmtCurrency(statement.total_paid as number)}</div>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-xl p-4">
              <div className="text-xs text-gray-500">Outstanding Balance</div>
              <div className="text-xl font-bold text-red-700">{fmtCurrency(statement.outstanding_balance as number)}</div>
            </div>
          </div>

          <div className="bg-white rounded-xl border shadow-sm p-4">
            <h2 className="font-semibold text-gray-800 mb-3 text-sm">Invoices in Period</h2>
            <div className="space-y-1">
              {(statement.invoices as Record<string, unknown>[]).map((inv, i) => (
                <div key={i} className="flex justify-between text-xs py-1 border-b last:border-0">
                  <span className="font-mono text-blue-600">{inv.invoice_no as string}</span>
                  <span className="text-gray-500">{inv.invoice_date as string}</span>
                  <span className="text-gray-800">{fmtCurrency(inv.total_amount as number)}</span>
                  <span className={`font-medium ${(inv.outstanding as number) > 0 ? "text-red-700" : "text-green-700"}`}>
                    {(inv.outstanding as number) > 0 ? `Outstanding: ${fmtCurrency(inv.outstanding as number)}` : "Paid"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function PortalClaimsView({ accountId }: { accountId: string }) {
  const [claims, setClaims] = useState<PortalClaim[]>([]);
  const [showClaim, setShowClaim] = useState(false);
  const [claimForm, setClaimForm] = useState({ claim_type: "SHORTAGE_CLAIM", linked_order_id: "", reason: "", description: "" });
  const [saving, setSaving] = useState(false);

  const load = () => {
    portalApi.getClaims(accountId).then(d => setClaims(d as PortalClaim[])).catch(console.error);
  };

  useEffect(() => { load(); }, [accountId]);

  const handleSubmit = async () => {
    setSaving(true);
    try {
      await portalApi.submitClaim(accountId, claimForm as Partial<PortalClaim>);
      setShowClaim(false);
      load();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  return (
    <div className="space-y-3">
      <button onClick={() => setShowClaim(true)}
        className="px-3 py-1.5 text-sm bg-orange-600 text-white rounded-lg hover:bg-orange-700">
        + Submit New Claim
      </button>
      <div className="space-y-2">
        {claims.length === 0 && <p className="text-sm text-gray-400">No claims submitted</p>}
        {claims.map(claim => (
          <div key={claim.id} className="bg-white rounded-xl border shadow-sm p-4">
            <div className="flex items-start justify-between">
              <div>
                <div className="font-medium text-gray-800 text-sm">{CLAIM_TYPE_LABELS[claim.claim_type]}</div>
                <div className="text-xs text-gray-400 mt-0.5">{claim.claim_no} · {claim.created_at ? new Date(claim.created_at).toLocaleDateString() : ""}</div>
                <p className="text-xs text-gray-600 mt-1">{claim.reason}</p>
                {claim.resolution_notes && (
                  <p className="text-xs text-green-600 mt-1">Resolution: {claim.resolution_notes}</p>
                )}
              </div>
              <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                style={{ background: CLAIM_STATUS_COLORS[claim.status] + "22", color: CLAIM_STATUS_COLORS[claim.status] }}>
                {claim.status}
              </span>
            </div>
          </div>
        ))}
      </div>

      {showClaim && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md space-y-3">
            <h2 className="font-semibold text-lg">Submit Claim</h2>
            <select value={claimForm.claim_type} onChange={e => setClaimForm(f => ({ ...f, claim_type: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm">
              {Object.entries(CLAIM_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <input placeholder="Linked Order No / ID" value={claimForm.linked_order_id}
              onChange={e => setClaimForm(f => ({ ...f, linked_order_id: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
            <textarea placeholder="Reason *" value={claimForm.reason}
              onChange={e => setClaimForm(f => ({ ...f, reason: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} />
            <textarea placeholder="Description / Details" value={claimForm.description}
              onChange={e => setClaimForm(f => ({ ...f, description: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} />
            <div className="flex gap-2 pt-1">
              <button onClick={handleSubmit} disabled={saving || !claimForm.reason}
                className="flex-1 bg-orange-600 text-white py-2 rounded-lg text-sm disabled:opacity-50">
                {saving ? "Submitting…" : "Submit Claim"}
              </button>
              <button onClick={() => setShowClaim(false)} className="flex-1 border rounded-lg py-2 text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function PortalNewOrderView({ accountId }: { accountId: string }) {
  const [lines, setLines] = useState<{ product_name: string; product_sku: string; quantity: string; unit: string; unit_price: string }[]>([
    { product_name: "", product_sku: "", quantity: "", unit: "PCS", unit_price: "" },
  ]);
  const [delivery_date, setDeliveryDate] = useState("");
  const [delivery_address, setDeliveryAddress] = useState("");
  const [comments, setComments] = useState("");
  const [saving, setSaving] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const addLine = () => setLines(l => [...l, { product_name: "", product_sku: "", quantity: "", unit: "PCS", unit_price: "" }]);
  const removeLine = (i: number) => setLines(l => l.filter((_, idx) => idx !== i));

  const handleSubmit = async () => {
    setSaving(true);
    try {
      const payload = {
        requested_delivery_date: delivery_date || undefined,
        delivery_address: delivery_address || undefined,
        order_comments: comments || undefined,
        currency: "KES",
        lines: lines.filter(l => l.product_name && l.quantity).map(l => ({
          product_name: l.product_name,
          product_sku: l.product_sku || undefined,
          quantity: parseFloat(l.quantity),
          unit: l.unit,
          unit_price: l.unit_price ? parseFloat(l.unit_price) : 0,
        })),
      };
      const draft = await portalApi.createDraftOrder(accountId, payload);
      await portalApi.submitDraftOrder(accountId, (draft as { id: string }).id);
      setSubmitted(true);
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  if (submitted) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
        <div className="text-green-700 text-lg font-semibold">Order Request Submitted!</div>
        <p className="text-sm text-gray-500 mt-1">Your order request has been submitted for review. You will be notified when it is approved.</p>
        <button onClick={() => { setSubmitted(false); setLines([{ product_name: "", product_sku: "", quantity: "", unit: "PCS", unit_price: "" }]); }}
          className="mt-3 px-4 py-2 text-sm bg-green-600 text-white rounded-lg">Place Another Order</button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl border shadow-sm p-4 space-y-3">
        <h2 className="font-semibold text-gray-800">New Order Request</h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Delivery Date</label>
            <input type="date" value={delivery_date} onChange={e => setDeliveryDate(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
        </div>
        <div>
          <label className="text-xs text-gray-500 mb-1 block">Delivery Address</label>
          <textarea value={delivery_address} onChange={e => setDeliveryAddress(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} placeholder="Delivery address" />
        </div>

        {/* Order Lines */}
        <div>
          <label className="text-xs text-gray-500 mb-2 block">Order Lines</label>
          <div className="space-y-2">
            {lines.map((line, i) => (
              <div key={i} className="flex items-center gap-2">
                <input placeholder="Product Name" value={line.product_name}
                  onChange={e => setLines(l => l.map((x, idx) => idx === i ? { ...x, product_name: e.target.value } : x))}
                  className="flex-1 border rounded-lg px-2 py-1.5 text-sm" />
                <input placeholder="SKU" value={line.product_sku}
                  onChange={e => setLines(l => l.map((x, idx) => idx === i ? { ...x, product_sku: e.target.value } : x))}
                  className="w-24 border rounded-lg px-2 py-1.5 text-sm" />
                <input type="number" placeholder="Qty" value={line.quantity}
                  onChange={e => setLines(l => l.map((x, idx) => idx === i ? { ...x, quantity: e.target.value } : x))}
                  className="w-20 border rounded-lg px-2 py-1.5 text-sm" />
                <select value={line.unit} onChange={e => setLines(l => l.map((x, idx) => idx === i ? { ...x, unit: e.target.value } : x))}
                  className="w-16 border rounded-lg px-1 py-1.5 text-sm">
                  {["PCS","KG","CTN","BOX","PKT"].map(u => <option key={u}>{u}</option>)}
                </select>
                <button onClick={() => removeLine(i)} className="text-red-400 hover:text-red-600 text-lg">×</button>
              </div>
            ))}
          </div>
          <button onClick={addLine} className="mt-2 text-xs text-blue-600 hover:underline">+ Add Line</button>
        </div>

        <textarea placeholder="Order comments…" value={comments} onChange={e => setComments(e.target.value)}
          className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} />

        <button onClick={handleSubmit} disabled={saving || lines.every(l => !l.product_name || !l.quantity)}
          className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
          {saving ? "Submitting…" : "Submit Order Request"}
        </button>
      </div>
    </div>
  );
}
