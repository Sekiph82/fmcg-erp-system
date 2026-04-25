"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { gs1Api, type PrintJob, statusColor } from "@/lib/gs1";

export default function PrintQueuePage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("PENDING");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ trigger: "MANUAL", printer_name: "", notes: "" });

  const { data: jobs } = useQuery({
    queryKey: ["gs1-print-jobs", statusFilter],
    queryFn: () => gs1Api.listPrintJobs(statusFilter || undefined),
  });

  const { data: templates } = useQuery({ queryKey: ["gs1-templates"], queryFn: () => gs1Api.listTemplates() });

  const createJob = useMutation({
    mutationFn: gs1Api.createPrintJob,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["gs1-print-jobs"] }); setShowForm(false); },
  });

  const completeJob = useMutation({
    mutationFn: (id: string) => gs1Api.completePrintJob(id, "operator"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["gs1-print-jobs"] }),
  });

  const triggerLabels: Record<string, string> = {
    MANUAL: "Manual",
    PRODUCTION_COMPLETE: "Production Complete",
    PACKAGING_COMPLETE: "Packaging Complete",
    PALLETIZATION: "Palletization",
    SHIPMENT: "Shipment",
    QC_RELEASE: "QC Release",
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Print Queue</h1>
          <p className="text-sm text-gray-500">Label print job management — batch print, PDF export, direct printing</p>
        </div>
        <button onClick={() => setShowForm(true)} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">
          + New Print Job
        </button>
      </div>

      {/* New Print Job Form */}
      {showForm && (
        <div className="bg-white border rounded-lg p-4 space-y-3">
          <h2 className="text-sm font-medium text-gray-700">New Print Job</h2>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-gray-500">Trigger</label>
              <select className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.trigger} onChange={(e) => setForm((p) => ({ ...p, trigger: e.target.value }))}>
                {Object.entries(triggerLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Printer Name</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.printer_name} onChange={(e) => setForm((p) => ({ ...p, printer_name: e.target.value }))} placeholder="Zebra ZT410 - Warehouse A" />
            </div>
            <div>
              <label className="text-xs text-gray-500">Notes</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.notes} onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))} />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => createJob.mutate(form)} disabled={createJob.isPending} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded disabled:opacity-50">Create Job</button>
            <button onClick={() => setShowForm(false)} className="px-3 py-1.5 text-sm border rounded">Cancel</button>
          </div>
        </div>
      )}

      {/* Status Filter Tabs */}
      <div className="flex gap-2">
        {["", "PENDING", "PRINTING", "COMPLETED", "FAILED", "CANCELLED"].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 text-xs rounded border ${statusFilter === s ? "bg-gray-900 text-white border-gray-900" : "bg-white hover:bg-gray-50"}`}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      {/* Print Jobs Table */}
      <div className="bg-white border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {["Job No.", "Trigger", "Status", "Printer", "Qty", "Printed By", "Printed At", "Created", "Actions"].map((h) => (
                  <th key={h} className="px-3 py-2 text-left whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {!jobs?.length && <tr><td colSpan={9} className="px-4 py-6 text-center text-gray-400">No print jobs found</td></tr>}
              {jobs?.map((j) => (
                <tr key={j.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-mono text-xs font-medium">{j.job_no}</td>
                  <td className="px-3 py-2 text-xs">{triggerLabels[j.trigger] || j.trigger}</td>
                  <td className="px-3 py-2">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${statusColor[j.status] ?? ""}`}>{j.status}</span>
                  </td>
                  <td className="px-3 py-2 text-gray-500 text-xs">{j.printer_name || "—"}</td>
                  <td className="px-3 py-2">{j.quantity}</td>
                  <td className="px-3 py-2 text-gray-500">{j.printed_by || "—"}</td>
                  <td className="px-3 py-2 text-gray-400 text-xs">{j.printed_at ? new Date(j.printed_at).toLocaleString() : "—"}</td>
                  <td className="px-3 py-2 text-gray-400 text-xs">{new Date(j.created_at).toLocaleDateString()}</td>
                  <td className="px-3 py-2">
                    {j.status === "PENDING" && (
                      <button
                        onClick={() => completeJob.mutate(j.id)}
                        disabled={completeJob.isPending}
                        className="text-xs bg-green-50 text-green-700 px-2 py-0.5 rounded hover:bg-green-100 disabled:opacity-50"
                      >
                        Mark Complete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Print Trigger Legend */}
      <div className="bg-gray-50 border rounded-lg p-3">
        <p className="text-xs font-medium text-gray-600 mb-2">Print Triggers</p>
        <div className="grid grid-cols-3 gap-2">
          {Object.entries(triggerLabels).map(([k, v]) => (
            <div key={k} className="text-xs text-gray-500"><span className="font-mono text-gray-700">{k}</span> → {v}</div>
          ))}
        </div>
      </div>
    </div>
  );
}
