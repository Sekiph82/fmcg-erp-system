"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { recruitmentApi, CandidatePipeline, RecruitmentStage, JobRequisition, PIPELINE_STATUS_COLOR } from "@/lib/recruitment";

export default function PipelineBoardPage() {
  const searchParams = useSearchParams();
  const reqIdParam = searchParams.get("requisition_id") ?? "";
  const [stages, setStages] = useState<RecruitmentStage[]>([]);
  const [pipeline, setPipeline] = useState<CandidatePipeline[]>([]);
  const [reqs, setReqs] = useState<JobRequisition[]>([]);
  const [selectedReq, setSelectedReq] = useState(reqIdParam);
  const [dragging, setDragging] = useState<string | null>(null);
  const [msg, setMsg] = useState("");

  const load = async () => {
    const [s, r] = await Promise.all([recruitmentApi.listStages(), recruitmentApi.listRequisitions()]);
    setStages(s.filter((s) => s.stage_type === "active" || s.stage_type === "final_hire")); setReqs(r);
  };
  const loadPipeline = async () => {
    const pl = await recruitmentApi.listPipeline(selectedReq ? { requisition_id: selectedReq } : {});
    setPipeline(pl.filter((p) => p.status !== "rejected"));
  };

  useEffect(() => { load(); }, []);
  useEffect(() => { loadPipeline(); }, [selectedReq]);

  const stageMap: Record<string, CandidatePipeline[]> = {};
  for (const s of stages) stageMap[s.stage_id] = [];
  for (const p of pipeline) { if (stageMap[p.stage_id]) stageMap[p.stage_id].push(p); else stageMap[p.stage_id] = [p]; }

  const handleDrop = async (targetStageId: string) => {
    if (!dragging) return;
    try { await recruitmentApi.moveStage(dragging, { stage_id: targetStageId }); await loadPipeline(); setMsg("Moved"); setTimeout(() => setMsg(""), 1500); }
    catch (e: any) { setMsg(e.message); }
    setDragging(null);
  };

  return (
    <div className="p-6 space-y-4 min-h-screen bg-[#060d18] text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Pipeline Board</h1>
          <p className="text-slate-500 text-sm mt-0.5">Drag candidates between stages</p>
        </div>
        <select value={selectedReq} onChange={(e) => setSelectedReq(e.target.value)}
          className="bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none w-72">
          <option value="">All Requisitions</option>
          {reqs.map((r) => <option key={r.requisition_id} value={r.requisition_id}>{r.requisition_code} — {r.job_title}</option>)}
        </select>
      </div>

      {msg && <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/10 p-3 text-sm text-indigo-300">{msg}</div>}

      <div className="flex gap-3 overflow-x-auto pb-4">
        {stages.map((stage) => {
          const cards = stageMap[stage.stage_id] ?? [];
          return (
            <div key={stage.stage_id} onDragOver={(e) => e.preventDefault()} onDrop={() => handleDrop(stage.stage_id)}
              className="flex-shrink-0 w-56 rounded-xl bg-white/[0.03] border border-white/[0.06] p-3 space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest">{stage.stage_name}</h3>
                <span className="text-[10px] bg-white/[0.06] rounded-full px-2 py-0.5 text-slate-500">{cards.length}</span>
              </div>
              {cards.map((p) => (
                <div key={p.pipeline_id} draggable onDragStart={() => setDragging(p.pipeline_id)} onDragEnd={() => setDragging(null)}
                  className="rounded-lg border border-white/[0.07] bg-[#0d1829] p-3 cursor-grab space-y-1.5 hover:bg-white/[0.04]">
                  <p className="text-xs font-medium text-slate-300">{p.candidate_id.slice(-8)}</p>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${PIPELINE_STATUS_COLOR[p.status]}`}>{p.status}</span>
                  <p className="text-[10px] text-slate-600">{p.application_date}</p>
                  <button onClick={() => recruitmentApi.rejectCandidate(p.pipeline_id, "Rejected from board").then(loadPipeline)}
                    className="text-[10px] text-red-400 hover:text-red-300">Reject</button>
                </div>
              ))}
              {cards.length === 0 && (
                <div className="border-2 border-dashed border-white/[0.05] rounded-lg p-3 text-center text-[10px] text-slate-600">Drop here</div>
              )}
            </div>
          );
        })}
        {stages.length === 0 && <p className="text-slate-500 text-sm">No stages — go to Stages to seed defaults first.</p>}
      </div>
    </div>
  );
}
