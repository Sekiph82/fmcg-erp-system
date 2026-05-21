"use client";
import { useEffect, useState } from "react";
import { kanbanApi, KanbanBoard } from "@/lib/kanban";

export default function KanbanReportsPage() {
  const [boards, setBoards] = useState<KanbanBoard[]>([]);
  const [selectedBoard, setSelectedBoard] = useState("");
  const [bottleneck, setBottleneck] = useState<unknown>(null);
  const [completion, setCompletion] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { kanbanApi.listBoards().then(setBoards); }, []);

  const run = async () => {
    if (!selectedBoard) { alert("Select a board"); return; }
    setLoading(true);
    setBottleneck(null);
    setCompletion(null);
    try {
      const [b, c] = await Promise.all([
        kanbanApi.reportBottleneck(selectedBoard),
        kanbanApi.reportCompletion(selectedBoard),
      ]);
      setBottleneck(b);
      setCompletion(c);
    } finally { setLoading(false); }
  };

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Kanban Reports</h1>

      <div className="flex gap-3 items-end">
        <div>
          <label className="text-xs text-gray-500">Board</label>
          <select className="block border rounded px-2 py-1 text-sm mt-1 w-64" value={selectedBoard}
            onChange={(e) => setSelectedBoard(e.target.value)}>
            <option value="">Select board…</option>
            {boards.map(b => <option key={b.board_id} value={b.board_id}>{b.board_name}</option>)}
          </select>
        </div>
        <button onClick={run} disabled={loading}
          className="rounded bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
          {loading ? "Loading…" : "Run Reports"}
        </button>
      </div>

      {!!completion && (() => {
        const c = completion as { total: number; done: number; completion_rate_pct: number };
        return (
          <div className="bg-white border rounded-lg p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Completion Rate</h2>
            <div className="flex gap-6 items-center">
              <div className="text-center">
                <p className="text-3xl font-bold text-blue-700">{c.completion_rate_pct}%</p>
                <p className="text-xs text-gray-500">Completion Rate</p>
              </div>
              <div className="flex-1">
                <div className="bg-gray-100 rounded-full h-6 overflow-hidden">
                  <div className="bg-green-500 h-6 rounded-full flex items-center justify-center text-xs font-semibold text-white transition-all"
                    style={{ width: `${c.completion_rate_pct}%` }}>
                    {c.done} done
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-1">{c.done} of {c.total} cards completed</p>
              </div>
            </div>
          </div>
        );
      })()}

      {!!bottleneck && (() => {
        const rows = bottleneck as { column_id: string; column_name: string; card_count: number; wip_limit: number | null; over_wip_limit: boolean }[];
        const maxCards = Math.max(...rows.map(r => r.card_count), 1);
        return (
          <div className="bg-white border rounded-lg p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Bottleneck Analysis — Cards per Column</h2>
            <div className="space-y-2">
              {rows.map(r => (
                <div key={r.column_id} className="flex items-center gap-3">
                  <span className={`w-32 text-sm truncate ${r.over_wip_limit ? "font-semibold text-red-700" : "text-gray-700"}`}>
                    {r.column_name}
                    {r.over_wip_limit && " ⚠"}
                  </span>
                  <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
                    <div
                      className={`h-5 rounded-full flex items-center px-2 text-xs font-semibold text-white ${r.over_wip_limit ? "bg-red-500" : "bg-blue-500"}`}
                      style={{ width: `${(r.card_count / maxCards) * 100}%`, minWidth: r.card_count > 0 ? "32px" : "0" }}
                    >
                      {r.card_count > 0 ? r.card_count : ""}
                    </div>
                  </div>
                  {r.wip_limit && (
                    <span className={`text-xs w-16 text-right ${r.over_wip_limit ? "text-red-600 font-semibold" : "text-gray-400"}`}>
                      WIP: {r.wip_limit}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        );
      })()}
    </div>
  );
}
