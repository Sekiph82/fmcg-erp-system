"use client";
import { useEffect, useState } from "react";
import { qmsApi, QMSAIRecommendation, RISK_BG, QMSAIAgentType, QMSAIRecStatus } from "@/lib/qms";

const AGENT_INFO: Record<QMSAIAgentType, { label: string; desc: string; color: string }> = {
  QUALITY_RISK_PREDICTOR: {
    label: "Quality Risk Predictor",
    desc: "Predicts likely QC failures and high-risk batches before they occur",
    color: "border-red-200 bg-red-50",
  },
  DEVIATION_ANALYZER: {
    label: "Deviation Analyzer",
    desc: "Detects recurring failures and process instability patterns",
    color: "border-orange-200 bg-orange-50",
  },
  HACCP_ASSISTANT: {
    label: "HACCP Assistant",
    desc: "Suggests missing CCPs and identifies weak control points",
    color: "border-teal-200 bg-teal-50",
  },
};

const STATUS_BG_AI: Record<QMSAIRecStatus, string> = {
  PENDING: "bg-yellow-100 text-yellow-800",
  ACCEPTED: "bg-green-100 text-green-800",
  REJECTED: "bg-gray-100 text-gray-600",
  APPLIED: "bg-teal-100 text-teal-800",
};

export default function QMSAIPage() {
  const [recs, setRecs] = useState<QMSAIRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState<QMSAIAgentType | null>(null);
  const [agentFilter, setAgentFilter] = useState<QMSAIAgentType | "">("");
  const [statusFilter, setStatusFilter] = useState<QMSAIRecStatus | "">("");
  const [reviewModal, setReviewModal] = useState<{ id: string; status: QMSAIRecStatus } | null>(null);
  const [reviewNote, setReviewNote] = useState("");

  const load = () => {
    setLoading(true);
    qmsApi.listAIRecs({
      agent_type: agentFilter || undefined,
      status: statusFilter || undefined,
    }).then(setRecs).finally(() => setLoading(false));
  };

  useEffect(load, [agentFilter, statusFilter]);

  const runAgent = async (agent: QMSAIAgentType) => {
    setRunning(agent);
    try {
      if (agent === "QUALITY_RISK_PREDICTOR") await qmsApi.runQualityRisk();
      else if (agent === "DEVIATION_ANALYZER") await qmsApi.runDeviationAnalyzer();
      else if (agent === "HACCP_ASSISTANT") await qmsApi.runHACCPAssistant();
      load();
    } finally {
      setRunning(null);
    }
  };

  const handleReview = async (status: QMSAIRecStatus) => {
    if (!reviewModal) return;
    await qmsApi.reviewAIRec(reviewModal.id, status, reviewNote);
    setReviewModal(null);
    setReviewNote("");
    load();
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">QMS AI Agents</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Intelligent quality risk prediction, deviation analysis, and HACCP assistance
        </p>
      </div>

      {/* Agents */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {(Object.keys(AGENT_INFO) as QMSAIAgentType[]).map(agent => {
          const info = AGENT_INFO[agent];
          const isRunning = running === agent;
          return (
            <div key={agent} className={`border rounded-xl p-5 ${info.color}`}>
              <h3 className="font-semibold text-gray-800">{info.label}</h3>
              <p className="text-xs text-gray-600 mt-1 mb-4">{info.desc}</p>
              <button
                onClick={() => runAgent(agent)}
                disabled={isRunning || running !== null}
                className="w-full px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                {isRunning ? "Running…" : "Run Agent"}
              </button>
            </div>
          );
        })}
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <select className="border rounded-lg px-3 py-2 text-sm text-gray-700 bg-white"
          value={agentFilter} onChange={e => setAgentFilter(e.target.value as QMSAIAgentType | "")}>
          <option value="">All Agents</option>
          <option value="QUALITY_RISK_PREDICTOR">Quality Risk Predictor</option>
          <option value="DEVIATION_ANALYZER">Deviation Analyzer</option>
          <option value="HACCP_ASSISTANT">HACCP Assistant</option>
        </select>
        <select className="border rounded-lg px-3 py-2 text-sm text-gray-700 bg-white"
          value={statusFilter} onChange={e => setStatusFilter(e.target.value as QMSAIRecStatus | "")}>
          <option value="">All Statuses</option>
          <option value="PENDING">Pending</option>
          <option value="ACCEPTED">Accepted</option>
          <option value="REJECTED">Rejected</option>
          <option value="APPLIED">Applied</option>
        </select>
      </div>

      {/* Recommendations */}
      <div className="space-y-4">
        {loading ? (
          <p className="text-gray-400 text-sm">Loading recommendations…</p>
        ) : recs.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-xl p-8 text-center">
            <p className="text-gray-400 text-sm">No AI recommendations yet. Run an agent to generate insights.</p>
          </div>
        ) : (
          recs.map(rec => (
            <div key={rec.id} className="bg-white border border-gray-200 rounded-xl p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">
                      {AGENT_INFO[rec.agent_type]?.label || rec.agent_type}
                    </span>
                    {rec.risk_level && (
                      <span className={`px-2 py-0.5 rounded text-xs ${RISK_BG[rec.risk_level]}`}>
                        {rec.risk_level}
                      </span>
                    )}
                    <span className={`px-2 py-0.5 rounded text-xs ${STATUS_BG_AI[rec.status]}`}>
                      {rec.status}
                    </span>
                    {rec.confidence_score && (
                      <span className="text-xs text-gray-400">{parseFloat(rec.confidence_score).toFixed(0)}% confidence</span>
                    )}
                  </div>
                  <h4 className="font-semibold text-gray-800">{rec.title}</h4>
                  <p className="text-sm text-gray-600 mt-1">{rec.explanation}</p>
                  <div className="mt-2 p-3 bg-indigo-50 rounded-lg">
                    <p className="text-xs font-semibold text-indigo-700 mb-0.5">Recommendation</p>
                    <p className="text-sm text-indigo-800">{rec.recommendation}</p>
                  </div>
                  {rec.review_note && (
                    <p className="text-xs text-gray-500 mt-2">Review note: {rec.review_note}</p>
                  )}
                </div>
                <div className="flex flex-col gap-2">
                  {rec.status === "PENDING" && (
                    <>
                      <button
                        onClick={() => setReviewModal({ id: rec.id, status: "ACCEPTED" })}
                        className="text-xs px-3 py-1.5 bg-green-600 text-white rounded-lg hover:bg-green-700 whitespace-nowrap"
                      >
                        Accept
                      </button>
                      <button
                        onClick={() => qmsApi.reviewAIRec(rec.id, "REJECTED").then(load)}
                        className="text-xs px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 whitespace-nowrap"
                      >
                        Dismiss
                      </button>
                    </>
                  )}
                  {rec.status === "ACCEPTED" && (
                    <button
                      onClick={() => qmsApi.reviewAIRec(rec.id, "APPLIED").then(load)}
                      className="text-xs px-3 py-1.5 bg-teal-600 text-white rounded-lg hover:bg-teal-700 whitespace-nowrap"
                    >
                      Mark Applied
                    </button>
                  )}
                </div>
              </div>
              <p className="text-xs text-gray-400 mt-2">{new Date(rec.created_at).toLocaleString()}</p>
            </div>
          ))
        )}
      </div>

      {reviewModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl border border-gray-200 p-6 w-full max-w-md space-y-4">
            <h3 className="font-semibold text-gray-800">Accept Recommendation</h3>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Review Note (optional)</label>
              <textarea className="border rounded-lg px-3 py-2 text-sm w-full" rows={3}
                value={reviewNote} onChange={e => setReviewNote(e.target.value)}
                placeholder="Document action taken or planned…" />
            </div>
            <div className="flex gap-3">
              <button onClick={() => handleReview("ACCEPTED")}
                className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700">
                Accept
              </button>
              <button onClick={() => setReviewModal(null)}
                className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
