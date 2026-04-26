"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { crmApi, CRMRecord, CRMStage, fmtCurrency, TEMPERATURE_COLORS, STATUS_COLORS } from "@/lib/crm_pipeline";

export default function PipelineBoardPage() {
  const [stages, setStages] = useState<CRMStage[]>([]);
  const [records, setRecords] = useState<CRMRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [movingId, setMovingId] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [stgs, recs] = await Promise.all([
        crmApi.getStages(true),
        crmApi.getAllRecords({ status: "OPEN", limit: 500 }),
      ]);
      setStages(stgs);
      setRecords(recs);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleDrop = async (e: React.DragEvent, targetStageId: string) => {
    e.preventDefault();
    const recordId = e.dataTransfer.getData("recordId");
    if (!recordId || movingId) return;
    setMovingId(recordId);
    try {
      await crmApi.updateRecord(recordId, { stage_id: targetStageId });
      await load();
    } catch (err) { console.error(err); }
    setMovingId(null);
  };

  const recordsByStage = (stageId: string) =>
    records.filter(r => r.stage_id === stageId);

  const stageTotal = (stageId: string) =>
    recordsByStage(stageId).reduce((s, r) => s + (r.expected_revenue || 0), 0);

  if (loading) return <div className="p-6 text-gray-500">Loading pipeline…</div>;

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Pipeline Board</h1>
        <div className="flex gap-2">
          <Link href="/dashboard/crm/leads" className="text-sm text-blue-600 hover:underline">+ Lead</Link>
          <Link href="/dashboard/crm/opportunities" className="text-sm text-purple-600 hover:underline">+ Opportunity</Link>
        </div>
      </div>

      <div className="text-xs text-gray-400">Drag cards between stages to move records</div>

      {/* Kanban Board */}
      <div className="flex gap-4 overflow-x-auto pb-4" style={{ minHeight: "500px" }}>
        {stages.filter(s => s.stage_type !== "TERMINAL").map(stage => {
          const stageRecs = recordsByStage(stage.id);
          return (
            <div
              key={stage.id}
              className="flex-shrink-0 w-64 bg-gray-50 rounded-xl border"
              onDragOver={e => e.preventDefault()}
              onDrop={e => handleDrop(e, stage.id)}
            >
              {/* Column Header */}
              <div className="p-3 border-b" style={{ borderTop: `3px solid ${stage.color_code || "#6B7280"}` }}>
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-sm text-gray-800">{stage.stage_name}</span>
                  <span className="text-xs bg-white border rounded-full px-2 py-0.5 text-gray-600">
                    {stageRecs.length}
                  </span>
                </div>
                <div className="text-xs text-gray-500 mt-0.5">{fmtCurrency(stageTotal(stage.id))}</div>
              </div>

              {/* Cards */}
              <div className="p-2 space-y-2 min-h-[400px]">
                {stageRecs.map(rec => (
                  <div
                    key={rec.id}
                    draggable
                    onDragStart={e => e.dataTransfer.setData("recordId", rec.id)}
                    className="bg-white rounded-lg border shadow-sm p-3 cursor-grab hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between gap-1">
                      <div className="font-medium text-xs text-gray-800 leading-snug">{rec.company_name}</div>
                      <div className="w-2 h-2 rounded-full flex-shrink-0 mt-1"
                        style={{ background: TEMPERATURE_COLORS[rec.temperature] }} />
                    </div>
                    <div className="text-xs text-gray-400 mt-0.5">
                      {rec.lead_code || rec.opportunity_code}
                    </div>
                    {rec.expected_revenue ? (
                      <div className="text-xs font-semibold text-indigo-700 mt-1">
                        {fmtCurrency(rec.expected_revenue, rec.currency)}
                      </div>
                    ) : null}
                    <div className="flex items-center justify-between mt-2">
                      <div className="text-xs text-gray-400">{rec.probability_pct ?? 0}%</div>
                      {rec.expected_close_date && (
                        <div className="text-xs text-gray-400">{rec.expected_close_date}</div>
                      )}
                    </div>
                    <Link href={`/dashboard/crm/records/${rec.id}`}
                      className="block text-center text-xs text-blue-600 hover:underline mt-2 pt-1 border-t">
                      View
                    </Link>
                  </div>
                ))}
                {stageRecs.length === 0 && (
                  <div className="text-center text-xs text-gray-300 py-4">No records</div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary Footer */}
      <div className="bg-white rounded-xl border shadow-sm p-4">
        <div className="text-xs text-gray-500 mb-2">Pipeline Summary</div>
        <div className="flex flex-wrap gap-4">
          <div>
            <span className="text-xs text-gray-400">Total Open</span>
            <div className="font-semibold text-gray-800">{records.length} records</div>
          </div>
          <div>
            <span className="text-xs text-gray-400">Pipeline Value</span>
            <div className="font-semibold text-gray-800">
              {fmtCurrency(records.reduce((s, r) => s + (r.expected_revenue || 0), 0))}
            </div>
          </div>
          <div>
            <span className="text-xs text-gray-400">Weighted Value</span>
            <div className="font-semibold text-indigo-700">
              {fmtCurrency(records.reduce((s, r) => s + (r.expected_revenue || 0) * (r.probability_pct || 0) / 100, 0))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
