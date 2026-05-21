"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { scApi, SCOrderOut, SCOrderStatus, orderStatusBadge, fmt } from "@/lib/subcontracting";

const STATUS_OPTIONS: (SCOrderStatus|"")[] = ["","DRAFT","APPROVED","ISSUED","IN_PROGRESS","PARTIALLY_RECEIVED","COMPLETED","CLOSED","CANCELLED"];

function OrderDetail({ orderId }: { orderId: string }) {
  const qc = useQueryClient();
  const { data: order, isLoading } = useQuery({ queryKey: ["sc-order", orderId], queryFn: () => scApi.getOrder(orderId) });
  const { data: issues } = useQuery({ queryKey: ["sc-issues", orderId], queryFn: () => scApi.listIssues(orderId) });
  const { data: receipts } = useQuery({ queryKey: ["sc-receipts", orderId], queryFn: () => scApi.listReceipts(orderId) });
  const { data: yieldRecs } = useQuery({ queryKey: ["sc-yield", orderId], queryFn: () => scApi.getYield(orderId) });

  const approve = useMutation({ mutationFn: () => scApi.approveOrder(orderId), onSuccess: () => qc.invalidateQueries({ queryKey: ["sc-order", orderId] }) });
  const complete = useMutation({ mutationFn: () => scApi.completeOrder(orderId), onSuccess: () => qc.invalidateQueries({ queryKey: ["sc-order", orderId] }) });

  if (isLoading || !order) return <div className="p-6 text-gray-400">Loading order…</div>;

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 font-mono">{order.order_no}</h2>
          <p className="text-sm text-gray-500">{order.supplier_name} · {order.order_date}</p>
        </div>
        <div className="flex gap-2">
          <span className={`px-2 py-1 rounded-full text-xs ${orderStatusBadge(order.status)}`}>{order.status}</span>
          {order.status === "DRAFT" && (
            <button onClick={() => approve.mutate()} disabled={approve.isPending}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              Approve
            </button>
          )}
          {["ISSUED","IN_PROGRESS","PARTIALLY_RECEIVED"].includes(order.status) && (
            <button onClick={() => complete.mutate()} disabled={complete.isPending}
              className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50">
              Complete Order
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 bg-white border rounded-lg p-4 text-sm">
        <div><p className="text-gray-500 text-xs">Expected Completion</p><p className="font-medium">{order.expected_completion_date ?? "—"}</p></div>
        <div><p className="text-gray-500 text-xs">Material Cost</p><p className="font-medium">{order.total_material_cost ? `KES ${fmt(order.total_material_cost, 0)}` : "—"}</p></div>
        <div><p className="text-gray-500 text-xs">Service Cost</p><p className="font-medium">{order.total_service_cost ? `KES ${fmt(order.total_service_cost, 0)}` : "—"}</p></div>
        <div><p className="text-gray-500 text-xs">Wastage Cost</p><p className="font-medium text-orange-600">{order.total_wastage_cost ? `KES ${fmt(order.total_wastage_cost, 0)}` : "—"}</p></div>
        <div><p className="text-gray-500 text-xs">SC Location</p><p className="font-medium">{order.subcontractor_location_id ? "Configured" : <span className="text-red-500">Not configured</span>}</p></div>
        <div><p className="text-gray-500 text-xs">Remarks</p><p className="font-medium">{order.remarks ?? "—"}</p></div>
      </div>

      {/* Order Lines */}
      <div className="bg-white border border-gray-200 rounded-lg">
        <div className="px-4 py-3 border-b border-gray-100"><h3 className="text-sm font-semibold">Order Lines (What to Produce)</h3></div>
        <table className="w-full text-xs">
          <thead className="bg-gray-50 text-gray-500 uppercase"><tr>
            <th className="text-left px-4 py-2">#</th><th className="text-left px-4 py-2">Item</th>
            <th className="text-right px-4 py-2">Ordered</th><th className="text-right px-4 py-2">Received</th>
            <th className="text-right px-4 py-2">Yield %</th><th className="text-right px-4 py-2">Service Cost/U</th>
          </tr></thead>
          <tbody>{order.lines.map((l) => (
            <tr key={l.id} className="border-t border-gray-100">
              <td className="px-4 py-2">{l.line_no}</td>
              <td className="px-4 py-2 font-medium">{l.product_name ?? l.material_name ?? l.description ?? "—"}</td>
              <td className="px-4 py-2 text-right">{fmt(l.quantity_ordered)} {l.uom}</td>
              <td className={`px-4 py-2 text-right font-semibold ${Number(l.quantity_received) >= Number(l.quantity_ordered) ? "text-green-600" : "text-gray-700"}`}>
                {fmt(l.quantity_received)}
              </td>
              <td className="px-4 py-2 text-right">{l.estimated_yield_pct != null ? `${l.estimated_yield_pct}%` : "—"}</td>
              <td className="px-4 py-2 text-right">{l.service_unit_cost ? fmt(l.service_unit_cost) : "—"}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>

      {/* Material Issues */}
      {issues && issues.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg">
          <div className="px-4 py-3 border-b border-gray-100"><h3 className="text-sm font-semibold">Material Issues ({issues.length})</h3></div>
          {issues.map((iss) => (
            <div key={iss.id} className="border-t border-gray-100 p-4">
              <p className="text-sm font-medium font-mono mb-2">{iss.issue_no} — {iss.issue_date}
                <span className={`ml-2 px-2 py-0.5 rounded text-xs bg-blue-100 text-blue-700`}>{iss.status}</span>
              </p>
              <table className="w-full text-xs">
                <thead className="bg-gray-50 text-gray-500 uppercase"><tr>
                  <th className="text-left px-3 py-1">Material</th><th className="text-right px-3 py-1">Issued</th>
                  <th className="text-right px-3 py-1">Returned</th><th className="text-right px-3 py-1">Consumed</th>
                  <th className="text-right px-3 py-1">Scrapped</th>
                </tr></thead>
                <tbody>{iss.lines.map((l) => (
                  <tr key={l.id} className="border-t border-gray-100">
                    <td className="px-3 py-1">{l.material_name} <span className="text-gray-400 font-mono">{l.material_code}</span></td>
                    <td className="px-3 py-1 text-right">{fmt(l.quantity_issued)} {l.uom}</td>
                    <td className="px-3 py-1 text-right">{fmt(l.quantity_returned)}</td>
                    <td className="px-3 py-1 text-right">{fmt(l.quantity_consumed)}</td>
                    <td className={`px-3 py-1 text-right ${Number(l.quantity_scrapped) > 0 ? "text-red-600" : ""}`}>{fmt(l.quantity_scrapped)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          ))}
        </div>
      )}

      {/* Receipts */}
      {receipts && receipts.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg">
          <div className="px-4 py-3 border-b border-gray-100"><h3 className="text-sm font-semibold">Goods Receipts ({receipts.length})</h3></div>
          {receipts.map((r) => (
            <div key={r.id} className="border-t border-gray-100 p-4">
              <p className="text-sm font-medium font-mono mb-2">{r.receipt_no} — {r.receipt_date}</p>
              <table className="w-full text-xs">
                <thead className="bg-gray-50 text-gray-500 uppercase"><tr>
                  <th className="text-left px-3 py-1">Item</th><th className="text-right px-3 py-1">Received</th>
                  <th className="text-right px-3 py-1">Accepted</th><th className="text-right px-3 py-1">Rejected</th>
                  <th className="text-left px-3 py-1">Lot</th>
                </tr></thead>
                <tbody>{r.lines.map((l) => (
                  <tr key={l.id} className="border-t border-gray-100">
                    <td className="px-3 py-1">{l.product_name ?? l.material_name ?? "—"}</td>
                    <td className="px-3 py-1 text-right">{fmt(l.quantity_received)}</td>
                    <td className="px-3 py-1 text-right text-green-600 font-medium">{fmt(l.quantity_accepted)}</td>
                    <td className={`px-3 py-1 text-right ${Number(l.quantity_rejected) > 0 ? "text-red-600" : ""}`}>{fmt(l.quantity_rejected)}</td>
                    <td className="px-3 py-1 text-gray-500">{l.lot_number ?? "—"}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          ))}
        </div>
      )}

      {/* Yield */}
      {yieldRecs && yieldRecs.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg">
          <div className="px-4 py-3 border-b border-gray-100"><h3 className="text-sm font-semibold">Yield Analysis</h3></div>
          {yieldRecs.map((y) => (
            <div key={y.id} className="px-4 py-3 border-t border-gray-100 text-sm">
              <div className="grid grid-cols-4 gap-4">
                <div><p className="text-xs text-gray-500">Actual Yield</p>
                  <p className={`font-bold text-lg ${Number(y.actual_yield_pct ?? 0) < 90 ? "text-red-600" : "text-green-600"}`}>
                    {y.actual_yield_pct != null ? `${fmt(y.actual_yield_pct, 1)}%` : "—"}
                  </p></div>
                <div><p className="text-xs text-gray-500">Expected</p><p className="font-medium">{y.expected_yield_pct != null ? `${y.expected_yield_pct}%` : "—"}</p></div>
                <div><p className="text-xs text-gray-500">Variance</p>
                  <p className={`font-medium ${Number(y.yield_variance_pct ?? 0) < 0 ? "text-red-600" : "text-green-600"}`}>
                    {y.yield_variance_pct != null ? `${Number(y.yield_variance_pct) >= 0 ? "+" : ""}${fmt(y.yield_variance_pct, 1)}%` : "—"}
                  </p></div>
                <div><p className="text-xs text-gray-500">Scrapped</p>
                  <p className={`font-medium ${Number(y.total_scrapped) > 0 ? "text-orange-600" : "text-gray-700"}`}>{fmt(y.total_scrapped)}</p></div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function NewOrderModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    supplier_id: "", order_date: new Date().toISOString().split("T")[0],
    expected_completion_date: "", warehouse_id: "", currency: "KES", remarks: "",
  });

  const create = useMutation({
    mutationFn: () => scApi.createOrder({ ...form, lines: [] }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sc-orders"] }); onClose(); },
  });

  const f = (k: string, v: string) => setForm((p) => ({ ...p, [k]: v }));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-96 space-y-3 shadow-xl">
        <h2 className="font-semibold text-gray-900">New Subcontracting Order</h2>
        {[["Supplier ID","supplier_id"],["Order Date","order_date","date"],["Expected Completion","expected_completion_date","date"],
          ["Source Warehouse ID","warehouse_id"],["Currency","currency"],["Remarks","remarks"],
        ].map(([label, key, type = "text"]) => (
          <div key={key}><label className="text-xs text-gray-600">{label}</label>
            <input type={type} value={(form as Record<string,string>)[key]} onChange={(e) => f(key, e.target.value)}
              className="w-full border rounded px-2 py-1.5 text-sm mt-0.5" /></div>
        ))}
        <div className="flex gap-2 pt-2">
          <button onClick={() => create.mutate()} disabled={!form.supplier_id || create.isPending}
            className="flex-1 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50">
            {create.isPending ? "Creating…" : "Create Order"}
          </button>
          <button onClick={onClose} className="flex-1 py-2 border rounded text-sm hover:bg-gray-50">Cancel</button>
        </div>
      </div>
    </div>
  );
}

export default function OrdersPage() {
  const params = useSearchParams();
  const selectedId = params.get("id");
  const [statusFilter, setStatusFilter] = useState<SCOrderStatus|"">("");
  const [showNew, setShowNew] = useState(false);

  const { data: orders, isLoading } = useQuery({
    queryKey: ["sc-orders", statusFilter],
    queryFn: () => scApi.listOrders({ status: statusFilter || undefined }),
  });

  if (selectedId) return <OrderDetail orderId={selectedId} />;

  return (
    <div className="p-6 space-y-4">
      {showNew && <NewOrderModal onClose={() => setShowNew(false)} />}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Subcontracting Orders</h1>
          <p className="text-sm text-gray-500">Manage external manufacturing orders</p>
        </div>
        <div className="flex gap-2">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as SCOrderStatus|"")}
            className="border rounded px-2 py-1.5 text-sm">
            {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s || "All Statuses"}</option>)}
          </select>
          <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700">
            + New Order
          </button>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="text-left px-4 py-2">Order No</th><th className="text-left px-4 py-2">Supplier</th>
              <th className="text-left px-4 py-2">Date</th><th className="text-left px-4 py-2">Due</th>
              <th className="text-left px-4 py-2">Status</th><th className="text-right px-4 py-2">Items</th>
              <th className="text-right px-4 py-2">Service Cost</th><th className="text-left px-4 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>}
            {!isLoading && !orders?.length && <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No orders found.</td></tr>}
            {(orders ?? []).map((o) => (
              <tr key={o.id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2 font-mono font-medium text-blue-700">{o.order_no}</td>
                <td className="px-4 py-2">{o.supplier_name}</td>
                <td className="px-4 py-2 text-gray-500">{o.order_date}</td>
                <td className={`px-4 py-2 ${o.expected_completion_date && o.expected_completion_date < new Date().toISOString().split("T")[0] && ["ISSUED","IN_PROGRESS"].includes(o.status) ? "text-red-600 font-medium" : "text-gray-500"}`}>
                  {o.expected_completion_date ?? "—"}
                </td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${orderStatusBadge(o.status)}`}>{o.status}</span>
                </td>
                <td className="px-4 py-2 text-right">{o.lines.length}</td>
                <td className="px-4 py-2 text-right">{o.total_service_cost ? `KES ${fmt(o.total_service_cost, 0)}` : "—"}</td>
                <td className="px-4 py-2">
                  <a href={`/dashboard/subcontracting/orders?id=${o.id}`} className="text-blue-600 hover:underline text-xs">Manage →</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
