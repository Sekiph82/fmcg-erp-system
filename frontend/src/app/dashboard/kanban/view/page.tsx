"use client";
import { useEffect, useState, useRef } from "react";
import { useSearchParams } from "next/navigation";
import {
  kanbanApi, KanbanBoard, KanbanCard, KanbanColumn,
  CardPriority, PRIORITY_COLOR, PRIORITY_BADGE, STATUS_COLOR, STAGE_COLOR, PRIORITIES,
} from "@/lib/kanban";

function CardChip({ card, onMove, onOpen }: {
  card: KanbanCard;
  onMove: (cardId: string, colId: string) => void;
  onOpen: (card: KanbanCard) => void;
}) {
  const isOverdue = card.due_date && new Date(card.due_date) < new Date() && card.status === "active";
  return (
    <div
      draggable
      onDragStart={(e) => e.dataTransfer.setData("cardId", card.card_id)}
      onClick={() => onOpen(card)}
      className={`bg-white border-l-4 ${PRIORITY_BADGE[card.priority]} rounded shadow-sm p-2 cursor-pointer hover:shadow-md text-xs select-none`}
    >
      <div className="flex items-start justify-between gap-1">
        <span className="text-gray-400 font-mono">{card.card_no}</span>
        <span className={`rounded-full px-1.5 py-0.5 ${PRIORITY_COLOR[card.priority]}`}>{card.priority}</span>
      </div>
      <p className="font-medium text-gray-800 mt-0.5 line-clamp-2">{card.title}</p>
      <div className="flex items-center gap-1 mt-1 flex-wrap">
        {card.assigned_user_name && (
          <span className="bg-gray-100 text-gray-600 rounded-full px-1.5 py-0.5">{card.assigned_user_name}</span>
        )}
        {card.due_date && (
          <span className={`rounded-full px-1.5 py-0.5 ${isOverdue ? "bg-red-100 text-red-700 font-semibold" : "bg-gray-100 text-gray-500"}`}>
            {card.due_date}
          </span>
        )}
        {card.status === "blocked" && <span className="bg-red-100 text-red-700 rounded px-1.5">Blocked</span>}
        {card.comments.length > 0 && <span className="text-gray-400">💬 {card.comments.length}</span>}
        {card.tags && card.tags.split(",").slice(0,2).map(t => (
          <span key={t} className="bg-indigo-50 text-indigo-600 rounded px-1">{t.trim()}</span>
        ))}
      </div>
    </div>
  );
}

export default function KanbanViewPage() {
  const searchParams = useSearchParams();
  const boardIdParam = searchParams.get("board");
  const [boards, setBoards] = useState<KanbanBoard[]>([]);
  const [selectedBoardId, setSelectedBoardId] = useState(boardIdParam ?? "");
  const [board, setBoard] = useState<KanbanBoard | null>(null);
  const [cards, setCards] = useState<KanbanCard[]>([]);
  const [loading, setLoading] = useState(false);
  const [draggingOver, setDraggingOver] = useState<string | null>(null);
  const [selected, setSelected] = useState<KanbanCard | null>(null);
  const [showAddCard, setShowAddCard] = useState<string | null>(null);
  const [cardForm, setCardForm] = useState({ title: "", description: "", assigned_user_name: "", due_date: "", priority: "normal" as CardPriority, tags: "" });
  const [comment, setComment] = useState("");
  const [filterUser, setFilterUser] = useState("");
  const [filterPriority, setFilterPriority] = useState("");

  useEffect(() => {
    kanbanApi.listBoards().then(setBoards);
  }, []);

  useEffect(() => {
    if (!selectedBoardId) return;
    setLoading(true);
    Promise.all([kanbanApi.getBoard(selectedBoardId), kanbanApi.listCards({ board_id: selectedBoardId })])
      .then(([b, c]) => { setBoard(b); setCards(c); })
      .finally(() => setLoading(false));
  }, [selectedBoardId]);

  const reload = () => {
    if (!selectedBoardId) return;
    kanbanApi.listCards({ board_id: selectedBoardId }).then(setCards);
  };

  const handleDrop = async (e: React.DragEvent, colId: string) => {
    e.preventDefault();
    const cardId = e.dataTransfer.getData("cardId");
    if (!cardId) return;
    setDraggingOver(null);
    await kanbanApi.moveCard(cardId, { target_column_id: colId, position: 0 });
    reload();
  };

  const addCard = async (colId: string) => {
    if (!cardForm.title || !selectedBoardId) return;
    await kanbanApi.createCard(selectedBoardId, {
      column_id: colId,
      title: cardForm.title,
      description: cardForm.description || undefined,
      assigned_user_name: cardForm.assigned_user_name || undefined,
      due_date: cardForm.due_date || undefined,
      priority: cardForm.priority,
      tags: cardForm.tags || undefined,
    });
    setShowAddCard(null);
    setCardForm({ title: "", description: "", assigned_user_name: "", due_date: "", priority: "normal", tags: "" });
    reload();
  };

  const postComment = async () => {
    if (!selected || !comment) return;
    await kanbanApi.addComment(selected.card_id, { body: comment });
    setComment("");
    const refreshed = await kanbanApi.getCard(selected.card_id);
    setSelected(refreshed);
    reload();
  };

  const updateCardStatus = async (status: string) => {
    if (!selected) return;
    await kanbanApi.updateCard(selected.card_id, { status: status as "active" | "blocked" | "done" });
    const refreshed = await kanbanApi.getCard(selected.card_id);
    setSelected(refreshed);
    reload();
  };

  const filteredCards = (colId: string) =>
    cards.filter(c => {
      if (c.column_id !== colId) return false;
      if (filterUser && c.assigned_user_name !== filterUser) return false;
      if (filterPriority && c.priority !== filterPriority) return false;
      return true;
    });

  const allUsers = Array.from(new Set(cards.map(c => c.assigned_user_name).filter(Boolean))) as string[];

  return (
    <div className="p-4 space-y-3 h-full flex flex-col">
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-xl font-bold text-gray-900">Board View</h1>
        <select className="border rounded px-2 py-1 text-sm" value={selectedBoardId}
          onChange={(e) => setSelectedBoardId(e.target.value)}>
          <option value="">Select board…</option>
          {boards.map(b => <option key={b.board_id} value={b.board_id}>{b.board_name}</option>)}
        </select>
        {selectedBoardId && (
          <>
            <select className="border rounded px-2 py-1 text-sm" value={filterUser}
              onChange={(e) => setFilterUser(e.target.value)}>
              <option value="">All Users</option>
              {allUsers.map(u => <option key={u} value={u}>{u}</option>)}
            </select>
            <select className="border rounded px-2 py-1 text-sm" value={filterPriority}
              onChange={(e) => setFilterPriority(e.target.value)}>
              <option value="">All Priorities</option>
              {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </>
        )}
      </div>

      {loading ? <p className="text-gray-500 text-sm">Loading…</p> : board ? (
        <div className="flex gap-3 overflow-x-auto pb-4 flex-1">
          {board.columns.map(col => {
            const colCards = filteredCards(col.column_id);
            const overWip = col.wip_limit && colCards.length > col.wip_limit;
            return (
              <div key={col.column_id}
                className={`shrink-0 w-64 flex flex-col rounded-lg border bg-gray-50 ${STAGE_COLOR[col.stage_type]} overflow-hidden`}
                onDragOver={(e) => { e.preventDefault(); setDraggingOver(col.column_id); }}
                onDragLeave={() => setDraggingOver(null)}
                onDrop={(e) => handleDrop(e, col.column_id)}
              >
                <div className="px-3 py-2 border-b flex items-center justify-between"
                  style={{ borderTopColor: col.color, borderTopWidth: 3 }}>
                  <span className="text-sm font-semibold text-gray-700">{col.column_name}</span>
                  <div className="flex items-center gap-1">
                    <span className={`text-xs font-bold rounded-full px-2 py-0.5 ${overWip ? "bg-red-100 text-red-700" : "bg-gray-200 text-gray-600"}`}>
                      {colCards.length}{col.wip_limit ? `/${col.wip_limit}` : ""}
                    </span>
                  </div>
                </div>
                <div className={`flex-1 overflow-y-auto p-2 space-y-2 min-h-[100px] ${draggingOver === col.column_id ? "bg-blue-50" : ""}`}>
                  {colCards.map(card => (
                    <CardChip key={card.card_id} card={card}
                      onMove={(cardId, colId) => kanbanApi.moveCard(cardId, { target_column_id: colId, position: 0 }).then(reload)}
                      onOpen={setSelected}
                    />
                  ))}
                </div>
                <div className="p-2 border-t">
                  {showAddCard === col.column_id ? (
                    <div className="space-y-1">
                      <input autoFocus className="w-full border rounded px-2 py-1 text-xs" placeholder="Card title…"
                        value={cardForm.title} onChange={(e) => setCardForm({ ...cardForm, title: e.target.value })}
                        onKeyDown={(e) => { if (e.key === "Enter") addCard(col.column_id); if (e.key === "Escape") setShowAddCard(null); }}
                      />
                      <input className="w-full border rounded px-2 py-1 text-xs" placeholder="Assignee"
                        value={cardForm.assigned_user_name} onChange={(e) => setCardForm({ ...cardForm, assigned_user_name: e.target.value })} />
                      <div className="flex gap-1">
                        <input type="date" className="flex-1 border rounded px-2 py-1 text-xs"
                          value={cardForm.due_date} onChange={(e) => setCardForm({ ...cardForm, due_date: e.target.value })} />
                        <select className="border rounded px-1 py-1 text-xs" value={cardForm.priority}
                          onChange={(e) => setCardForm({ ...cardForm, priority: e.target.value as CardPriority })}>
                          {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
                        </select>
                      </div>
                      <div className="flex gap-1">
                        <button onClick={() => addCard(col.column_id)}
                          className="flex-1 rounded bg-blue-600 py-1 text-xs text-white hover:bg-blue-700">Add</button>
                        <button onClick={() => setShowAddCard(null)}
                          className="flex-1 rounded border py-1 text-xs text-gray-600 hover:bg-gray-50">Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <button onClick={() => setShowAddCard(col.column_id)}
                      className="w-full rounded py-1 text-xs text-gray-400 hover:bg-gray-100 hover:text-gray-700 text-left px-2">
                      + Add card
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : selectedBoardId ? null : (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-gray-400">Select a board above to start.</p>
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-end z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md h-full max-h-[calc(100vh-2rem)] flex flex-col overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-gray-400">{selected.card_no}</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_COLOR[selected.priority]}`}>{selected.priority}</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[selected.status]}`}>{selected.status}</span>
              </div>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-700 text-xl">✕</button>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <h2 className="font-bold text-gray-900 text-base">{selected.title}</h2>
              {selected.description && <p className="text-sm text-gray-600">{selected.description}</p>}

              <div className="grid grid-cols-2 gap-2 text-xs text-gray-500">
                {selected.assigned_user_name && <div><span className="font-medium">Assigned:</span> {selected.assigned_user_name}</div>}
                {selected.due_date && <div><span className="font-medium">Due:</span> {selected.due_date}</div>}
                {selected.tags && <div className="col-span-2"><span className="font-medium">Tags:</span> {selected.tags}</div>}
                {selected.reference_type && <div className="col-span-2"><span className="font-medium">Ref:</span> {selected.reference_type} #{selected.reference_id}</div>}
              </div>

              <div className="flex gap-2">
                {selected.status !== "blocked" && (
                  <button onClick={() => updateCardStatus("blocked")}
                    className="rounded border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50">Mark Blocked</button>
                )}
                {selected.status !== "active" && (
                  <button onClick={() => updateCardStatus("active")}
                    className="rounded border border-green-200 px-2 py-1 text-xs text-green-600 hover:bg-green-50">Mark Active</button>
                )}
                {selected.status !== "done" && (
                  <button onClick={() => updateCardStatus("done")}
                    className="rounded border border-gray-200 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50">Mark Done</button>
                )}
              </div>

              {selected.activities.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-gray-600 mb-2">Activity</h3>
                  <div className="space-y-1.5">
                    {selected.activities.slice(0, 8).map(a => (
                      <div key={a.activity_id} className="flex gap-2 text-xs text-gray-500">
                        <span className="text-gray-400 w-20 shrink-0">{new Date(a.created_at).toLocaleString().slice(0,10)}</span>
                        <span className="capitalize font-medium text-gray-700">{a.event_type.replace(/_/g," ")}</span>
                        {a.from_value && <span>from <em>{a.from_value}</em></span>}
                        {a.to_value && <span>→ <em>{a.to_value}</em></span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <h3 className="text-xs font-semibold text-gray-600 mb-2">Comments ({selected.comments.length})</h3>
                <div className="space-y-2 mb-2">
                  {selected.comments.map(c => (
                    <div key={c.comment_id} className="bg-gray-50 rounded p-2 text-xs">
                      <div className="flex items-center gap-1 text-gray-400 mb-0.5">
                        <span className="font-medium text-gray-700">{c.author_name ?? "Anonymous"}</span>
                        <span>·</span>
                        <span>{new Date(c.created_at).toLocaleString()}</span>
                      </div>
                      <p className="text-gray-700">{c.body}</p>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input className="flex-1 border rounded px-2 py-1 text-xs" placeholder="Add comment…"
                    value={comment} onChange={(e) => setComment(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) postComment(); }}
                  />
                  <button onClick={postComment} className="rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700">Post</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
