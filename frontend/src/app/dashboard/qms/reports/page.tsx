"use client";
import { useEffect, useState } from "react";
import { qmsApi } from "@/lib/qms";

interface QCReport {
  total: number;
  by_status: Record<string, number>;
  pass_rate: number;
  fail_rate: number;
}

interface CCPReport {
  total_violations: number;
  violations_by_ccp: Record<string, number>;
  recent_violations: Array<{ id: string; ccp_id: string; monitoring_datetime: string; recorded_value: number | null; deviation_amount: number | null }>;
}

interface DevReport {
  total: number;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  open: number;
  resolved: number;
}

interface LotReport {
  total_lots_tracked: number;
  by_release_status: Record<string, number>;
  fefo_eligible: number;
  shipment_eligible: number;
  on_hold: number;
  quarantined: number;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="font-semibold text-gray-800 mb-4">{title}</h3>
      {children}
    </div>
  );
}

function StatRow({ label, value, bar = 0, color = "bg-indigo-500" }: { label: string; value: string | number; bar?: number; color?: string }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
      <span className="text-sm text-gray-600">{label}</span>
      <div className="flex items-center gap-3">
        {bar > 0 && (
          <div className="w-24 bg-gray-100 rounded-full h-2">
            <div className={`${color} h-2 rounded-full`} style={{ width: `${Math.min(100, bar)}%` }} />
          </div>
        )}
        <span className="text-sm font-semibold text-gray-800 min-w-[3rem] text-right">{value}</span>
      </div>
    </div>
  );
}

export default function QMSReportsPage() {
  const [qcReport, setQcReport] = useState<QCReport | null>(null);
  const [ccpReport, setCcpReport] = useState<CCPReport | null>(null);
  const [devReport, setDevReport] = useState<DevReport | null>(null);
  const [lotReport, setLotReport] = useState<LotReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      qmsApi.getQCSummaryReport(),
      qmsApi.getCCPViolationReport(),
      qmsApi.getDeviationReport(),
      qmsApi.getLotQualityReport(),
    ]).then(([qc, ccp, dev, lot]) => {
      setQcReport(qc as QCReport);
      setCcpReport(ccp as CCPReport);
      setDevReport(dev as DevReport);
      setLotReport(lot as LotReport);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-gray-500">Loading QMS reports…</div>;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">QMS Reports</h1>
        <p className="text-sm text-gray-500 mt-0.5">Quality performance, CCP violations, deviations, and lot quality</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* QC Summary */}
        {qcReport && (
          <Section title="QC Inspection Summary">
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="text-center">
                <p className="text-3xl font-bold text-gray-800">{qcReport.total}</p>
                <p className="text-xs text-gray-500 mt-0.5">Total Inspections</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-green-700">{qcReport.pass_rate}%</p>
                <p className="text-xs text-gray-500 mt-0.5">Pass Rate</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-red-700">{qcReport.fail_rate}%</p>
                <p className="text-xs text-gray-500 mt-0.5">Fail Rate</p>
              </div>
            </div>
            {Object.entries(qcReport.by_status).map(([status, count]) => (
              <StatRow key={status} label={status.replace("_", " ")} value={count}
                bar={qcReport.total ? (count / qcReport.total * 100) : 0}
                color={status === "PASSED" ? "bg-green-500" : status === "FAILED" ? "bg-red-500" : "bg-blue-500"} />
            ))}
          </Section>
        )}

        {/* CCP Violations */}
        {ccpReport && (
          <Section title="CCP Violations">
            <div className="mb-4">
              <p className="text-3xl font-bold text-red-700">{ccpReport.total_violations}</p>
              <p className="text-xs text-gray-500 mt-0.5">Total Violations</p>
            </div>
            {Object.entries(ccpReport.violations_by_ccp).length === 0 ? (
              <p className="text-sm text-green-700">No CCP violations recorded</p>
            ) : (
              Object.entries(ccpReport.violations_by_ccp).map(([ccp_id, count]) => (
                <StatRow key={ccp_id} label={`CCP ${ccp_id.slice(0, 8)}…`} value={count} color="bg-red-500" />
              ))
            )}
            {ccpReport.recent_violations.length > 0 && (
              <div className="mt-4">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Recent</p>
                {ccpReport.recent_violations.slice(0, 5).map(v => (
                  <div key={v.id} className="flex items-center justify-between py-1.5 text-xs border-t border-gray-100">
                    <span className="text-gray-600">Value: {v.recorded_value}</span>
                    <span className="text-red-600">+{v.deviation_amount} deviation</span>
                    <span className="text-gray-400">{new Date(v.monitoring_datetime).toLocaleDateString()}</span>
                  </div>
                ))}
              </div>
            )}
          </Section>
        )}

        {/* Deviations */}
        {devReport && (
          <Section title="Deviation Analysis">
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="text-center">
                <p className="text-3xl font-bold text-gray-800">{devReport.total}</p>
                <p className="text-xs text-gray-500 mt-0.5">Total</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-red-700">{devReport.open}</p>
                <p className="text-xs text-gray-500 mt-0.5">Open</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-green-700">{devReport.resolved}</p>
                <p className="text-xs text-gray-500 mt-0.5">Resolved</p>
              </div>
            </div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">By Severity</p>
            {Object.entries(devReport.by_severity).map(([sev, count]) => (
              <StatRow key={sev} label={sev} value={count}
                bar={devReport.total ? (count / devReport.total * 100) : 0}
                color={sev === "CRITICAL" ? "bg-red-600" : sev === "HIGH" ? "bg-orange-500" : sev === "MEDIUM" ? "bg-yellow-500" : "bg-green-500"} />
            ))}
          </Section>
        )}

        {/* Lot Quality */}
        {lotReport && (
          <Section title="Lot Quality Status">
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="text-center">
                <p className="text-3xl font-bold text-gray-800">{lotReport.total_lots_tracked}</p>
                <p className="text-xs text-gray-500 mt-0.5">Lots Tracked</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-teal-700">{lotReport.fefo_eligible}</p>
                <p className="text-xs text-gray-500 mt-0.5">FEFO Eligible</p>
              </div>
            </div>
            {[
              { label: "On Hold", value: lotReport.on_hold, color: "bg-orange-500" },
              { label: "Quarantined", value: lotReport.quarantined, color: "bg-red-500" },
              { label: "Shipment Eligible", value: lotReport.shipment_eligible, color: "bg-green-500" },
            ].map(row => (
              <StatRow key={row.label} label={row.label} value={row.value}
                bar={lotReport.total_lots_tracked ? (row.value / lotReport.total_lots_tracked * 100) : 0}
                color={row.color} />
            ))}
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 mt-3">By Release Status</p>
            {Object.entries(lotReport.by_release_status).map(([status, count]) => (
              <StatRow key={status} label={status.replace("_", " ")} value={count}
                bar={lotReport.total_lots_tracked ? (count / lotReport.total_lots_tracked * 100) : 0} />
            ))}
          </Section>
        )}
      </div>
    </div>
  );
}
