"use client";
import { useCallback, useEffect, useState } from "react";
import { recruitmentApi } from "@/lib/recruitment";

type Tab = "pipeline" | "source" | "offers";

export default function RecruitmentReportsPage() {
  const [tab, setTab] = useState<Tab>("pipeline");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    if (tab === "pipeline") setData(await recruitmentApi.reportPipelineByStage());
    else if (tab === "source") setData(await recruitmentApi.reportSourceEffectiveness());
    else setData(await recruitmentApi.reportOfferAcceptance());
    setLoading(false);
  }, [tab]);
  useEffect(() => { load(); }, [load]);

  const tabs = [{ id: "pipeline" as Tab, label: "Pipeline by Stage" }, { id: "source" as Tab, label: "Source Effectiveness" }, { id: "offers" as Tab, label: "Offer Acceptance" }];

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <h1 className="text-xl font-bold text-white">Recruitment Reports</h1>

      <div className="flex gap-2">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${tab === t.id ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {loading ? <p className="text-slate-500 text-sm">Loading…</p> : (
        <div className="glass-table">
          {tab === "pipeline" && Array.isArray(data) && (
            <table className="w-full text-sm">
              <thead><tr className="border-b border-white/[0.07]">
                {["Stage", "Active Candidates", "Visual"].map((h) => <th key={h} className="px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest text-left">{h}</th>)}
              </tr></thead>
              <tbody>
                {data.map((r: any, i: number) => {
                  const max = Math.max(...data.map((d: any) => d.count), 1);
                  return (
                    <tr key={i} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                      <td className="px-4 py-3 text-white font-medium">{r.stage_name}</td>
                      <td className="px-4 py-3 text-slate-300 font-mono">{r.count}</td>
                      <td className="px-4 py-3 w-48"><div className="h-2 bg-white/[0.06] rounded-full"><div className="h-2 bg-indigo-500 rounded-full" style={{ width: `${(r.count / max) * 100}%` }} /></div></td>
                    </tr>
                  );
                })}
                {data.length === 0 && <tr><td colSpan={3} className="px-4 py-8 text-center text-slate-600">No data</td></tr>}
              </tbody>
            </table>
          )}
          {tab === "source" && Array.isArray(data) && (
            <table className="w-full text-sm">
              <thead><tr className="border-b border-white/[0.07]">
                {["Source", "Candidates", "Applied"].map((h) => <th key={h} className="px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest text-left">{h}</th>)}
              </tr></thead>
              <tbody>
                {data.map((r: any, i: number) => (
                  <tr key={i} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                    <td className="px-4 py-3 text-white capitalize font-medium">{r.source}</td>
                    <td className="px-4 py-3 text-slate-400">{r.candidates}</td>
                    <td className="px-4 py-3 text-slate-400">{r.applied}</td>
                  </tr>
                ))}
                {data.length === 0 && <tr><td colSpan={3} className="px-4 py-8 text-center text-slate-600">No data</td></tr>}
              </tbody>
            </table>
          )}
          {tab === "offers" && data && !Array.isArray(data) && (
            <div className="p-6 grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: "Total Offers", value: data.total_offers, color: "text-white" },
                { label: "Accepted", value: data.accepted, color: "text-emerald-400" },
                { label: "Rejected", value: data.rejected, color: "text-red-400" },
                { label: "Acceptance Rate", value: `${data.acceptance_rate_pct}%`, color: "text-indigo-400" },
              ].map((k) => (
                <div key={k.label} className="rounded-xl border border-white/[0.07] bg-white/[0.03] p-4">
                  <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">{k.label}</p>
                  <p className={`text-2xl font-bold ${k.color}`}>{k.value}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
