"use client";
import { useCallback, useEffect, useState } from "react";
import { kanbanApi, KanbanCard, CardPriority, CardStatus, PRIORITY_COLOR, STATUS_COLOR, PRIORITIES } from "@/lib/kanban";

const STATUSES: CardStatus[] = ["active","blocked","done","archived"];

export default function AllCardsPage() {
  const [cards, setCards] = useState<KanbanCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ priority: "", status: "", assigned_user_id: "", overdue_only: false });
  const [selected, setSelected] = useState<KanbanCard | null>(null);

  const load = useCallback(() =>
    kanbanApi.listCards({
      priority: filters.priority || undefined,
      status: filters.status || undefined,
      assigned_user_id: filters.assigned_user_id || undefined,
      overdue_only: filters.overdue_only || undefined,
    }).then(setCards).finally(() => setLoading(false)), [filters]);

  useEffect(() => { load(); }, [load]);

  const isOverdue = (c: KanbanCard) => c.due_date && new Date(c.due_date) < new Date() && c.status === "active";

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold text-gray-900">All Kanban Cards</h1>

      <div className="flex gap-3 flex-wrap">
        <select className="border rounded px-2 py-1 text-sm" value={filters.priority}
          onChange={(e) => setFilters({ ...filters, priority: e.target.value })}>
          <option value="">All Priorities</option>
          {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <select className="border rounded px-2 py-1 text-sm" value={filters.status}
          onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
          <option value="">All Statuses</option>
          {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <input className="border rounded px-2 py-1 text-sm w-36" placeholder="Assigned user ID…"
          value={filters.assigned_user_id} onChange={(e) => setFilters({ ...filters, assigned_user_id: e.target.value })} />
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input type="checkbox" checked={filters.overdue_only}
            onChange={(e) => setFilters({ ...filters, overdue_only: e.target.checked })} />
          Overdue only
        </label>
        <span className="text-xs text-gray-400 self-center">{cards.length} cards</span>
      </div>

      {loading ? <p className="text-gray-500 text-sm">Loading…</p> : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["#","Title","Assigned","Due","Priority","Status","Tags","Comments"].map(h=>(
                  <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {cards.map(c => (
                <tr key={c.card_id} className={`hover:bg-gray-50 cursor-pointer ${isOverdue(c) ? "bg-red-50" : ""}`}
                  onClick={() => setSelected(c)}>
                  <td className="px-3 py-2 font-mono text-xs text-gray-400">{c.card_no}</td>
                  <td className="px-3 py-2 font-medium text-gray-800 max-w-[200px] truncate">{c.title}</td>
                  <td className="px-3 py-2 text-gray-600">{c.assigned_user_name ?? "—"}</td>
                  <td className={`px-3 py-2 ${isOverdue(c) ? "text-red-600 font-semibold" : "text-gray-600"}`}>{c.due_date ?? "—"}</td>
                  <td className="px-3 py-2"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_COLOR[c.priority]}`}>{c.priority}</span></td>
                  <td className="px-3 py-2"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[c.status]}`}>{c.status}</span></td>
                  <td className="px-3 py-2 text-xs text-gray-400 max-w-[100px] truncate">{c.tags ?? "—"}</td>
                  <td className="px-3 py-2 text-center text-gray-400">{c.comments.length > 0 ? `💬 ${c.comments.length}` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {cards.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">No cards found.</p>}
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-3 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-gray-400">{selected.card_no}</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_COLOR[selected.priority]}`}>{selected.priority}</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[selected.status]}`}>{selected.status}</span>
              </div>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-700 text-xl">✕</button>
            </div>
            <h2 className="font-bold text-gray-900">{selected.title}</h2>
            {selected.description && <p className="text-sm text-gray-600">{selected.description}</p>}
            <div className="grid grid-cols-2 gap-2 text-xs text-gray-500">
              {selected.assigned_user_name && <div><strong>Assigned:</strong> {selected.assigned_user_name}</div>}
              {selected.due_date && <div><strong>Due:</strong> {selected.due_date}</div>}
              {selected.tags && <div className="col-span-2"><strong>Tags:</strong> {selected.tags}</div>}
              {selected.reference_type && <div className="col-span-2"><strong>Ref:</strong> {selected.reference_type} #{selected.reference_id}</div>}
            </div>
            {selected.comments.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-gray-600 mb-1">Comments</h3>
                {selected.comments.slice(0,5).map(c => (
                  <div key={c.comment_id} className="text-xs bg-gray-50 rounded p-2 mb-1">
                    <span className="font-medium text-gray-700">{c.author_name ?? "Anonymous"}:</span> {c.body}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
