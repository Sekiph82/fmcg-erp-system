"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { kanbanApi, KanbanDashboard, PRIORITY_COLOR } from "@/lib/kanban";

export default function KanbanDashboardPage() {
  const [dash, setDash] = useState<KanbanDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);

  useEffect(() => {
    kanbanApi.getDashboard().then(setDash).finally(() => setLoading(false));
  }, []);

  const seed = async () => {
    setSeeding(true);
    const r = await kanbanApi.seedBoards();
    setSeeding(false);
    alert(`Seeded ${r.created} default boards.`);
    kanbanApi.getDashboard().then(setDash);
  };

  const kpis = dash ? [
    { label: "Total Boards", value: dash.total_boards },
    { label: "Active Boards", value: dash.active_boards, color: "text-green-600" },
    { label: "Total Cards", value: dash.total_cards },
    { label: "Active Cards", value: dash.active_cards, color: "text-blue-600" },
    { label: "Overdue", value: dash.overdue_cards, color: "text-red-600" },
    { label: "Blocked", value: dash.blocked_cards, color: "text-orange-600" },
    { label: "Done", value: dash.done_cards, color: "text-green-600" },
  ] : [];

  const links = [
    { href: "/dashboard/kanban/boards", label: "All Boards" },
    { href: "/dashboard/kanban/view", label: "Board View" },
    { href: "/dashboard/kanban/cards", label: "All Cards" },
    { href: "/dashboard/kanban/reports", label: "Reports" },
    { href: "/dashboard/kanban/ai", label: "AI Insights" },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Kanban Boards</h1>
        <button onClick={seed} disabled={seeding}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50">
          {seeding ? "Seeding…" : "Seed Default Boards"}
        </button>
      </div>

      {loading ? <p className="text-gray-500">Loading…</p> : (
        <>
          <div className="grid grid-cols-3 gap-4 lg:grid-cols-7">
            {kpis.map((k) => (
              <div key={k.label} className="bg-white rounded-lg border p-4 shadow-sm">
                <p className="text-xs text-gray-500">{k.label}</p>
                <p className={`text-2xl font-bold mt-1 ${k.color ?? "text-gray-900"}`}>{k.value}</p>
              </div>
            ))}
          </div>

          {dash && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="bg-white border rounded-lg p-4 shadow-sm">
                <h2 className="text-sm font-semibold text-gray-700 mb-3">By Priority</h2>
                <div className="space-y-1.5">
                  {Object.entries(dash.cards_by_priority).map(([p, c]) => (
                    <div key={p} className="flex items-center justify-between">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_COLOR[p as keyof typeof PRIORITY_COLOR] ?? ""}`}>
                        {p}
                      </span>
                      <span className="text-sm font-semibold">{c}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="bg-white border rounded-lg p-4 shadow-sm">
                <h2 className="text-sm font-semibold text-gray-700 mb-3">By Module</h2>
                <div className="space-y-1.5">
                  {dash.cards_by_module.map((m) => (
                    <div key={m.module} className="flex items-center justify-between">
                      <span className="text-sm text-gray-700 capitalize">{m.module}</span>
                      <span className="text-sm font-semibold text-gray-700">{m.count}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="bg-white border rounded-lg p-4 shadow-sm">
                <h2 className="text-sm font-semibold text-gray-700 mb-3">Top Assignees</h2>
                <div className="space-y-1.5">
                  {dash.top_assignees.map((a) => (
                    <div key={a.user} className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">{a.user}</span>
                      <span className="text-sm font-semibold text-blue-600">{a.count} cards</span>
                    </div>
                  ))}
                  {dash.top_assignees.length === 0 && <p className="text-gray-400 text-xs">No assigned cards yet.</p>}
                </div>
              </div>
            </div>
          )}
        </>
      )}

      <div className="bg-white border rounded-lg p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Quick Navigation</h2>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
          {links.map((l) => (
            <Link key={l.href} href={l.href}
              className="block rounded border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-700 hover:bg-blue-100 text-center">
              {l.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
