"use client";
import { useEffect, useState } from "react";
import { qmsApi, QCDeviation, RISK_BG, STATUS_BG, DeviationStatus, RiskLevel } from "@/lib/qms";

export default function DeviationsPage() {
  const [devs, setDevs] = useState<QCDeviation[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<DeviationStatus | "">("");
  const [severityFilter, setSeverityFilter] = useState<RiskLevel | "">("");
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState<Record<string, unknown>>({
    deviation_type: "", severity: "MEDIUM", description: "",
  });
  const [resolveId, setResolveId] = useState<string | null>(null);
  const [rootCause, setRootCause] = useState("");

  const load = () => {
    setLoading(true);
    qmsApi.listDeviations({
      status: statusFilter || undefined,
      severity: severityFilter || undefined,
    }).then(setDevs).finally(() => setLoading(false));
  };

  useEffect(load, [statusFilter, severityFilter]);

  const handleCreate = async () => {
    await qmsApi.createDeviation(form);
    setShowNew(false);
    setForm({ deviation_type: "", severity: "MEDIUM", description: "" });
    load();
  };

  const handleResolve = async (id: string) => {
    await qmsApi.updateDeviation(id, { status: "RESOLVED", root_cause: rootCause });
    setResolveId(null);
    setRootCause("");
    load();
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Deviation Management</h1>
          <p className="text-sm text-gray-500 mt-0.5">QC failures, out-of-spec results, and process deviations</p>
        </div>
        <button onClick={() => setShowNew(true)}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700">
          + Report Deviation
        </button>
      </div>

      <div className="flex gap-3">
        <select className="border rounded-lg px-3 py-2 text-sm text-gray-700 bg-white"
          value={statusFilter} onChange={e => setStatusFilter(e.target.value as DeviationStatus | "")}>
          <option value="">All Statuses</option>
          <option value="OPEN">Open</option>
          <option value="UNDER_REVIEW">Under Review</option>
          <option value="RESOLVED">Resolved</option>
          <option value="CLOSED">Closed</option>
        </select>
        <select className="border rounded-lg px-3 py-2 text-sm text-gray-700 bg-white"
          value={severityFilter} onChange={e => setSeverityFilter(e.target.value as RiskLevel | "")}>
          <option value="">All Severities</option>
          <option value="LOW">Low</option>
          <option value="MEDIUM">Medium</option>
          <option value="HIGH">High</option>
          <option value="CRITICAL">Critical</option>
        </select>
      </div>

      {showNew && (
        <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
          <h3 className="font-semibold text-gray-800">Report New Deviation</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Deviation Type *</label>
              <input className="border rounded-lg px-3 py-2 text-sm w-full"
                placeholder="e.g. QC_FAILURE, CCP_BREACH, PROCESS_EXCURSION"
                value={form.deviation_type as string}
                onChange={e => setForm(p => ({ ...p, deviation_type: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Severity *</label>
              <select className="border rounded-lg px-3 py-2 text-sm w-full"
                value={form.severity as string}
                onChange={e => setForm(p => ({ ...p, severity: e.target.value }))}>
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Affected Quantity</label>
              <input type="number" className="border rounded-lg px-3 py-2 text-sm w-full"
                value={(form.affected_quantity as number) || ""}
                onChange={e => setForm(p => ({ ...p, affected_quantity: parseFloat(e.target.value) }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Due Date</label>
              <input type="date" className="border rounded-lg px-3 py-2 text-sm w-full"
                value={(form.due_date as string) || ""}
                onChange={e => setForm(p => ({ ...p, due_date: e.target.value }))} />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-500 block mb-1">Description *</label>
              <textarea className="border rounded-lg px-3 py-2 text-sm w-full" rows={2}
                value={form.description as string}
                onChange={e => setForm(p => ({ ...p, description: e.target.value }))} />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-500 block mb-1">Immediate Action Taken</label>
              <textarea className="border rounded-lg px-3 py-2 text-sm w-full" rows={2}
                value={(form.immediate_action as string) || ""}
                onChange={e => setForm(p => ({ ...p, immediate_action: e.target.value }))} />
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={handleCreate}
              className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700">
              Submit
            </button>
            <button onClick={() => setShowNew(false)}
              className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200">
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <p className="px-5 py-8 text-gray-400 text-sm">Loading…</p>
        ) : devs.length === 0 ? (
          <p className="px-5 py-8 text-gray-400 text-sm">No deviations found</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                {["Deviation #", "Type", "Severity", "Status", "Product/Material", "Qty", "Reported", "Assigned To", "Due", "Actions"].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {devs.map(d => (
                <tr key={d.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{d.deviation_no}</td>
                  <td className="px-4 py-3 text-gray-600">{d.deviation_type.replace("_", " ")}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${RISK_BG[d.severity]}`}>
                      {d.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${STATUS_BG[d.status] || "bg-gray-100"}`}>
                      {d.status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{d.product_name || d.material_name || "—"}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {d.affected_quantity ? `${d.affected_quantity} ${d.affected_uom || ""}` : "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {new Date(d.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{d.assigned_to_name || "—"}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {d.due_date ? new Date(d.due_date).toLocaleDateString() : "—"}
                  </td>
                  <td className="px-4 py-3">
                    {d.status === "OPEN" || d.status === "UNDER_REVIEW" ? (
                      <button onClick={() => setResolveId(resolveId === d.id ? null : d.id)}
                        className="text-xs text-indigo-600 hover:underline">Resolve</button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {resolveId && (
        <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-3">
          <h3 className="font-semibold text-gray-800">Resolve Deviation</h3>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Root Cause Analysis</label>
            <textarea className="border rounded-lg px-3 py-2 text-sm w-full" rows={3}
              value={rootCause} onChange={e => setRootCause(e.target.value)} />
          </div>
          <div className="flex gap-3">
            <button onClick={() => handleResolve(resolveId)}
              className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700">
              Mark Resolved
            </button>
            <button onClick={() => setResolveId(null)}
              className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200">
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
