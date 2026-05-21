"use client";
import { useEffect, useState } from "react";
import { qmsApi, CriticalControlPoint, CCPMonitoringLog, RISK_BG } from "@/lib/qms";

export default function CCPMonitoringPage() {
  const [ccps, setCCPs] = useState<CriticalControlPoint[]>([]);
  const [violations, setViolations] = useState<CCPMonitoringLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCCP, setSelectedCCP] = useState<CriticalControlPoint | null>(null);
  const [logs, setLogs] = useState<CCPMonitoringLog[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [monitorForm, setMonitorForm] = useState<Record<string, unknown>>({});
  const [showMonitor, setShowMonitor] = useState(false);
  const [showNewCCP, setShowNewCCP] = useState(false);
  const [ccpForm, setCcpForm] = useState<Record<string, unknown>>({
    ccp_name: "", process_step: "", hazard_type: "BIOLOGICAL",
    parameter_name: "", monitoring_method: "", monitoring_frequency: "",
    corrective_action_description: "", is_active: true,
  });

  const load = () => {
    setLoading(true);
    Promise.all([qmsApi.listCCPs(), qmsApi.listViolations(20)])
      .then(([c, v]) => { setCCPs(c); setViolations(v); })
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const loadLogs = (ccp: CriticalControlPoint) => {
    setSelectedCCP(ccp);
    setLogsLoading(true);
    qmsApi.getCCPLogs(ccp.id).then(setLogs).finally(() => setLogsLoading(false));
  };

  const handleMonitor = async () => {
    if (!selectedCCP) return;
    const body = { ...monitorForm, ccp_id: selectedCCP.id,
      monitoring_datetime: new Date().toISOString() };
    await qmsApi.recordMonitoring(body);
    setShowMonitor(false);
    loadLogs(selectedCCP);
    load();
  };

  const handleCreateCCP = async () => {
    await qmsApi.createCCP(ccpForm);
    setShowNewCCP(false);
    load();
  };

  const HAZARD_COLORS: Record<string, string> = {
    BIOLOGICAL: "bg-red-100 text-red-800", CHEMICAL: "bg-orange-100 text-orange-800",
    PHYSICAL: "bg-yellow-100 text-yellow-800", ALLERGEN: "bg-purple-100 text-purple-800",
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">CCP Monitoring Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">Critical Control Points — real-time monitoring and violation tracking</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => setShowNewCCP(!showNewCCP)}
            className="px-4 py-2 bg-teal-600 text-white text-sm rounded-lg hover:bg-teal-700">
            + Define CCP
          </button>
        </div>
      </div>

      {showNewCCP && (
        <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
          <h3 className="font-semibold text-gray-800">Define New Critical Control Point</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1">CCP Name *</label>
              <input className="border rounded-lg px-3 py-2 text-sm w-full"
                value={ccpForm.ccp_name as string}
                onChange={e => setCcpForm(p => ({ ...p, ccp_name: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Process Step *</label>
              <input className="border rounded-lg px-3 py-2 text-sm w-full" placeholder="e.g. Pasteurization"
                value={ccpForm.process_step as string}
                onChange={e => setCcpForm(p => ({ ...p, process_step: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Hazard Type *</label>
              <select className="border rounded-lg px-3 py-2 text-sm w-full"
                value={ccpForm.hazard_type as string}
                onChange={e => setCcpForm(p => ({ ...p, hazard_type: e.target.value }))}>
                <option value="BIOLOGICAL">Biological</option>
                <option value="CHEMICAL">Chemical</option>
                <option value="PHYSICAL">Physical</option>
                <option value="ALLERGEN">Allergen</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Parameter Name *</label>
              <input className="border rounded-lg px-3 py-2 text-sm w-full" placeholder="e.g. Temperature (°C)"
                value={ccpForm.parameter_name as string}
                onChange={e => setCcpForm(p => ({ ...p, parameter_name: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Critical Limit Min</label>
              <input type="number" className="border rounded-lg px-3 py-2 text-sm w-full"
                value={(ccpForm.critical_limit_min as number) || ""}
                onChange={e => setCcpForm(p => ({ ...p, critical_limit_min: parseFloat(e.target.value) }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Critical Limit Max</label>
              <input type="number" className="border rounded-lg px-3 py-2 text-sm w-full"
                value={(ccpForm.critical_limit_max as number) || ""}
                onChange={e => setCcpForm(p => ({ ...p, critical_limit_max: parseFloat(e.target.value) }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Monitoring Method *</label>
              <input className="border rounded-lg px-3 py-2 text-sm w-full"
                value={ccpForm.monitoring_method as string}
                onChange={e => setCcpForm(p => ({ ...p, monitoring_method: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Monitoring Frequency *</label>
              <input className="border rounded-lg px-3 py-2 text-sm w-full" placeholder="e.g. Every 30 minutes"
                value={ccpForm.monitoring_frequency as string}
                onChange={e => setCcpForm(p => ({ ...p, monitoring_frequency: e.target.value }))} />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-500 block mb-1">Corrective Action (use semicolons for steps) *</label>
              <textarea className="border rounded-lg px-3 py-2 text-sm w-full" rows={2}
                placeholder="Stop production; Adjust temperature; Re-test; Document corrective action"
                value={ccpForm.corrective_action_description as string}
                onChange={e => setCcpForm(p => ({ ...p, corrective_action_description: e.target.value }))} />
            </div>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 text-sm mt-2">
                <input type="checkbox" checked={ccpForm.allergen_related as boolean || false}
                  onChange={e => setCcpForm(p => ({ ...p, allergen_related: e.target.checked }))} />
                Allergen-related
              </label>
              <label className="flex items-center gap-2 text-sm mt-2">
                <input type="checkbox" checked={ccpForm.cleaning_required as boolean || false}
                  onChange={e => setCcpForm(p => ({ ...p, cleaning_required: e.target.checked }))} />
                Cleaning required
              </label>
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={handleCreateCCP}
              className="px-4 py-2 bg-teal-600 text-white text-sm rounded-lg hover:bg-teal-700">
              Define CCP
            </button>
            <button onClick={() => setShowNewCCP(false)}
              className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Recent Violations */}
      {violations.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <h2 className="font-semibold text-red-800 mb-3">⚠ Recent CCP Violations</h2>
          <div className="space-y-2">
            {violations.slice(0, 5).map(v => (
              <div key={v.id} className="flex items-center justify-between bg-white rounded-lg px-4 py-2 border border-red-100">
                <div>
                  <span className="font-medium text-red-800">{v.ccp_name || "CCP"}</span>
                  <span className="text-xs text-gray-500 ml-2">
                    Value: {v.recorded_value} | Deviation: {v.deviation_amount}
                  </span>
                </div>
                <span className="text-xs text-gray-400">{new Date(v.monitoring_datetime).toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* CCP List */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100">
            <h2 className="font-semibold text-gray-800">Active CCPs</h2>
          </div>
          {loading ? (
            <p className="px-5 py-8 text-gray-400 text-sm">Loading…</p>
          ) : ccps.length === 0 ? (
            <p className="px-5 py-8 text-gray-400 text-sm">No CCPs defined yet</p>
          ) : (
            <div className="divide-y divide-gray-100">
              {ccps.map(c => (
                <div key={c.id}
                  className={`px-5 py-4 hover:bg-gray-50 cursor-pointer ${selectedCCP?.id === c.id ? "bg-indigo-50" : ""}`}
                  onClick={() => loadLogs(c)}>
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-medium text-gray-800">{c.ccp_no}</span>
                      <span className="text-sm text-gray-600 ml-2">{c.ccp_name}</span>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-xs ${HAZARD_COLORS[c.hazard_type] || "bg-gray-100"}`}>
                      {c.hazard_type}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                    <span>{c.process_step}</span>
                    <span>│</span>
                    <span>{c.parameter_name}</span>
                    {c.critical_limit_min != null && <span>Min: {c.critical_limit_min}</span>}
                    {c.critical_limit_max != null && <span>Max: {c.critical_limit_max}</span>}
                    {c.recent_violations > 0 && (
                      <span className="text-red-600 font-medium">⚠ {c.recent_violations} violation(s)</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Monitoring Logs */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-800">
              {selectedCCP ? `${selectedCCP.ccp_no} — Monitoring Logs` : "Select a CCP to view logs"}
            </h2>
            {selectedCCP && (
              <button onClick={() => setShowMonitor(!showMonitor)}
                className="text-sm px-3 py-1.5 bg-teal-600 text-white rounded-lg hover:bg-teal-700">
                + Record
              </button>
            )}
          </div>

          {showMonitor && selectedCCP && (
            <div className="px-5 py-4 border-b border-gray-100 bg-gray-50 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 block mb-1">
                    {selectedCCP.parameter_name} value *
                  </label>
                  <input type="number" className="border rounded-lg px-3 py-2 text-sm w-full"
                    value={(monitorForm.recorded_value as number) || ""}
                    onChange={e => setMonitorForm(p => ({ ...p, recorded_value: parseFloat(e.target.value) }))} />
                </div>
                <div>
                  <label className="text-xs text-gray-500 block mb-1">Notes</label>
                  <input className="border rounded-lg px-3 py-2 text-sm w-full"
                    value={(monitorForm.notes as string) || ""}
                    onChange={e => setMonitorForm(p => ({ ...p, notes: e.target.value }))} />
                </div>
              </div>
              <div className="flex gap-3">
                <button onClick={handleMonitor}
                  className="px-3 py-1.5 bg-teal-600 text-white text-sm rounded-lg hover:bg-teal-700">
                  Record
                </button>
                <button onClick={() => setShowMonitor(false)}
                  className="px-3 py-1.5 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200">
                  Cancel
                </button>
              </div>
            </div>
          )}

          {!selectedCCP ? (
            <p className="px-5 py-8 text-gray-400 text-sm">Click a CCP to view monitoring history</p>
          ) : logsLoading ? (
            <p className="px-5 py-8 text-gray-400 text-sm">Loading logs…</p>
          ) : logs.length === 0 ? (
            <p className="px-5 py-8 text-gray-400 text-sm">No monitoring records for this CCP</p>
          ) : (
            <div className="divide-y divide-gray-100 max-h-96 overflow-y-auto">
              {logs.map(l => (
                <div key={l.id} className={`px-5 py-3 ${l.is_violation ? "bg-red-50" : ""}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={`w-2 h-2 rounded-full ${l.is_within_limits ? "bg-green-500" : "bg-red-500"}`} />
                      <span className="font-medium text-gray-800">{l.recorded_value}</span>
                      {l.is_violation && (
                        <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">
                          VIOLATION +{l.deviation_amount}
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-gray-400">{new Date(l.monitoring_datetime).toLocaleString()}</span>
                  </div>
                  {l.corrective_action_taken && (
                    <p className="text-xs text-gray-500 mt-1 pl-5">{l.corrective_action_taken}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
