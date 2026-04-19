"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { sfApi, ShiftHandover } from "@/lib/shopFloor";

export default function ShiftHandoverPage() {
  const qc = useQueryClient();
  const [lineFilter, setLineFilter] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [approvedBy, setApprovedBy] = useState("");

  // Form state
  const [form, setForm] = useState({
    line_id: "",
    shift_from_name: "",
    shift_to_name: "",
    outgoing_supervisor: "",
    incoming_supervisor: "",
    outgoing_operators_str: "",
    incoming_operators_str: "",
    qty_completed: "",
    qty_remaining: "",
    issues_str: "",
    qc_pending_str: "",
    material_shortages_str: "",
    notes: "",
  });

  const { data: handovers = [], isLoading } = useQuery<ShiftHandover[]>({
    queryKey: ["sf-handovers", lineFilter],
    queryFn: () => sfApi.listHandovers(lineFilter || undefined),
  });

  const createMut = useMutation({
    mutationFn: () => sfApi.createHandover({
      line_id: form.line_id || null,
      shift_from_name: form.shift_from_name || null,
      shift_to_name: form.shift_to_name || null,
      outgoing_supervisor: form.outgoing_supervisor || null,
      incoming_supervisor: form.incoming_supervisor || null,
      outgoing_operators: form.outgoing_operators_str ? form.outgoing_operators_str.split(",").map((s) => s.trim()) : null,
      incoming_operators: form.incoming_operators_str ? form.incoming_operators_str.split(",").map((s) => s.trim()) : null,
      qty_completed: form.qty_completed ? parseFloat(form.qty_completed) : null,
      qty_remaining: form.qty_remaining ? parseFloat(form.qty_remaining) : null,
      issues_open: form.issues_str ? form.issues_str.split("\n").filter(Boolean) : null,
      qc_pending_items: form.qc_pending_str ? form.qc_pending_str.split("\n").filter(Boolean) : null,
      material_shortages: form.material_shortages_str ? form.material_shortages_str.split("\n").filter(Boolean) : null,
      notes: form.notes || null,
    }),
    onSuccess: () => {
      setShowModal(false);
      qc.invalidateQueries({ queryKey: ["sf-handovers"] });
    },
  });

  const approveMut = useMutation({
    mutationFn: ({ id, by }: { id: string; by: string }) => sfApi.approveHandover(id, by),
    onSuccess: () => {
      setApprovingId(null);
      qc.invalidateQueries({ queryKey: ["sf-handovers"] });
    },
  });

  const updateForm = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <a href="/dashboard/shop-floor" className="text-sm text-gray-400 hover:text-gray-600">← Dashboard</a>
          </div>
          <h1 className="text-xl font-bold text-gray-900">Shift Handover Board</h1>
          <p className="text-sm text-gray-500 mt-0.5">Document and approve shift transitions</p>
        </div>
        <div className="flex gap-2">
          <input
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm"
            placeholder="Filter by line…"
            value={lineFilter}
            onChange={(e) => setLineFilter(e.target.value)}
          />
          <button
            onClick={() => setShowModal(true)}
            className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            + New Handover
          </button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Total Handovers", value: handovers.length, color: "text-gray-700" },
          { label: "Approved", value: handovers.filter((h) => h.is_approved).length, color: "text-green-600" },
          { label: "Pending Approval", value: handovers.filter((h) => !h.is_approved).length, color: "text-yellow-600" },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-3 text-center">
            <p className="text-xs text-gray-400">{k.label}</p>
            <p className={`text-2xl font-bold mt-0.5 ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* List */}
      {isLoading ? (
        <div className="text-center text-gray-400 py-8">Loading…</div>
      ) : handovers.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center text-sm text-gray-400">
          No handover records
        </div>
      ) : (
        <div className="space-y-4">
          {handovers.map((h) => (
            <div key={h.id} className={`bg-white rounded-xl border shadow-sm p-4 ${h.is_approved ? "border-gray-100" : "border-yellow-200"}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-sm text-gray-900">
                      {h.shift_from_name || "?"} → {h.shift_to_name || "?"}
                    </h3>
                    <span className={`text-xs px-1.5 py-0.5 rounded-full ${h.is_approved ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"}`}>
                      {h.is_approved ? "Approved" : "Pending"}
                    </span>
                    {h.line_id && <span className="text-xs text-gray-400">{h.line_id}</span>}
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-1 text-xs text-gray-500">
                    <div><span className="text-gray-400">Outgoing:</span> {h.outgoing_supervisor || "—"}</div>
                    <div><span className="text-gray-400">Incoming:</span> {h.incoming_supervisor || "—"}</div>
                    {h.qty_completed !== null && <div><span className="text-gray-400">Completed:</span> {Number(h.qty_completed).toFixed(0)}</div>}
                    {h.qty_remaining !== null && <div><span className="text-gray-400">Remaining:</span> {Number(h.qty_remaining).toFixed(0)}</div>}
                  </div>
                  <div className="mt-2 grid grid-cols-1 md:grid-cols-3 gap-2">
                    {h.issues_open && h.issues_open.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-red-600 mb-0.5">Open Issues</p>
                        <ul className="text-xs text-gray-500 space-y-0.5">
                          {h.issues_open.map((iss, i) => <li key={i}>• {iss}</li>)}
                        </ul>
                      </div>
                    )}
                    {h.qc_pending_items && h.qc_pending_items.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-purple-600 mb-0.5">QC Pending</p>
                        <ul className="text-xs text-gray-500 space-y-0.5">
                          {h.qc_pending_items.map((q, i) => <li key={i}>• {q}</li>)}
                        </ul>
                      </div>
                    )}
                    {h.material_shortages && h.material_shortages.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-orange-600 mb-0.5">Material Shortages</p>
                        <ul className="text-xs text-gray-500 space-y-0.5">
                          {h.material_shortages.map((m, i) => <li key={i}>• {m}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                  {h.notes && <p className="mt-2 text-xs text-gray-500 italic">{h.notes}</p>}
                  <p className="mt-1.5 text-xs text-gray-400">
                    {new Date(h.handover_time).toLocaleString()}
                    {h.is_approved && h.approved_by && ` · Approved by ${h.approved_by}`}
                  </p>
                </div>
                {!h.is_approved && (
                  <div>
                    {approvingId === h.id ? (
                      <div className="flex gap-1 items-center">
                        <input
                          className="border border-gray-200 rounded-lg px-2 py-1 text-xs w-28"
                          placeholder="Approver name"
                          value={approvedBy}
                          onChange={(e) => setApprovedBy(e.target.value)}
                        />
                        <button
                          onClick={() => approveMut.mutate({ id: h.id, by: approvedBy })}
                          disabled={!approvedBy || approveMut.isPending}
                          className="px-2 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 disabled:opacity-40"
                        >
                          Confirm
                        </button>
                        <button onClick={() => setApprovingId(null)} className="px-2 py-1 border border-gray-200 text-xs rounded">✕</button>
                      </div>
                    ) : (
                      <button
                        onClick={() => { setApprovingId(h.id); setApprovedBy(""); }}
                        className="px-3 py-1.5 bg-green-600 text-white text-xs rounded-lg hover:bg-green-700"
                      >
                        Approve
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 overflow-y-auto">
          <div className="bg-white rounded-2xl p-6 w-full max-w-lg shadow-xl space-y-4 my-8">
            <h2 className="text-lg font-bold text-gray-900">New Shift Handover</h2>
            <div className="grid grid-cols-2 gap-3">
              {[
                { key: "line_id", label: "Line ID", placeholder: "e.g. LINE-1" },
                { key: "shift_from_name", label: "Shift From", placeholder: "e.g. Morning" },
                { key: "shift_to_name", label: "Shift To", placeholder: "e.g. Afternoon" },
                { key: "outgoing_supervisor", label: "Outgoing Supervisor", placeholder: "" },
                { key: "incoming_supervisor", label: "Incoming Supervisor", placeholder: "" },
                { key: "qty_completed", label: "Qty Completed", placeholder: "0" },
                { key: "qty_remaining", label: "Qty Remaining", placeholder: "0" },
              ].map(({ key, label, placeholder }) => (
                <div key={key}>
                  <label className="text-xs text-gray-500">{label}</label>
                  <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-0.5" placeholder={placeholder} value={(form as any)[key]} onChange={(e) => updateForm(key, e.target.value)} />
                </div>
              ))}
              <div>
                <label className="text-xs text-gray-500">Outgoing Operators (comma-sep)</label>
                <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-0.5" value={form.outgoing_operators_str} onChange={(e) => updateForm("outgoing_operators_str", e.target.value)} />
              </div>
              <div>
                <label className="text-xs text-gray-500">Incoming Operators (comma-sep)</label>
                <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-0.5" value={form.incoming_operators_str} onChange={(e) => updateForm("incoming_operators_str", e.target.value)} />
              </div>
            </div>
            {[
              { key: "issues_str", label: "Open Issues (one per line)" },
              { key: "qc_pending_str", label: "QC Pending Items (one per line)" },
              { key: "material_shortages_str", label: "Material Shortages (one per line)" },
              { key: "notes", label: "Notes" },
            ].map(({ key, label }) => (
              <div key={key}>
                <label className="text-xs text-gray-500">{label}</label>
                <textarea className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-0.5" rows={2} value={(form as any)[key]} onChange={(e) => updateForm(key, e.target.value)} />
              </div>
            ))}
            <div className="flex gap-2">
              <button onClick={() => setShowModal(false)} className="flex-1 py-2 border border-gray-200 rounded-lg text-sm">Cancel</button>
              <button onClick={() => createMut.mutate()} disabled={createMut.isPending} className="flex-1 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium disabled:opacity-40">
                Submit Handover
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
