"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  appraisalsApi, AppraisalRecord, AppraisalStatus,
  APPRAISAL_STATUS_COLOR, APPRAISAL_STATUS_LABEL, RATING_COLOR, RATING_LABEL,
} from "@/lib/appraisals";
import { tx } from "@/lib/i18n/core";

const STATUSES: AppraisalStatus[] = ["draft","self_review","manager_review","hr_review","calibration","completed","rejected"];

export default function AppraisalRecordsPage() {
  const [records, setRecords] = useState<AppraisalRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [empFilter, setEmpFilter] = useState("");
  const [selected, setSelected] = useState<AppraisalRecord | null>(null);

  const load = () => {
    appraisalsApi.listRecords({
      status: statusFilter || undefined,
      employee_id: empFilter || undefined,
    }).then(setRecords).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, [statusFilter, empFilter]);

  const calc = async (id: string) => {
    await appraisalsApi.calculateScores(id);
    load();
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">{tx("Appraisal Records")}</h1>
        <Link
          href="/dashboard/appraisals/records/new"
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          {tx("+ New Appraisal")}
        </Link>
      </div>

      <div className="flex gap-3 flex-wrap">
        <select
          className="border rounded px-2 py-1 text-sm"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">{tx("All Statuses")}</option>
          {STATUSES.map((s) => <option key={s} value={s}>{APPRAISAL_STATUS_LABEL[s]}</option>)}
        </select>
        <input
          className="border rounded px-2 py-1 text-sm w-48"
          placeholder={tx("Filter by employee ID…")}
          value={empFilter}
          onChange={(e) => setEmpFilter(e.target.value)}
        />
      </div>

      {loading ? (
        <p className="text-gray-500 text-sm">{tx("Loading…")}</p>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {[tx("Employee"),tx("Department"),tx("Manager"),tx("Status"),tx("Self Score"),tx("Mgr Score"),tx("Final Score"),tx("Rating"),tx("Actions")].map((h) => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {records.map((r) => (
                <tr key={r.appraisal_id} className="hover:bg-gray-50 cursor-pointer" onClick={() => setSelected(r)}>
                  <td className="px-4 py-2 font-medium text-gray-800">{r.employee_name ?? r.employee_id}</td>
                  <td className="px-4 py-2 text-gray-600">{r.department_name ?? "—"}</td>
                  <td className="px-4 py-2 text-gray-600">{r.manager_name ?? "—"}</td>
                  <td className="px-4 py-2">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${APPRAISAL_STATUS_COLOR[r.status]}`}>
                      {APPRAISAL_STATUS_LABEL[r.status]}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-center">{r.self_score ?? "—"}</td>
                  <td className="px-4 py-2 text-center">{r.manager_score ?? "—"}</td>
                  <td className="px-4 py-2 text-center font-semibold">{r.final_score ?? "—"}</td>
                  <td className="px-4 py-2">
                    {r.final_rating ? (
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${RATING_COLOR[r.final_rating]}`}>
                        {r.final_rating.replace(/_/g," ")}
                      </span>
                    ) : "—"}
                  </td>
                  <td className="px-4 py-2" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => calc(r.appraisal_id)}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      {tx("Calc Scores")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {records.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">{tx("No appraisals found.")}</p>}
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-center z-50 p-6 overflow-auto">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl p-6 space-y-4">
            <div className="flex justify-between">
              <h2 className="text-lg font-bold text-gray-900">
                {selected.employee_name ?? selected.employee_id}
              </h2>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-700 text-xl">✕</button>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div><span className="text-gray-500">{tx("Status:")}</span>{" "}
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${APPRAISAL_STATUS_COLOR[selected.status]}`}>
                  {APPRAISAL_STATUS_LABEL[selected.status]}
                </span>
              </div>
              <div><span className="text-gray-500">{tx("Self Score:")}</span> {selected.self_score ?? "—"}</div>
              <div><span className="text-gray-500">{tx("Manager Score:")}</span> {selected.manager_score ?? "—"}</div>
              <div><span className="text-gray-500">{tx("Final Score:")}</span> <strong>{selected.final_score ?? "—"}</strong></div>
              <div><span className="text-gray-500">{tx("Rating:")}</span>{" "}
                {selected.final_rating ? (
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${RATING_COLOR[selected.final_rating]}`}>
                    {RATING_LABEL[selected.final_rating]}
                  </span>
                ) : "—"}
              </div>
              <div><span className="text-gray-500">{tx("Promotion Rec:")}</span> {selected.promotion_recommendation ? tx("Yes") : tx("No")}</div>
              {selected.increment_recommendation && (
                <div><span className="text-gray-500">{tx("Increment:")}</span> {selected.increment_recommendation}%</div>
              )}
            </div>

            {selected.kpi_lines.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">{tx("KPI Lines")}</h3>
                <table className="w-full text-xs border rounded">
                  <thead className="bg-gray-50"><tr>
                    {["KPI",tx("Target"),tx("Actual"),tx("Weight %"),tx("Self"),tx("Mgr"),tx("Final")].map(h=><th key={h} className="px-2 py-1 text-left text-gray-600">{h}</th>)}
                  </tr></thead>
                  <tbody className="divide-y">
                    {selected.kpi_lines.map(l => (
                      <tr key={l.kpi_line_id}>
                        <td className="px-2 py-1">{l.kpi_name}</td>
                        <td className="px-2 py-1">{l.target_value ?? "—"} {l.unit}</td>
                        <td className="px-2 py-1">{l.actual_value ?? "—"}</td>
                        <td className="px-2 py-1">{l.weight_pct}%</td>
                        <td className="px-2 py-1">{l.self_score ?? "—"}</td>
                        <td className="px-2 py-1">{l.manager_score ?? "—"}</td>
                        <td className="px-2 py-1 font-semibold">{l.final_score ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {selected.competency_lines.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">{tx("Competency Lines")}</h3>
                <table className="w-full text-xs border rounded">
                  <thead className="bg-gray-50"><tr>
                    {[tx("Competency"),tx("Weight %"),tx("Self"),tx("Manager"),tx("Final")].map(h=><th key={h} className="px-2 py-1 text-left text-gray-600">{h}</th>)}
                  </tr></thead>
                  <tbody className="divide-y">
                    {selected.competency_lines.map(l => (
                      <tr key={l.competency_line_id}>
                        <td className="px-2 py-1">{l.competency_name}</td>
                        <td className="px-2 py-1">{l.weight_pct}%</td>
                        <td className="px-2 py-1">{l.self_rating ?? "—"}</td>
                        <td className="px-2 py-1">{l.manager_rating ?? "—"}</td>
                        <td className="px-2 py-1 font-semibold">{l.final_rating ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {selected.notes && (
              <div className="text-sm text-gray-600 border-t pt-2">
                <strong>{tx("Notes:")}</strong> {selected.notes}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
