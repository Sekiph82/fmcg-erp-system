"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  execApi, ExecDashboard, ProdExecOrderSummary, ProdExecStatus,
  STATUS_COLOR, LIFECYCLE_NEXT, fmtKES,
} from "@/lib/productionExecution";

const STATUSES: ProdExecStatus[] = ["DRAFT", "PLANNED", "RELEASED", "IN_PROGRESS", "PAUSED", "COMPLETED", "CLOSED", "CANCELLED"];
const SOURCES = ["MANUAL", "MRP", "MPS", "SALES", "SUBCONTRACT_RETURN"];
const UOMS = ["KG", "L", "UNIT", "MT", "G", "ML"];

const emptyForm = {
  product_name: "", planned_qty: "1000", uom: "KG",
  source_type: "MANUAL", priority: "5",
  planned_start: "", planned_end: "",
  batch_no: "", remarks: "",
};

export default function ProductionExecutionPage() {
  const qc = useQueryClient();
  const [filterStatus, setFilterStatus] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState(emptyForm);

  const { data: dashboard } = useQuery<ExecDashboard>({
    queryKey: ["exec-dashboard"],
    queryFn: () => execApi.dashboard(),
  });

  const { data: orders = [], isLoading } = useQuery<ProdExecOrderSummary[]>({
    queryKey: ["exec-orders", filterStatus],
    queryFn: () => execApi.list({ status: filterStatus || undefined }),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["exec-orders"] });
    qc.invalidateQueries({ queryKey: ["exec-dashboard"] });
  };

  const create = useMutation({
    mutationFn: () => execApi.create({
      ...form,
      planned_qty: Number(form.planned_qty),
      priority: Number(form.priority),
      planned_start: form.planned_start || undefined,
      planned_end: form.planned_end || undefined,
      batch_no: form.batch_no || undefined,
      remarks: form.remarks || undefined,
    } as any),
    onSuccess: () => { invalidate(); setShowCreate(false); setForm(emptyForm); },
  });

  const advance = useMutation({
    mutationFn: (id: string) => execApi.advance(id),
    onSuccess: invalidate,
  });

  const cancel = useMutation({
    mutationFn: (id: string) => execApi.cancel(id),
    onSuccess: invalidate,
  });

  const progressPct = (o: ProdExecOrderSummary) =>
    o.planned_qty > 0 ? Math.min(100, Math.round((o.completed_qty / o.planned_qty) * 100)) : 0;

  const isDelayed = (o: ProdExecOrderSummary) =>
    o.planned_end && new Date(o.planned_end) < new Date() &&
    !["COMPLETED", "CLOSED", "CANCELLED"].includes(o.status);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Production Execution</h1>
          <p className="text-sm text-gray-500 mt-0.5">Production Orders · Work Orders · Batch Traceability</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700">
          + New Order
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
        {[
          { label: "Total Orders",   value: dashboard?.total_orders ?? 0,      color: "text-gray-900" },
          { label: "Draft",          value: dashboard?.draft_orders ?? 0,       color: "text-gray-500" },
          { label: "Released",       value: dashboard?.released_orders ?? 0,    color: "text-indigo-600" },
          { label: "In Progress",    value: dashboard?.in_progress_orders ?? 0, color: "text-yellow-600" },
          { label: "Done Today",     value: dashboard?.completed_today ?? 0,    color: "text-green-600" },
          { label: "Delayed",        value: dashboard?.delayed_orders ?? 0,     color: "text-red-600" },
          { label: "Active WOs",     value: dashboard?.active_work_orders ?? 0, color: "text-purple-600" },
          { label: "Scrap (units)",  value: dashboard?.total_scrap_qty?.toFixed(1) ?? 0, color: "text-orange-600" },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-3">
            <p className="text-xs text-gray-400">{k.label}</p>
            <p className={`text-xl font-bold mt-0.5 ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm"
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
        >
          <option value="">All Statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <a href="/dashboard/production-execution/work-orders" className="text-sm text-indigo-600 hover:underline ml-auto">
          Work Order Queue →
        </a>
      </div>

      {/* Orders Table */}
      {isLoading ? (
        <div className="text-center text-gray-400 py-8">Loading…</div>
      ) : orders.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center text-sm text-gray-400">
          No production orders found. Create your first order to begin execution.
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["Order #", "Product", "Batch", "Qty", "Progress", "Schedule", "Status", "Cost", ""].map((h) => (
                  <th key={h} className="px-3 py-3 text-left font-medium text-gray-400 text-xs">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {orders.map((o) => (
                <tr key={o.id} className={`hover:bg-gray-50 ${isDelayed(o) ? "bg-red-50/30" : ""}`}>
                  <td className="px-3 py-2">
                    <a href={`/dashboard/production-execution/${o.id}`} className="font-mono text-xs text-indigo-600 hover:underline">
                      {o.order_no}
                    </a>
                    <div className="flex gap-1 mt-0.5">
                      {o.is_rework && <span className="text-xs bg-orange-100 text-orange-700 px-1 rounded">REWORK</span>}
                      {o.is_split && <span className="text-xs bg-blue-100 text-blue-700 px-1 rounded">SPLIT</span>}
                    </div>
                  </td>
                  <td className="px-3 py-2">
                    <p className="font-medium">{o.product_name || "—"}</p>
                    {o.bom_code && <p className="text-xs text-gray-400">{o.bom_code}</p>}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-gray-500">{o.batch_no || "—"}</td>
                  <td className="px-3 py-2 text-right text-xs font-mono">
                    {Number(o.planned_qty).toLocaleString()} {o.uom}
                  </td>
                  <td className="px-3 py-2 w-32">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${progressPct(o) >= 100 ? "bg-green-500" : "bg-indigo-500"}`}
                          style={{ width: `${progressPct(o)}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-400 w-7">{progressPct(o)}%</span>
                    </div>
                    {o.scrap_qty > 0 && (
                      <p className="text-xs text-red-500 mt-0.5">Scrap: {Number(o.scrap_qty).toFixed(2)} {o.uom}</p>
                    )}
                  </td>
                  <td className="px-3 py-2 text-xs">
                    {o.planned_start && <p className="text-gray-400">{new Date(o.planned_start).toLocaleDateString()}</p>}
                    {o.planned_end && (
                      <p className={isDelayed(o) ? "text-red-600 font-medium" : "text-gray-400"}>
                        → {new Date(o.planned_end).toLocaleDateString()}
                        {isDelayed(o) && " ⚠"}
                      </p>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <span className={`text-xs px-1.5 py-0.5 rounded ${STATUS_COLOR[o.status]}`}>{o.status}</span>
                  </td>
                  <td className="px-3 py-2 text-right text-xs">
                    {o.total_actual_cost > 0 ? fmtKES(Number(o.total_actual_cost)) : "—"}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <a href={`/dashboard/production-execution/${o.id}`} className="text-xs text-blue-600 hover:underline">View</a>
                      {LIFECYCLE_NEXT[o.status] && (
                        <button onClick={() => advance.mutate(o.id)} disabled={advance.isPending} className="text-xs text-indigo-600 hover:underline">
                          {LIFECYCLE_NEXT[o.status]}
                        </button>
                      )}
                      {!["COMPLETED", "CLOSED", "CANCELLED"].includes(o.status) && (
                        <button onClick={() => cancel.mutate(o.id)} className="text-xs text-red-400 hover:text-red-600">Cancel</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">New Production Order</h2>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="space-y-3">
              <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Product Name" value={form.product_name} onChange={(e) => setForm({ ...form, product_name: e.target.value })} />
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="text-xs text-gray-500 mb-1 block">Planned Qty *</label>
                  <input type="number" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={form.planned_qty} onChange={(e) => setForm({ ...form, planned_qty: e.target.value })} />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">UOM</label>
                  <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={form.uom} onChange={(e) => setForm({ ...form, uom: e.target.value })}>
                    {UOMS.map((u) => <option key={u} value={u}>{u}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Source</label>
                  <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={form.source_type} onChange={(e) => setForm({ ...form, source_type: e.target.value })}>
                    {SOURCES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Priority (1=high, 10=low)</label>
                  <input type="number" min={1} max={10} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Planned Start</label>
                  <input type="datetime-local" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={form.planned_start} onChange={(e) => setForm({ ...form, planned_start: e.target.value })} />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Planned End</label>
                  <input type="datetime-local" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={form.planned_end} onChange={(e) => setForm({ ...form, planned_end: e.target.value })} />
                </div>
              </div>
              <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Batch No (auto-generated if blank)" value={form.batch_no} onChange={(e) => setForm({ ...form, batch_no: e.target.value })} />
              <textarea className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" rows={2} placeholder="Remarks" value={form.remarks} onChange={(e) => setForm({ ...form, remarks: e.target.value })} />
            </div>
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => create.mutate()}
                disabled={!form.planned_qty || create.isPending}
                className="flex-1 bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-40"
              >
                {create.isPending ? "Creating…" : "Create Order"}
              </button>
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
