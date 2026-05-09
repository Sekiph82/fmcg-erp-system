"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  helpdeskApi, Ticket, TicketStatus, TicketCategory, TicketPriority,
  TicketCreate, STATUS_COLOR, PRIORITY_COLOR, fmtDate,
} from "@/lib/helpdesk";
import { salesApi } from "@/lib/sales";
import { Button } from "@/components/ui/Button";

// ── KPI card ─────────────────────────────────────────────────────────────────

function KpiCard({ label, value, accent }: { label: string; value: string | number; accent?: string }) {
  return (
    <div className={`bg-white rounded-xl border p-4 flex flex-col gap-1 ${accent ?? ""}`}>
      <span className="text-xs text-gray-500 font-medium">{label}</span>
      <span className="text-2xl font-bold text-gray-900">{value}</span>
    </div>
  );
}

// ── Badges ────────────────────────────────────────────────────────────────────

function StatusBadge({ s }: { s: TicketStatus }) {
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${STATUS_COLOR[s]}`}>{s.replace("_", " ")}</span>;
}

function PriorityBadge({ p }: { p: TicketPriority }) {
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${PRIORITY_COLOR[p]}`}>{p}</span>;
}

// ── Create modal ──────────────────────────────────────────────────────────────

function CreateModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const { data: customers = [] } = useQuery({ queryKey: ["customers"], queryFn: () => salesApi.listCustomers() });
  const [form, setForm] = useState<TicketCreate>({
    category: "QUALITY",
    priority: "MEDIUM",
    source: "MANUAL",
    subject: "",
    description: "",
  });

  const mut = useMutation({
    mutationFn: () => helpdeskApi.create({ ...form, description: form.description || undefined }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["helpdesk"] }); onClose(); },
  });

  const categories: TicketCategory[] = ["QUALITY", "DELIVERY", "BILLING", "PRODUCT", "OTHER"];
  const priorities: TicketPriority[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-bold">New Support Ticket</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-sm font-medium text-gray-700">Customer</label>
            <select className="w-full border rounded px-3 py-2 text-sm mt-1"
              value={form.customer_id ?? ""} onChange={e => setForm({ ...form, customer_id: e.target.value || undefined })}>
              <option value="">— None / Anonymous —</option>
              {customers.map(c => <option key={c.id} value={c.id}>{c.name} ({c.code})</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Source</label>
            <select className="w-full border rounded px-3 py-2 text-sm mt-1"
              value={form.source} onChange={e => setForm({ ...form, source: e.target.value as TicketCreate["source"] })}>
              {["PHONE", "EMAIL", "PORTAL", "WHATSAPP", "MANUAL"].map(s => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Category *</label>
            <select className="w-full border rounded px-3 py-2 text-sm mt-1"
              value={form.category} onChange={e => setForm({ ...form, category: e.target.value as TicketCategory })}>
              {categories.map(c => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Priority *</label>
            <select className="w-full border rounded px-3 py-2 text-sm mt-1"
              value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value as TicketPriority })}>
              {priorities.map(p => <option key={p}>{p}</option>)}
            </select>
          </div>
        </div>

        <div>
          <label className="text-sm font-medium text-gray-700">Subject *</label>
          <input className="w-full border rounded px-3 py-2 text-sm mt-1" value={form.subject}
            onChange={e => setForm({ ...form, subject: e.target.value })} placeholder="Describe the issue briefly" />
        </div>
        <div>
          <label className="text-sm font-medium text-gray-700">Description</label>
          <textarea className="w-full border rounded px-3 py-2 text-sm mt-1" rows={3}
            value={form.description ?? ""} onChange={e => setForm({ ...form, description: e.target.value })}
            placeholder="Full details, product batch, order reference…" />
        </div>

        <div className="flex gap-2 justify-end pt-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mut.mutate()} disabled={!form.subject || mut.isPending}>
            {mut.isPending ? "Creating…" : "Create Ticket"}
          </Button>
        </div>
        {mut.isError && <p className="text-xs text-red-600">{(mut.error as Error).message}</p>}
      </div>
    </div>
  );
}

// ── Ticket detail / action panel ──────────────────────────────────────────────

function TicketDetail({ ticket, onClose }: { ticket: Ticket; onClose: () => void }) {
  const qc = useQueryClient();
  const [comment, setComment] = useState("");
  const [isInternal, setIsInternal] = useState(false);
  const [satScore, setSatScore] = useState<number>(5);
  const [showClose, setShowClose] = useState(false);
  const [resNotes, setResNotes] = useState("");

  const mk = (fn: () => Promise<unknown>) =>
    useMutation({ mutationFn: fn, onSuccess: () => qc.invalidateQueries({ queryKey: ["helpdesk"] }) });

  const escalateM = mk(() => helpdeskApi.escalate(ticket.id));
  const resolveM  = mk(() => helpdeskApi.resolve(ticket.id, resNotes || undefined));
  const closeM    = mk(() => helpdeskApi.close(ticket.id, satScore));
  const reopenM   = mk(() => helpdeskApi.reopen(ticket.id));
  const commentM  = mk(() => helpdeskApi.addComment(ticket.id, comment, isInternal).then(r => { setComment(""); return r; }));

  const busy = escalateM.isPending || resolveM.isPending || closeM.isPending || reopenM.isPending || commentM.isPending;

  const slaLabel = ticket.sla_breached
    ? <span className="text-xs text-red-600 font-semibold">SLA BREACHED</span>
    : <span className="text-xs text-green-600">Within SLA</span>;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 space-y-4">
        <div className="flex justify-between items-start">
          <div>
            <h2 className="text-lg font-bold text-gray-900">{ticket.ticket_no} — {ticket.subject}</h2>
            <div className="flex gap-2 mt-1">
              <StatusBadge s={ticket.status} />
              <PriorityBadge p={ticket.priority} />
              {slaLabel}
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
        </div>

        <div className="grid grid-cols-2 gap-3 text-sm text-gray-600 bg-gray-50 rounded-lg p-3">
          <div><span className="font-medium">Customer:</span> {ticket.customer_name ?? "—"}</div>
          <div><span className="font-medium">Category:</span> {ticket.category}</div>
          <div><span className="font-medium">Source:</span> {ticket.source}</div>
          <div><span className="font-medium">SLA:</span> {ticket.sla_hours}h</div>
          <div><span className="font-medium">Assigned to:</span> {ticket.assigned_to_name ?? "Unassigned"}</div>
          <div><span className="font-medium">Lot #:</span> {ticket.lot_number ?? "—"}</div>
          <div><span className="font-medium">Opened:</span> {fmtDate(ticket.created_at)}</div>
          <div><span className="font-medium">First response:</span> {fmtDate(ticket.first_response_at)}</div>
          {ticket.resolved_at && <div><span className="font-medium">Resolved:</span> {fmtDate(ticket.resolved_at)}</div>}
          {ticket.customer_satisfaction && (
            <div><span className="font-medium">CSAT:</span> {"★".repeat(ticket.customer_satisfaction)}{"☆".repeat(5 - ticket.customer_satisfaction)}</div>
          )}
        </div>

        {ticket.description && (
          <div>
            <p className="text-xs font-semibold text-gray-500 mb-1">DESCRIPTION</p>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{ticket.description}</p>
          </div>
        )}

        {/* Actions */}
        {ticket.status !== "CLOSED" && (
          <div className="flex flex-wrap gap-2 border-t pt-3">
            {ticket.status !== "ESCALATED" && ticket.status !== "RESOLVED" && (
              <button disabled={busy} onClick={() => escalateM.mutate()}
                className="text-xs px-3 py-1.5 rounded bg-orange-50 text-orange-700 border border-orange-200 hover:bg-orange-100">
                Escalate
              </button>
            )}
            {ticket.status !== "RESOLVED" && (
              <div className="flex gap-1">
                <input className="border rounded px-2 py-1 text-xs w-40" placeholder="Resolution notes…"
                  value={resNotes} onChange={e => setResNotes(e.target.value)} />
                <button disabled={busy} onClick={() => resolveM.mutate()}
                  className="text-xs px-3 py-1.5 rounded bg-green-50 text-green-700 border border-green-200 hover:bg-green-100">
                  Resolve
                </button>
              </div>
            )}
            {!showClose ? (
              <button disabled={busy} onClick={() => setShowClose(true)}
                className="text-xs px-3 py-1.5 rounded bg-gray-100 text-gray-700 border border-gray-200 hover:bg-gray-200">
                Close
              </button>
            ) : (
              <div className="flex gap-1 items-center">
                <span className="text-xs text-gray-500">CSAT (1-5):</span>
                <select className="border rounded px-2 py-1 text-xs" value={satScore}
                  onChange={e => setSatScore(Number(e.target.value))}>
                  {[1, 2, 3, 4, 5].map(n => <option key={n}>{n}</option>)}
                </select>
                <button disabled={busy} onClick={() => closeM.mutate()}
                  className="text-xs px-3 py-1.5 rounded bg-gray-200 text-gray-800 hover:bg-gray-300">
                  Confirm Close
                </button>
                <button onClick={() => setShowClose(false)} className="text-xs text-gray-400 hover:text-gray-600">✕</button>
              </div>
            )}
          </div>
        )}

        {(ticket.status === "RESOLVED" || ticket.status === "CLOSED") && (
          <button disabled={busy} onClick={() => reopenM.mutate()}
            className="text-xs px-3 py-1.5 rounded bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100">
            Reopen
          </button>
        )}

        {/* Comments */}
        <div className="border-t pt-3 space-y-2">
          <p className="text-xs font-semibold text-gray-500">COMMENTS & ACTIVITY ({ticket.comments.length})</p>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {ticket.comments.map(c => (
              <div key={c.id} className={`rounded-lg p-2.5 text-sm ${c.is_internal ? "bg-yellow-50 border border-yellow-100" : "bg-gray-50"}`}>
                <div className="flex gap-2 items-center mb-1">
                  <span className="font-medium text-gray-700 text-xs">{c.created_by_name ?? "User"}</span>
                  {c.is_internal && <span className="text-xs text-yellow-600 font-semibold">INTERNAL</span>}
                  <span className="text-xs text-gray-400 ml-auto">{fmtDate(c.created_at)}</span>
                </div>
                <p className="text-gray-700 whitespace-pre-wrap">{c.body}</p>
              </div>
            ))}
            {ticket.comments.length === 0 && <p className="text-xs text-gray-400">No comments yet.</p>}
          </div>

          {ticket.status !== "CLOSED" && (
            <div className="flex gap-2 pt-1">
              <textarea className="flex-1 border rounded px-3 py-2 text-sm" rows={2}
                placeholder="Add comment…" value={comment} onChange={e => setComment(e.target.value)} />
              <div className="flex flex-col gap-1">
                <label className="flex items-center gap-1 text-xs text-gray-600">
                  <input type="checkbox" checked={isInternal} onChange={e => setIsInternal(e.target.checked)} />
                  Internal
                </label>
                <button disabled={!comment || busy} onClick={() => commentM.mutate()}
                  className="text-xs px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50">
                  Send
                </button>
              </div>
            </div>
          )}
        </div>

        {(escalateM.isError || resolveM.isError || closeM.isError || commentM.isError) && (
          <p className="text-xs text-red-600">Action failed — please try again.</p>
        )}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function HelpdeskPage({ defaultStatus }: { defaultStatus?: TicketStatus | "" } = {}) {
  const [statusFilter, setStatusFilter] = useState<TicketStatus | "">(defaultStatus ?? "");
  const [catFilter, setCatFilter] = useState<TicketCategory | "">("");
  const [priFilter, setPriFilter] = useState<TicketPriority | "">("");
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState<Ticket | null>(null);

  const { data: dash } = useQuery({ queryKey: ["helpdesk", "dashboard"], queryFn: helpdeskApi.dashboard });
  const { data: tickets = [], isLoading } = useQuery({
    queryKey: ["helpdesk", "list", statusFilter, catFilter, priFilter],
    queryFn: () => helpdeskApi.list({
      status:   statusFilter || undefined,
      category: catFilter    || undefined,
      priority: priFilter    || undefined,
    }),
  });

  const statuses:   TicketStatus[]   = ["OPEN", "IN_PROGRESS", "ESCALATED", "RESOLVED", "CLOSED"];
  const categories: TicketCategory[] = ["QUALITY", "DELIVERY", "BILLING", "PRODUCT", "OTHER"];
  const priorities: TicketPriority[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Helpdesk & Complaints</h1>
          <p className="text-sm text-gray-500">Customer complaints, quality issues, and support tickets</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>+ New Ticket</Button>
      </div>

      {/* KPI cards */}
      {dash && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
          <KpiCard label="Total" value={dash.total_tickets} />
          <KpiCard label="Open" value={dash.open_count} />
          <KpiCard label="In Progress" value={dash.in_progress_count} />
          <KpiCard label="Escalated" value={dash.escalated_count} />
          <KpiCard label="Resolved" value={dash.resolved_count} />
          <KpiCard label="Closed" value={dash.closed_count} />
          <KpiCard label="SLA Breached" value={dash.sla_breached_count} accent={dash.sla_breached_count > 0 ? "border-red-300" : ""} />
          <KpiCard label="Avg Resolution" value={dash.avg_resolution_hours != null ? `${dash.avg_resolution_hours}h` : "—"} />
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        {/* Status */}
        <div className="flex gap-1 flex-wrap">
          <button onClick={() => setStatusFilter("")}
            className={`text-xs px-3 py-1.5 rounded-full border font-medium ${statusFilter === "" ? "bg-gray-900 text-white" : "bg-white text-gray-600 border-gray-200"}`}>
            All Status
          </button>
          {statuses.map(s => (
            <button key={s} onClick={() => setStatusFilter(s)}
              className={`text-xs px-3 py-1.5 rounded-full border font-medium ${statusFilter === s ? "bg-gray-900 text-white" : "bg-white text-gray-600 border-gray-200"}`}>
              {s.replace("_", " ")}
            </button>
          ))}
        </div>

        <div className="h-6 border-l border-gray-200 mx-1" />

        {/* Category */}
        <div className="flex gap-1 flex-wrap">
          <button onClick={() => setCatFilter("")}
            className={`text-xs px-3 py-1.5 rounded-full border font-medium ${catFilter === "" ? "bg-blue-600 text-white" : "bg-white text-gray-600 border-gray-200"}`}>
            All Cat
          </button>
          {categories.map(c => (
            <button key={c} onClick={() => setCatFilter(c)}
              className={`text-xs px-3 py-1.5 rounded-full border font-medium ${catFilter === c ? "bg-blue-600 text-white" : "bg-white text-gray-600 border-gray-200"}`}>
              {c}
            </button>
          ))}
        </div>

        <div className="h-6 border-l border-gray-200 mx-1" />

        {/* Priority */}
        <div className="flex gap-1 flex-wrap">
          {priorities.map(p => (
            <button key={p} onClick={() => setPriFilter(priFilter === p ? "" : p)}
              className={`text-xs px-3 py-1.5 rounded-full border font-medium ${priFilter === p ? "bg-orange-600 text-white" : "bg-white text-gray-600 border-gray-200"}`}>
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Loading tickets…</div>
        ) : tickets.length === 0 ? (
          <div className="p-8 text-center text-gray-400">No tickets found. Create the first support ticket.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  {["Ticket #", "Customer", "Subject", "Category", "Priority", "Status", "SLA", "Assigned", "Opened", "Actions"].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {tickets.map(t => (
                  <tr key={t.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => setSelected(t)}>
                    <td className="px-4 py-3 font-mono font-medium text-gray-900">{t.ticket_no}</td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900 truncate max-w-[100px]">{t.customer_name ?? "—"}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="truncate max-w-[180px] text-gray-800">{t.subject}</div>
                      {t.lot_number && <div className="text-xs text-gray-400">Lot: {t.lot_number}</div>}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{t.category}</span>
                    </td>
                    <td className="px-4 py-3"><PriorityBadge p={t.priority} /></td>
                    <td className="px-4 py-3"><StatusBadge s={t.status} /></td>
                    <td className="px-4 py-3">
                      {t.sla_breached
                        ? <span className="text-xs text-red-600 font-semibold">BREACHED</span>
                        : <span className="text-xs text-green-600">{t.sla_hours}h SLA</span>}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">{t.assigned_to_name ?? "—"}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{fmtDate(t.created_at)}</td>
                    <td className="px-4 py-3">
                      <button onClick={e => { e.stopPropagation(); setSelected(t); }}
                        className="text-xs px-2 py-1 rounded bg-blue-50 text-blue-700 hover:bg-blue-100">
                        Open
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modals */}
      {showCreate && <CreateModal onClose={() => setShowCreate(false)} />}
      {selected && <TicketDetail ticket={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
