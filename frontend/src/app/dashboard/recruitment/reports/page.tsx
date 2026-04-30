"use client";
import { useEffect, useState } from "react";
import { recruitmentApi } from "@/lib/recruitment";

type Tab = "pipeline" | "source" | "offers";

export default function RecruitmentReportsPage() {
  const [tab, setTab] = useState<Tab>("pipeline");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    if (tab === "pipeline") setData(await recruitmentApi.reportPipelineByStage());
    else if (tab === "source") setData(await recruitmentApi.reportSourceEffectiveness());
    else setData(await recruitmentApi.reportOfferAcceptance());
    setLoading(false);
  };

  useEffect(() => { load(); }, [tab]);

  const tabs = [
    { id: "pipeline" as Tab, label: "Pipeline by Stage" },
    { id: "source" as Tab, label: "Source Effectiveness" },
    { id: "offers" as Tab, label: "Offer Acceptance" },
  ];

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold">Recruitment Reports</h1>

      <div className="flex gap-2">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded text-sm border ${tab === t.id ? "bg-blue-600 text-white" : "bg-white"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {loading ? <p className="text-sm text-gray-500">Loading…</p> : (
        <div className="bg-white rounded-xl border overflow-hidden">
          {tab === "pipeline" && Array.isArray(data) && (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-3 text-left">Stage</th>
                  <th className="px-4 py-3 text-right">Active Candidates</th>
                  <th className="px-4 py-3 text-left">Visual</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.map((r: any, i: number) => {
                  const max = Math.max(...data.map((d: any) => d.count), 1);
                  const pct = (r.count / max) * 100;
                  return (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium">{r.stage_name}</td>
                      <td className="px-4 py-3 text-right font-mono">{r.count}</td>
                      <td className="px-4 py-3 w-48">
                        <div className="h-3 bg-blue-200 rounded-full">
                          <div className="h-3 bg-blue-600 rounded-full" style={{ width: `${pct}%` }} />
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {data.length === 0 && <tr><td colSpan={3} className="px-4 py-8 text-center text-gray-400">No data</td></tr>}
              </tbody>
            </table>
          )}

          {tab === "source" && Array.isArray(data) && (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-3 text-left">Source</th>
                  <th className="px-4 py-3 text-right">Candidates</th>
                  <th className="px-4 py-3 text-right">Applied</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.map((r: any, i: number) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 capitalize font-medium">{r.source}</td>
                    <td className="px-4 py-3 text-right">{r.candidates}</td>
                    <td className="px-4 py-3 text-right">{r.applied}</td>
                  </tr>
                ))}
                {data.length === 0 && <tr><td colSpan={3} className="px-4 py-8 text-center text-gray-400">No data</td></tr>}
              </tbody>
            </table>
          )}

          {tab === "offers" && data && !Array.isArray(data) && (
            <div className="p-6 grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: "Total Offers", value: data.total_offers, color: "bg-blue-50 text-blue-700" },
                { label: "Accepted", value: data.accepted, color: "bg-green-50 text-green-700" },
                { label: "Rejected", value: data.rejected, color: "bg-red-50 text-red-700" },
                { label: "Acceptance Rate", value: `${data.acceptance_rate_pct}%`, color: "bg-indigo-50 text-indigo-700" },
              ].map((k) => (
                <div key={k.label} className={`rounded-xl p-4 ${k.color}`}>
                  <p className="text-xs opacity-70">{k.label}</p>
                  <p className="text-2xl font-bold mt-1">{k.value}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
