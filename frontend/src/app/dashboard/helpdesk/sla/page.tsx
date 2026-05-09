"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { helpdeskApi, Ticket, TicketStatus, TicketPriority, STATUS_COLOR, PRIORITY_COLOR, fmtDate } from "@/lib/helpdesk";
import { Button } from "@/components/ui/Button";

function StatusBadge({ s }: { s: TicketStatus }) {
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${STATUS_COLOR[s]}`}>{s.replace("_", " ")}</span>;
}

function PriorityBadge({ p }: { p: TicketPriority }) {
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${PRIORITY_COLOR[p]}`}>{p}</span>;
}

export default function SLABreachesPage() {
  const [selected, setSelected] = useState<Ticket | null>(null);

  const { data: allTickets = [], isLoading } = useQuery({
    queryKey: ["helpdesk", "list", "", "", ""],
    queryFn: () => helpdeskApi.list(),
  });

  const tickets = allTickets.filter(t => t.sla_breached);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">SLA Breaches</h1>
          <p className="text-sm text-gray-500">Tickets that have exceeded their SLA target</p>
        </div>
        <span className="text-sm font-medium text-red-600 bg-red-50 border border-red-200 px-3 py-1.5 rounded-full">
          {tickets.length} breached
        </span>
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Loading…</div>
        ) : tickets.length === 0 ? (
          <div className="p-8 text-center text-green-600 font-medium">No SLA breaches. All tickets within target.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-red-50 border-b">
                <tr>
                  {["Ticket #", "Customer", "Subject", "Category", "Priority", "Status", "SLA (h)", "Assigned", "Opened"].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {tickets.map(t => (
                  <tr key={t.id} className="hover:bg-red-50/40 cursor-pointer" onClick={() => setSelected(t)}>
                    <td className="px-4 py-3 font-mono font-medium text-red-700">{t.ticket_no}</td>
                    <td className="px-4 py-3 truncate max-w-[100px]">{t.customer_name ?? "—"}</td>
                    <td className="px-4 py-3 truncate max-w-[180px]">{t.subject}</td>
                    <td className="px-4 py-3"><span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{t.category}</span></td>
                    <td className="px-4 py-3"><PriorityBadge p={t.priority} /></td>
                    <td className="px-4 py-3"><StatusBadge s={t.status} /></td>
                    <td className="px-4 py-3 text-red-600 font-semibold">{t.sla_hours}h</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{t.assigned_to_name ?? "—"}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{fmtDate(t.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setSelected(null)}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-3" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-start">
              <h2 className="text-lg font-bold">{selected.ticket_no} — {selected.subject}</h2>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
            </div>
            <div className="flex gap-2">
              <StatusBadge s={selected.status} />
              <PriorityBadge p={selected.priority} />
              <span className="text-xs text-red-600 font-semibold bg-red-50 px-2 py-0.5 rounded-full">SLA BREACHED</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm text-gray-600 bg-gray-50 rounded-lg p-3">
              <div><span className="font-medium">Customer:</span> {selected.customer_name ?? "—"}</div>
              <div><span className="font-medium">Category:</span> {selected.category}</div>
              <div><span className="font-medium">SLA target:</span> {selected.sla_hours}h</div>
              <div><span className="font-medium">Assigned:</span> {selected.assigned_to_name ?? "Unassigned"}</div>
              <div><span className="font-medium">Opened:</span> {fmtDate(selected.created_at)}</div>
              {selected.resolved_at && <div><span className="font-medium">Resolved:</span> {fmtDate(selected.resolved_at)}</div>}
            </div>
            {selected.description && <p className="text-sm text-gray-700 whitespace-pre-wrap">{selected.description}</p>}
            <div className="flex justify-end pt-2">
              <Button variant="secondary" onClick={() => setSelected(null)}>Close</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
