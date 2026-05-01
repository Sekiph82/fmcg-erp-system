"use client";
import { useEffect, useState } from "react";
import { chatterApi, CTAIRec, CTAIAgentType, CTAIRecStatus } from "@/lib/chatter";

const AGENT_META: Record<CTAIAgentType, { label: string; desc: string; color: string }> = {
  activity_summarizer: {
    label: "Activity Summarizer",
    desc: "Identifies high-activity records with 10+ events and suggests pinning a summary comment to help team members catch up quickly.",
    color: "bg-blue-50 border-blue-200",
  },
  follow_up_assistant: {
    label: "Follow-up Assistant",
    desc: "Detects @mentions that are older than 48 hours without a response or notification, and flags them for follow-up.",
    color: "bg-orange-50 border-orange-200",
  },
  insight_extractor: {
    label: "Insight Extractor",
    desc: "Scans recent comments for problem-related keywords (error, delay, stuck, urgent) and surfaces patterns and inactive modules.",
    color: "bg-purple-50 border-purple-200",
  },
};

const STATUS_COLOR: Record<CTAIRecStatus, string> = {
  pending: "bg-yellow-100 text-yellow-700",
  acknowledged: "bg-blue-100 text-blue-700",
  actioned: "bg-green-100 text-green-700",
  dismissed: "bg-gray-100 text-gray-500",
};

export default function ChatterAIPage() {
  const [recs, setRecs] = useState<CTAIRec[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState<CTAIAgentType | null>(null);

  const load = () => chatterApi.listAIRecs().then(setRecs).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const run = async (agent: CTAIAgentType) => {
    setRunning(agent);
    try {
      if (agent === "activity_summarizer") await chatterApi.runActivitySummarizer();
      else if (agent === "follow_up_assistant") await chatterApi.runFollowUpAssistant();
      else await chatterApi.runInsightExtractor();
      load();
    } finally { setRunning(null); }
  };

  const ack = async (id: string, status: CTAIRecStatus) => {
    await chatterApi.ackAIRec(id, { status });
    load();
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold text-gray-900">Chatter AI Insights</h1>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {(Object.entries(AGENT_META) as [CTAIAgentType, typeof AGENT_META[CTAIAgentType]][]).map(([type, meta]) => (
          <div key={type} className={`border rounded-lg p-4 ${meta.color}`}>
            <h2 className="font-semibold text-gray-800 text-sm">{meta.label}</h2>
            <p className="text-xs text-gray-600 mt-1 mb-3">{meta.desc}</p>
            <button onClick={() => run(type)} disabled={running === type}
              className="w-full rounded bg-gray-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-gray-700 disabled:opacity-50">
              {running === type ? "Running…" : "Run Agent"}
            </button>
          </div>
        ))}
      </div>

      <div className="bg-white border rounded-lg shadow-sm">
        <div className="px-4 py-3 border-b">
          <h2 className="font-semibold text-gray-800 text-sm">
            AI Recommendations ({recs.filter(r => r.status === "pending").length} pending)
          </h2>
        </div>
        {loading ? <p className="text-gray-500 text-sm p-4">Loading…</p> :
          recs.length === 0
            ? <p className="text-gray-400 text-sm text-center py-8">No recommendations yet.</p>
            : (
              <div className="divide-y">
                {recs.map(r => (
                  <div key={r.rec_id} className="px-4 py-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                          <span className="text-xs font-medium text-gray-500 uppercase">
                            {AGENT_META[r.agent_type]?.label}
                          </span>
                          <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[r.status]}`}>
                            {r.status}
                          </span>
                          {r.score != null && <span className="text-xs text-gray-400">Score: {r.score}</span>}
                          {r.reference_type && (
                            <span className="text-xs bg-gray-100 text-gray-500 rounded px-1.5 py-0.5 capitalize">
                              {r.reference_type.replace("_", " ")}
                            </span>
                          )}
                        </div>
                        <p className="text-sm font-semibold text-gray-800">{r.title}</p>
                        <p className="text-sm text-gray-600">{r.body}</p>
                      </div>
                      {r.status === "pending" && (
                        <div className="flex flex-col gap-1 shrink-0">
                          <button onClick={() => ack(r.rec_id, "acknowledged")}
                            className="rounded border border-blue-300 px-2 py-0.5 text-xs text-blue-600 hover:bg-blue-50">Ack</button>
                          <button onClick={() => ack(r.rec_id, "actioned")}
                            className="rounded border border-green-300 px-2 py-0.5 text-xs text-green-600 hover:bg-green-50">Action</button>
                          <button onClick={() => ack(r.rec_id, "dismissed")}
                            className="rounded border border-gray-200 px-2 py-0.5 text-xs text-gray-500 hover:bg-gray-50">Dismiss</button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )
        }
      </div>
    </div>
  );
}
