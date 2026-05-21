"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { kanbanApi, KanbanBoard, BoardModuleType, BoardVisibility, MODULE_LABEL, MODULE_TYPES, STAGE_COLOR } from "@/lib/kanban";

export default function BoardsPage() {
  const [boards, setBoards] = useState<KanbanBoard[]>([]);
  const [loading, setLoading] = useState(true);
  const [moduleFilter, setModuleFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    board_code: "", board_name: "", module_type: "tasks" as BoardModuleType,
    visibility: "team" as BoardVisibility, description: "", owner_name: "",
  });

  const load = () =>
    kanbanApi.listBoards({ module_type: moduleFilter || undefined })
      .then(setBoards).finally(() => setLoading(false));
  useEffect(() => { load(); }, [moduleFilter]);

  const submit = async () => {
    await kanbanApi.createBoard({ ...form, description: form.description || undefined, owner_name: form.owner_name || undefined });
    setShowForm(false);
    load();
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Kanban Boards</h1>
        <button onClick={() => setShowForm(true)}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + New Board
        </button>
      </div>

      <select className="border rounded px-2 py-1 text-sm" value={moduleFilter}
        onChange={(e) => setModuleFilter(e.target.value)}>
        <option value="">All Modules</option>
        {MODULE_TYPES.map(m => <option key={m} value={m}>{MODULE_LABEL[m]}</option>)}
      </select>

      {showForm && (
        <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
          <h2 className="font-semibold text-gray-800">New Board</h2>
          <div className="grid grid-cols-2 gap-3">
            {(["board_code","board_name","owner_name"] as const).map(f => (
              <div key={f}><label className="text-xs text-gray-500 capitalize">{f.replace(/_/g," ")}</label>
                <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={form[f]}
                  onChange={(e) => setForm({ ...form, [f]: e.target.value })} /></div>
            ))}
            <div><label className="text-xs text-gray-500">Module Type</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.module_type}
                onChange={(e) => setForm({ ...form, module_type: e.target.value as BoardModuleType })}>
                {MODULE_TYPES.map(m => <option key={m} value={m}>{MODULE_LABEL[m]}</option>)}
              </select></div>
            <div><label className="text-xs text-gray-500">Visibility</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.visibility}
                onChange={(e) => setForm({ ...form, visibility: e.target.value as BoardVisibility })}>
                {(["private","team","global"] as BoardVisibility[]).map(v => <option key={v} value={v}>{v}</option>)}
              </select></div>
            <div className="col-span-2"><label className="text-xs text-gray-500">Description</label>
              <textarea className="w-full border rounded px-2 py-1 text-sm mt-1" rows={2} value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
          </div>
          <div className="flex gap-2">
            <button onClick={submit} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">Save</button>
            <button onClick={() => setShowForm(false)} className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {loading ? <p className="text-gray-500 text-sm">Loading…</p> : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {boards.map(b => (
            <div key={b.board_id} className="bg-white border rounded-lg shadow-sm overflow-hidden">
              <div className="p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-gray-800">{b.board_name}</span>
                      <span className="rounded bg-blue-100 text-blue-700 px-2 py-0.5 text-xs">{MODULE_LABEL[b.module_type]}</span>
                    </div>
                    <p className="font-mono text-xs text-gray-400 mt-0.5">{b.board_code}</p>
                    {b.description && <p className="text-sm text-gray-500 mt-1">{b.description}</p>}
                    <div className="flex gap-2 mt-2 text-xs text-gray-400">
                      <span>{b.visibility}</span>
                      {b.owner_name && <span>· {b.owner_name}</span>}
                      <span>· {b.columns.length} columns</span>
                    </div>
                  </div>
                </div>
              </div>
              <div className="border-t px-4 py-2 bg-gray-50 flex items-center gap-1 overflow-x-auto">
                {b.columns.map(col => (
                  <div key={col.column_id}
                    className={`shrink-0 rounded px-2 py-1 text-xs font-medium border-t-2 ${STAGE_COLOR[col.stage_type]}`}
                    style={{ borderTopColor: col.color }}>
                    {col.column_name}
                    {col.card_count > 0 && <span className="ml-1 font-bold text-gray-600">{col.card_count}</span>}
                  </div>
                ))}
              </div>
              <div className="px-4 py-2 flex gap-2">
                <Link href={`/dashboard/kanban/view?board=${b.board_id}`}
                  className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700">
                  Open Board
                </Link>
              </div>
            </div>
          ))}
          {boards.length === 0 && (
            <p className="text-gray-400 text-sm col-span-3 text-center py-8">No boards. Seed defaults or create one.</p>
          )}
        </div>
      )}
    </div>
  );
}
